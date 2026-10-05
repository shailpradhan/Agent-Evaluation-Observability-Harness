"""Provider-independent agent orchestration."""

from __future__ import annotations

import json
from collections.abc import Iterable
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


class InvalidLLMResponseError(AgentError):
    """Raised when an LLM response violates the agent JSON contract."""


class MaxIterationsExceededError(AgentError):
    """Raised when no final response is produced within the configured limit."""


class Agent:
    """Run an LLM-directed tool loop using injected LLM and tool dependencies."""

    def __init__(
        self,
        llm: LLM,
        tools: ToolRegistry | Iterable[Tool[Any, Any]],
        max_iterations: int = 10,
    ) -> None:
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
            raise TypeError("max_iterations must be an integer.")
        if max_iterations < 1:
            raise ValueError("max_iterations must be a positive integer.")

        self.llm = llm
        self.tools = tools if isinstance(tools, ToolRegistry) else ToolRegistry(tools)
        self.max_iterations = max_iterations

    def run(self, task: str) -> AgentResult:
        """Execute a task until the LLM returns a final response or the limit hits."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an agent with access to the following tools. "
                    "Select a tool by returning JSON "
                    '{"tool_call":{"name":"...","arguments":{...}}}, or finish '
                    'with JSON {"final_response":"..."}. Use exactly one action. '
                    "Tool definitions: "
                    + json.dumps(self.tools.describe())
                ),
            },
            {"role": "user", "content": task},
        ]
        tool_calls: list[AgentToolCall] = []

        for _ in range(self.max_iterations):
            response = self.llm.generate(messages)
            decision = self._parse_decision(response)
            if decision.final_response is not None:
                return AgentResult(
                    final_response=decision.final_response,
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

            try:
                result = tool.execute(arguments)
            except Exception as exc:
                raise ToolExecutionError(
                    f"Tool '{tool.name}' failed: {exc}"
                ) from exc

            call = AgentToolCall(
                name=tool.name,
                arguments=arguments.model_dump(mode="json"),
                result=result.model_dump(mode="json"),
            )
            tool_calls.append(call)
            messages.extend(
                [
                    {"role": "assistant", "content": response},
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

    @staticmethod
    def _parse_decision(response: str) -> LLMDecision:
        try:
            return LLMDecision.model_validate_json(response)
        except (ValidationError, ValueError, TypeError) as exc:
            raise InvalidLLMResponseError(
                "LLM response must be valid JSON containing exactly one "
                "'tool_call' or 'final_response'."
            ) from exc
