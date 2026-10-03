"""Replay and mock tool interaction models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_eval.models.base import BaseSchema, Field


class MockToolEntry(BaseSchema):
    """A recorded tool call with its response for deterministic offline replay."""
    tool: str = Field(description="Name of the tool mocked")
    input: Dict[str, Any] = Field(default_factory=dict, description="Expected input parameters")
    output: Any = Field(default=None, description="Mock output to return during replay")
    error: Optional[str] = Field(default=None, description="Mock error to simulate failure")
    latency_ms: Optional[float] = Field(default=None, description="Simulated execution latency in ms")


class ReplaySession(BaseSchema):
    """Session containing recorded mocks for deterministic offline task execution."""
    session_id: str = Field(description="Unique replay session identifier")
    task_id: str = Field(description="Task identifier associated with these mocks")
    recorded_tools: List[MockToolEntry] = Field(default_factory=list, description="Recorded tool mock entries")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session recording metadata")

