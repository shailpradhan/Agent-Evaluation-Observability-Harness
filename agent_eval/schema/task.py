"""Task schema definitions for agent evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from agent_eval.models.base import BaseSchema, Field


class RubricCheck(BaseSchema):
    """A deterministic, binary assertion that can be checked against a trace."""

    assertion: str = Field(description="Atomic yes/no assertion shown in reports")
    kind: Literal[
        "tool_sequence",
        "tool_result_contains",
        "final_response_contains",
    ] = Field(description="Trace evidence to check")
    expected: Any = Field(description="Expected sequence, result fields, or response text")


class Task(BaseSchema):
    """Specification of an individual evaluation test task for an AI agent."""
    id: str = Field(description="Unique identifier for the task, e.g. 'refund_order_1234'")
    prompt: str = Field(description="Input task prompt or user request sent to the agent")
    expected_outcome: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target outcome attributes, states, or key-values expected upon completion"
    )
    expected_tools: List[str] = Field(
        default_factory=list,
        description="List of tool names expected to be called by the agent"
    )
    rubric: List[RubricCheck] = Field(
        default_factory=list,
        description="Atomic binary checks evaluated against the execution trace"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional human-readable description of what this task evaluates"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain tags, difficulty, or versioning metadata"
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not self.id or not str(self.id).strip():
            raise ValueError("Task 'id' must be a non-empty string.")
        if not self.prompt or not str(self.prompt).strip():
            raise ValueError("Task 'prompt' must be a non-empty string.")
        # Normalize prompt stripping whitespace
        self.prompt = str(self.prompt).strip()
