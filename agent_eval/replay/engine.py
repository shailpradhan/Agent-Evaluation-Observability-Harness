"""Deterministic replay using recorded LLM decisions and tool results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_eval.agent.agent import Agent, ToolExecutionError
from agent_eval.agent.llm import LLM
from agent_eval.agent.models import AgentResult, LLMDecision
from agent_eval.agent.tools import Tool, ToolRegistry
from agent_eval.tracing import TraceRunner
from agent_eval.models.replay import MockToolEntry, ReplaySession
from agent_eval.models.trajectory import Trajectory
from agent_eval.schema.task import Task


class ReplayError(Exception):
    """Base error for replay failures."""


class ReplayMismatchError(ReplayError):
    """Raised when replay diverges from recorded calls or results."""


@dataclass
class ReplayOutcome:
    """Outputs from replaying one recorded agent execution."""

    session: ReplaySession
    agent_result: AgentResult
    trajectory: Trajectory


class _RecordedLLM(LLM):
    def __init__(self, trajectory: Trajectory) -> None:
        self._calls = trajectory.llm_calls
        self._index = 0

    def generate(self, messages: list[dict[str, str]]) -> LLMDecision:
        del messages
        if self._index >= len(self._calls):
            raise ReplayMismatchError("Replay requested more LLM turns than recorded.")
        call = self._calls[self._index]
        self._index += 1
        try:
            return LLMDecision.model_validate_json(call.response)
        except ValueError as exc:
            raise ReplayMismatchError(
                f"Recorded LLM response {self._index} is invalid."
            ) from exc

    @property
    def consumed(self) -> int:
        return self._index


class ReplayEngine:
    """Replay a trajectory without invoking the original LLM or tool functions."""

    def replay(
        self,
        agent: Agent,
        task: Task,
        trajectory: Trajectory,
    ) -> ReplayOutcome:
        session = self.create_session(trajectory)
        recorded_llm = _RecordedLLM(trajectory)
        mocks = session.recorded_tools
        tool_index = 0

        def wrap_tool(tool: Tool[Any, Any]) -> Tool[Any, Any]:
            def replay_function(arguments: Any) -> Any:
                nonlocal tool_index
                if tool_index >= len(mocks):
                    raise ReplayMismatchError(
                        f"Replay requested unrecorded tool '{tool.name}'."
                    )
                entry = mocks[tool_index]
                tool_index += 1
                actual_input = arguments.model_dump(mode="json")
                if entry.tool != tool.name or entry.input != actual_input:
                    raise ReplayMismatchError(
                        "Replay tool call mismatch: "
                        f"expected {entry.tool}({entry.input}), got "
                        f"{tool.name}({actual_input})."
                    )
                if entry.error is not None:
                    raise ReplayMismatchError(
                        f"Recorded tool '{tool.name}' failed: {entry.error}"
                    )
                try:
                    return tool.output_model.model_validate(entry.output)
                except Exception as exc:
                    raise ReplayMismatchError(
                        f"Recorded output for tool '{tool.name}' is invalid: {exc}"
                    ) from exc

            return Tool(
                name=tool.name,
                description=tool.description,
                function=replay_function,
                input_model=tool.input_model,
                output_model=tool.output_model,
                requires_approval=tool.requires_approval,
                final_response_from_result=tool.final_response_from_result,
            )

        original_tools = (
            agent.tools.tools
            if isinstance(agent.tools, ToolRegistry)
            else tuple(agent.tools)
        )

        def approve_recorded_call(tool_name: str, arguments: dict[str, Any]) -> bool:
            return tool_name in {tool.name for tool in original_tools} and isinstance(
                arguments, dict
            )

        replay_agent = Agent(
            llm=recorded_llm,
            tools=[wrap_tool(tool) for tool in original_tools],
            max_iterations=agent.max_iterations,
            approval_handler=approve_recorded_call,
        )
        try:
            traced_replay = TraceRunner().run(
                replay_agent,
                task,
                run_id=f"{trajectory.run_id}-replay",
            )
        except ToolExecutionError as exc:
            if isinstance(exc.__cause__, ReplayMismatchError):
                raise exc.__cause__ from exc
            raise
        if recorded_llm.consumed != len(trajectory.llm_calls):
            raise ReplayMismatchError(
                f"Replay consumed {recorded_llm.consumed} of "
                f"{len(trajectory.llm_calls)} recorded LLM calls."
            )
        if tool_index != len(mocks):
            raise ReplayMismatchError(
                f"Replay consumed {tool_index} of {len(mocks)} recorded tool calls."
            )
        return ReplayOutcome(
            session=session,
            agent_result=traced_replay.agent_result,
            trajectory=traced_replay.trajectory,
        )

    @staticmethod
    def create_session(trajectory: Trajectory) -> ReplaySession:
        if len(trajectory.tool_calls) != len(trajectory.tool_responses):
            raise ReplayMismatchError(
                "Cannot replay a trajectory with unmatched tool calls and responses."
            )
        entries: list[MockToolEntry] = []
        for call, response in zip(
            trajectory.tool_calls,
            trajectory.tool_responses,
        ):
            if call.tool != response.tool or call.arguments != response.input:
                raise ReplayMismatchError(
                    "Cannot replay a trajectory with mismatched tool call and "
                    "response records."
                )
            entries.append(
                MockToolEntry(
                    tool=call.tool,
                    input=call.arguments,
                    output=response.output,
                    error=response.error,
                    latency_ms=response.latency_ms,
                )
            )
        return ReplaySession(
            session_id=f"{trajectory.run_id}-replay",
            task_id=trajectory.task_id,
            recorded_tools=entries,
        )