"""Evaluation metrics, run records, and regression reporting models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_eval.models.base import BaseSchema, Field


class EvalResult(BaseSchema):
    """Result of an evaluation for a single task."""
    result_id: str = Field(description="Unique identifier for this test result")
    run_id: str = Field(description="Evaluation run identifier")
    task_id: str = Field(description="Task identifier evaluated")
    score: float = Field(description="Score achieved (0.0 to 1.0)")
    passed: bool = Field(description="Whether the task passed acceptance criteria")
    latency_ms: float = Field(default=0.0, description="Total execution latency in milliseconds")
    tokens: int = Field(default=0, description="Total tokens consumed")
    resolved: Optional[bool] = Field(
        default=None,
        description="Whether execution reached a terminal outcome, independent of pass/fail",
    )
    safety_compliant: Optional[bool] = Field(
        default=None,
        description="Whether the response and actions complied with safety and privacy policies",
    )
    policy_violations: List[str] = Field(
        default_factory=list,
        description="Detected safety, privacy, or policy violations",
    )
    side_effects_intended: Optional[bool] = Field(
        default=None,
        description="Whether intended external state changes occurred",
    )
    unexpected_side_effects: List[str] = Field(
        default_factory=list,
        description="External state changes that were not intended",
    )
    tool_calls: int = Field(
        default=0,
        description="Number of tool calls made for this task",
    )
    agent_turns: int = Field(
        default=0,
        description="Number of agent/LLM turns used for this task",
    )
    error: Optional[str] = Field(default=None, description="Execution or evaluation error, if any")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Evaluation timestamp")


class EvalRun(BaseSchema):
    """Aggregate metrics recorded for a complete evaluation run across a dataset."""
    run_id: str = Field(description="Unique identifier for this evaluation run")
    model_version: str = Field(description="Identifier or version of the LLM evaluated")
    prompt_version: str = Field(description="Version tag of the agent prompt tested")
    dataset_version: str = Field(description="Version of the evaluation dataset used")
    mean_score: float = Field(default=0.0, description="Average score across all tasks in the dataset")
    pass_rate: float = Field(default=0.0, description="Percentage of passed tasks (0.0 to 1.0)")
    total_tasks: int = Field(default=0, description="Total number of tasks evaluated")
    passed_tasks: int = Field(default=0, description="Number of tasks that passed")
    failed_tasks: int = Field(default=0, description="Number of tasks that failed")
    token_cost: Optional[float] = Field(default=None, description="Estimated monetary cost of tokens used")
    cost_per_resolved_task: Optional[float] = Field(
        default=None,
        description="Total token cost divided by resolved tasks",
    )
    resolved_tasks: int = Field(
        default=0,
        description="Number of tasks that reached a terminal outcome",
    )
    total_tokens: int = Field(
        default=0,
        description="Total tokens consumed across evaluated tasks",
    )
    tokens_per_task: Optional[float] = Field(
        default=None,
        description="Average tokens consumed per evaluated task",
    )
    tool_calls_per_task: Optional[float] = Field(
        default=None,
        description="Average tool calls per evaluated task",
    )
    agent_turns_per_task: Optional[float] = Field(
        default=None,
        description="Average agent/LLM turns per evaluated task",
    )
    p50_latency_ms: Optional[float] = Field(
        default=None,
        description="Median task execution latency in milliseconds",
    )
    p95_latency_ms: Optional[float] = Field(default=None, description="95th percentile latency in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the run")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional run configuration or git commit SHA")


class RegressionReport(BaseSchema):
    """Comparison report between a baseline run and a candidate run."""
    baseline_run_id: str = Field(description="Reference / baseline run identifier")
    candidate_run_id: str = Field(description="New candidate run identifier")
    mean_score_diff: float = Field(description="Difference in mean score (candidate - baseline)")
    pass_rate_diff: float = Field(description="Difference in pass rate (candidate - baseline)")
    latency_diff_ms: float = Field(default=0.0, description="Difference in average/p95 latency in ms")
    regression_detected: bool = Field(description="Whether a quality regression occurred exceeding threshold")
    regressed_tasks: List[str] = Field(default_factory=list, description="IDs of tasks that degraded")
    summary: str = Field(default="", description="Human-readable summary of the comparison")
