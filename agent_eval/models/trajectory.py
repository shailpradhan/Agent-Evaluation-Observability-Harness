"""Trajectory and execution observability models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_eval.models.base import BaseSchema, Field


class StepType(str, Enum):
    """Types of steps in an agent trajectory."""
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    REASONING = "reasoning"
    FINAL_RESPONSE = "final_response"


class ToolCall(BaseSchema):
    """Record of a tool invocation requested by an agent."""
    tool: str = Field(description="Name of the tool being called")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    call_id: Optional[str] = Field(default=None, description="Unique identifier for this tool call invocation")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp when the tool call was made")


class ToolResponse(BaseSchema):
    """Record of the response returned by a tool."""
    tool: str = Field(description="Name of the tool that was executed")
    input: Dict[str, Any] = Field(default_factory=dict, description="Input arguments received by the tool")
    output: Any = Field(default=None, description="Output returned by the tool")
    error: Optional[str] = Field(default=None, description="Error message if tool execution failed")
    latency_ms: Optional[float] = Field(default=None, description="Tool execution duration in milliseconds")
    call_id: Optional[str] = Field(default=None, description="Corresponding call_id if available")


class LLMCall(BaseSchema):
    """Record of an LLM generation call."""
    model: str = Field(description="Model identifier, e.g., gemini-2.5-pro or gpt-4o")
    prompt: Any = Field(description="Prompt or message list sent to the LLM")
    response: str = Field(description="Text response or generated content from LLM")
    input_tokens: int = Field(default=0, description="Input / prompt tokens consumed")
    output_tokens: int = Field(default=0, description="Output / completion tokens consumed")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    latency_ms: float = Field(default=0.0, description="Call duration in milliseconds")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp of the LLM call")


class TrajectoryStep(BaseSchema):
    """A discrete step within an agent's execution trajectory."""
    step_index: int = Field(description="0-indexed sequence position of the step")
    type: StepType = Field(description="Type of execution step")
    content: Any = Field(description="Step payload (e.g. ToolCall, ToolResponse, LLMCall, text)")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp of the step")
    latency_ms: Optional[float] = Field(default=None, description="Duration of this step in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual metadata")


class Trajectory(BaseSchema):
    """Complete trace of an agent's interaction lifecycle on a task."""
    run_id: str = Field(description="Unique evaluation run identifier")
    task_id: str = Field(description="Identifier of the task being executed")
    agent_version: Optional[str] = Field(default=None, description="Version of the agent under test")
    prompt_version: Optional[str] = Field(default=None, description="Version of the agent system prompt")
    model_name: Optional[str] = Field(default=None, description="Underlying LLM model name")
    steps: List[TrajectoryStep] = Field(default_factory=list, description="Ordered trajectory steps")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="All tool calls executed")
    tool_responses: List[ToolResponse] = Field(default_factory=list, description="All tool responses received")
    llm_calls: List[LLMCall] = Field(default_factory=list, description="All LLM generations performed")
    final_response: Optional[str] = Field(default=None, description="Final answer produced for the user")
    total_latency_ms: float = Field(default=0.0, description="Total agent execution duration in milliseconds")
    total_tokens: int = Field(default=0, description="Total tokens consumed across all LLM calls")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata and trace context")

    def record_tool_call(self, call: ToolCall) -> TrajectoryStep:
        """Append a tool call to the trajectory."""
        if self.tool_calls is None:
            self.tool_calls = []
        if self.steps is None:
            self.steps = []
        self.tool_calls.append(call)
        step = TrajectoryStep(
            step_index=len(self.steps),
            type=StepType.TOOL_CALL,
            content=call.model_dump() if hasattr(call, "model_dump") else call,
            timestamp=call.timestamp or datetime.now(timezone.utc),
        )
        self.steps.append(step)
        return step

    def record_tool_response(self, response: ToolResponse) -> TrajectoryStep:
        """Append a tool response to the trajectory."""
        if self.tool_responses is None:
            self.tool_responses = []
        if self.steps is None:
            self.steps = []
        self.tool_responses.append(response)
        if response.latency_ms:
            self.total_latency_ms += response.latency_ms
        step = TrajectoryStep(
            step_index=len(self.steps),
            type=StepType.TOOL_RESPONSE,
            content=response.model_dump() if hasattr(response, "model_dump") else response,
            latency_ms=response.latency_ms,
            timestamp=datetime.now(timezone.utc),
        )
        self.steps.append(step)
        return step

    def record_llm_call(self, call: LLMCall) -> TrajectoryStep:
        """Append an LLM call to the trajectory and accumulate tokens/latency."""
        if self.llm_calls is None:
            self.llm_calls = []
        if self.steps is None:
            self.steps = []
        self.llm_calls.append(call)
        tokens = call.total_tokens or (call.input_tokens + call.output_tokens)
        self.total_tokens += tokens
        self.total_latency_ms += call.latency_ms
        step = TrajectoryStep(
            step_index=len(self.steps),
            type=StepType.LLM_CALL,
            content=call.model_dump() if hasattr(call, "model_dump") else call,
            latency_ms=call.latency_ms,
            timestamp=call.timestamp or datetime.now(timezone.utc),
        )
        self.steps.append(step)
        return step

    def set_final_response(self, response: str) -> TrajectoryStep:
        """Set final user-facing response."""
        if self.steps is None:
            self.steps = []
        self.final_response = response
        step = TrajectoryStep(
            step_index=len(self.steps),
            type=StepType.FINAL_RESPONSE,
            content=response,
            timestamp=datetime.now(timezone.utc),
        )
        self.steps.append(step)
        return step

    @property
    def tool_names_called(self) -> List[str]:
        """Return list of distinct tool names invoked."""
        return [tc.tool for tc in (self.tool_calls or [])]

