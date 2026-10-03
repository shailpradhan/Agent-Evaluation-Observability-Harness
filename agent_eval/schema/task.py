"""Task schema definitions for agent evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_eval.models.base import BaseSchema, Field


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
    rubric: List[str] = Field(
        default_factory=list,
        description="Grading criteria for LLM-as-a-judge evaluation"
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

