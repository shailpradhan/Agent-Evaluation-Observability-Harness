"""Provider-independent agent orchestration."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

from pydantic import ValidationError

from agent_eval.agent.llm import LLM
from agent_eval.agent.models import AgentResult, AgentToolCall, LLMDecision
from agent_eval.agent.tools import Tool, ToolRegistry


class AgentError(Exception):
    """Base exception for agent orchestration failures."""


class UnknownToolError(AgentError):
    """Raised when an LLM selects a tool absent from the injected registry."""


class InvalidToolArgumentsError(AgentError):
    """Raised when selected-tool arguments fail schema validation."""


class ToolExecutionError(AgentError):
    """Raised when a tool raises an exception or returns invalid output."""


class ToolApprovalRequiredError(AgentError):
    """Raised when a tool requires approval but no approval handler is configured."""


class ToolApprovalDeniedError(AgentError):
    """Raised when the configured approval handler rejects a tool call."""


class ToolApprovalError(AgentError):
    """Raised when the approval handler fails."""


class InvalidLLMResponseError(AgentError):
    """Raised when an LLM adapter violates the structured response contract."""


class MaxIterationsExceededError(AgentError):
    """Raised when no final response is produced within the configured limit."""


class Agent:
    """Run an LLM-directed tool loop using injected LLM and tool dependencies."""

    def __init__(
        self,
        llm: LLM,
        tools: ToolRegistry | Iterable[Tool[Any, Any]],
        max_iterations: int = 10,
        approval_handler: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
            raise TypeError("max_iterations must be an integer.")
        if max_iterations < 1:
            raise ValueError("max_iterations must be a positive integer.")

        self.llm = llm
        self.tools = tools if isinstance(tools, ToolRegistry) else ToolRegistry(tools)
        self.max_iterations = max_iterations
        self.approval_handler = approval_handler

    def run(self, task: str) -> AgentResult:
        """Execute a task until the LLM returns a final response or the limit hits."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an agent with access to the following tools. "
                    "Select exactly one tool call or provide a final response. "
                    "Do not claim a side effect succeeded unless a tool result "
                    "confirms it. "
                    "Tool definitions: "
                    + json.dumps(self.tools.describe())
                ),
            },
            {"role": "user", "content": task},
        ]
        tool_calls: list[AgentToolCall] = []
        grounded_final_response: str | None = None

        for _ in range(self.max_iterations):
            decision = self.llm.generate(messages)
            if not isinstance(decision, LLMDecision):
                raise InvalidLLMResponseError(
                    "LLM.generate() must return an LLMDecision instance."
                )

            if decision.final_response is not None:
                return AgentResult(
                    final_response=grounded_final_response or decision.final_response,
                    tool_calls=tool_calls,
                )

            if decision.tool_call is None:
                raise InvalidLLMResponseError("The LLM response contained no action.")

            tool = self.tools.get(decision.tool_call.name)
            if tool is None:
                raise UnknownToolError(
                    f"The LLM selected unknown tool '{decision.tool_call.name}'."
                )

            try:
                arguments = tool.validate_arguments(decision.tool_call.arguments)
            except ValidationError as exc:
                raise InvalidToolArgumentsError(
                    f"Invalid arguments for tool '{tool.name}': {exc}"
                ) from exc

            if tool.requires_approval:
                if self.approval_handler is None:
                    raise ToolApprovalRequiredError(
                        f"Tool '{tool.name}' requires approval, but no approval "
                        "handler was configured."
                    )
                try:
                    approved = self.approval_handler(
                        tool.name, arguments.model_dump(mode="json")
                    )
                except Exception as exc:
                    raise ToolApprovalError(
                        f"Approval handler failed for tool '{tool.name}': {exc}"
                    ) from exc
                if approved is not True:
                    raise ToolApprovalDeniedError(
                        f"Approval was denied for tool '{tool.name}'."
                    )

            try:
                result = tool.execute(arguments)
            except Exception as exc:
                raise ToolExecutionError(
                    f"Tool '{tool.name}' failed: {exc}"
                ) from exc

            if tool.final_response_from_result is not None:
                try:
                    grounded_final_response = tool.final_response_from_result(result)
                    if not grounded_final_response:
                        raise ValueError("The result formatter returned an empty response.")
                except Exception as exc:
                    raise ToolExecutionError(
                        f"Tool '{tool.name}' could not format its validated result: {exc}"
                    ) from exc

            call = AgentToolCall(
                name=tool.name,
                arguments=arguments.model_dump(mode="json"),
                result=result.model_dump(mode="json"),
            )
            tool_calls.append(call)
            messages.extend(
                [
                    {"role": "assistant", "content": decision.model_dump_json()},
                    {
                        "role": "tool",
                        "name": tool.name,
                        "content": json.dumps(result.model_dump(mode="json")),
                    },
                ]
            )

        raise MaxIterationsExceededError(
            f"Agent did not produce a final response within "
            f"{self.max_iterations} iterations."
        )
