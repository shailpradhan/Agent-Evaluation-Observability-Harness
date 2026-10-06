"""Execution tracing wrappers kept outside the core agent implementation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from agent_eval.agent.agent import Agent
from agent_eval.agent.llm import LLM
from agent_eval.agent.models import AgentResult, LLMDecision
from agent_eval.agent.tools import Tool, ToolRegistry
from agent_eval.models.trajectory import LLMCall, ToolCall, ToolResponse, Trajectory
from agent_eval.schema.task import Task


@dataclass
class TracedRun:
    """Agent result and trajectory collected by the evaluation layer."""

    agent_result: AgentResult
    trajectory: Trajectory


class _TracingLLM(LLM):
    def __init__(self, wrapped: LLM, trajectory: Trajectory) -> None:
        self._wrapped = wrapped
        self._trajectory = trajectory
        self.model_name = getattr(wrapped, "model_name", type(wrapped).__name__)

    def generate(self, messages: list[dict[str, str]]) -> LLMDecision:
        started = perf_counter()
        decision = self._wrapped.generate(messages)
        self._trajectory.record_llm_call(
            LLMCall(
                model=self.model_name,
                prompt=[dict(message) for message in messages],
                response=decision.model_dump_json(),
                latency_ms=(perf_counter() - started) * 1000,
            )
        )
        return decision


class TraceRunner:
    """Wrap an agent's LLM and tools to capture a trajectory externally."""

    def run(
        self,
        agent: Agent,
        task: Task,
        *,
        run_id: str | None = None,
    ) -> TracedRun:
        trajectory = Trajectory(
            run_id=run_id or str(uuid4()),
            task_id=task.id,
            model_name=getattr(agent.llm, "model_name", type(agent.llm).__name__),
        )
        tools = (
            agent.tools.tools
            if isinstance(agent.tools, ToolRegistry)
            else tuple(agent.tools)
        )
        traced_tools = [
            self._trace_tool(tool, trajectory) for tool in tools
        ]
        traced_agent = Agent(
            llm=_TracingLLM(agent.llm, trajectory),
            tools=traced_tools,
            max_iterations=agent.max_iterations,
            approval_handler=agent.approval_handler,
        )
        result = traced_agent.run(task.prompt)
        trajectory.set_final_response(result.final_response)
        return TracedRun(agent_result=result, trajectory=trajectory)

    @staticmethod
    def _trace_tool(
        tool: Tool[Any, Any],
        trajectory: Trajectory,
    ) -> Tool[Any, Any]:
        def traced_function(arguments: Any) -> Any:
            input_data = arguments.model_dump(mode="json")
            trajectory.record_tool_call(
                ToolCall(tool=tool.name, arguments=input_data)
            )
            started = perf_counter()
            try:
                output = tool.output_model.model_validate(tool.function(arguments))
            except Exception as exc:
                trajectory.record_tool_response(
                    ToolResponse(
                        tool=tool.name,
                        input=input_data,
                        error=str(exc),
                        latency_ms=(perf_counter() - started) * 1000,
                    )
                )
                raise

            trajectory.record_tool_response(
                ToolResponse(
                    tool=tool.name,
                    input=input_data,
                    output=output.model_dump(mode="json"),
                    latency_ms=(perf_counter() - started) * 1000,
                )
            )
            return output

        return Tool(
            name=tool.name,
            description=tool.description,
            function=traced_function,
            input_model=tool.input_model,
            output_model=tool.output_model,
            requires_approval=tool.requires_approval,
            final_response_from_result=tool.final_response_from_result,
        )
