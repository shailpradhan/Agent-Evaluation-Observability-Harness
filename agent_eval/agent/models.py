"""Provider-independent models used by the agent layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolCallRequest(BaseModel):
    """A tool selection returned through the LLM's JSON response contract."""

    model_config = ConfigDict(extra="forbid")

    name: str
    arguments: dict[str, Any]


class LLMDecision(BaseModel):
    """A single LLM turn: either a tool call or a final response."""

    model_config = ConfigDict(extra="forbid")

    tool_call: ToolCallRequest | None = None
    final_response: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_exactly_one_action(self) -> LLMDecision:
        if (self.tool_call is None) == (self.final_response is None):
            raise ValueError("Provide exactly one of 'tool_call' or 'final_response'.")
        return self


class AgentToolCall(BaseModel):
    """A successfully executed tool call and its result."""

    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class AgentResult(BaseModel):
    """The user-facing response and tool calls from one agent run."""

    final_response: str
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
