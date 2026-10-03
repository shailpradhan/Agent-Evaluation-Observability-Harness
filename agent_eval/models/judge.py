"""Judge and evaluation scoring models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_eval.models.base import BaseSchema, Field


class RubricEvaluation(BaseSchema):
    """Evaluation result for an individual rubric criterion."""
    criterion: str = Field(description="Description of the rubric requirement")
    score: float = Field(description="Score between 0.0 and 1.0 for this criterion")
    passed: bool = Field(description="Whether this criterion was satisfied")
    explanation: str = Field(description="Judge's explanation for this score")


class DimensionScores(BaseSchema):
    """Scores broken down by evaluation dimensions."""
    correctness: float = Field(default=0.0, description="Task goal accomplishment accuracy (0.0 - 1.0)")
    tool_usage: float = Field(default=0.0, description="Correctness and relevance of tool invocations (0.0 - 1.0)")
    completeness: Optional[float] = Field(default=None, description="Degree to which all aspects were fulfilled (0.0 - 1.0)")
    hallucination_absence: Optional[float] = Field(default=None, description="Absence of fabricated information (0.0 - 1.0)")
    final_response: Optional[float] = Field(default=None, description="Quality and tone of final response (0.0 - 1.0)")
    custom: Dict[str, float] = Field(default_factory=dict, description="Additional custom dimension scores")


class JudgeResult(BaseSchema):
    """Structured evaluation output produced by an LLM-as-a-judge or heuristic evaluator."""
    task_id: str = Field(description="Identifier of the evaluated task")
    run_id: str = Field(description="Identifier of the evaluation run")
    overall_score: float = Field(description="Normalized overall score between 0.0 and 1.0")
    passed: bool = Field(description="Whether the trajectory meets the passing threshold")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="Scores mapped by dimension name")
    rubric_evaluations: List[RubricEvaluation] = Field(default_factory=list, description="Per-criterion rubric scores")
    explanation: str = Field(default="", description="Summary justification for the evaluation score")
    judge_model: Optional[str] = Field(default=None, description="Model used as evaluator, e.g. gemini-2.5-pro")
    latency_ms: Optional[float] = Field(default=None, description="Evaluation latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Evaluation run metadata")

