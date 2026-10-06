"""Run one task through agent execution, trace replay, judging, and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from agent_eval.agent.agent import Agent
from agent_eval.agent.models import AgentResult
from agent_eval.judge.judge import BinaryRubricJudge
from agent_eval.models.judge import JudgeResult
from agent_eval.models.metrics import EvalResult
from agent_eval.models.trajectory import Trajectory
from agent_eval.replay.engine import ReplayEngine, ReplayOutcome
from agent_eval.schema.task import Task
from agent_eval.tracing import TraceRunner


@dataclass
class EvaluationOutcome:
    """Artifacts and final score from one complete task evaluation."""

    task: Task
    agent_result: AgentResult
    trace: Trajectory
    replay: ReplayOutcome
    judge_result: JudgeResult
    score: EvalResult


class EvaluationPipeline:
    """Complete the Phase 2 vertical slice for a single evaluation task."""

    def __init__(
        self,
        agent: Agent,
        replay_engine: ReplayEngine | None = None,
        judge: BinaryRubricJudge | None = None,
        trace_runner: TraceRunner | None = None,
    ) -> None:
        self.agent = agent
        self.replay_engine = replay_engine or ReplayEngine()
        self.judge = judge or BinaryRubricJudge()
        self.trace_runner = trace_runner or TraceRunner()

    def evaluate(self, task: Task, *, run_id: str | None = None) -> EvaluationOutcome:
        """Execute, trace, replay, judge, and score one task."""
        evaluation_run_id = run_id or str(uuid4())
        traced_run = self.trace_runner.run(
            self.agent,
            task,
            run_id=evaluation_run_id,
        )
        agent_result = traced_run.agent_result
        trace = traced_run.trajectory

        replay = self.replay_engine.replay(self.agent, task, trace)
        replay_trace = replay.trajectory

        judge_result = self.judge.evaluate(
            task,
            replay_trace,
            run_id=evaluation_run_id,
        )
        resolved = bool(replay.agent_result.final_response.strip())
        score = EvalResult(
            result_id=str(uuid4()),
            run_id=evaluation_run_id,
            task_id=task.id,
            score=judge_result.overall_score,
            passed=judge_result.passed,
            latency_ms=trace.total_latency_ms,
            tokens=trace.total_tokens,
            resolved=resolved,
            tool_calls=len(trace.tool_calls),
            agent_turns=len(trace.llm_calls),
        )
        return EvaluationOutcome(
            task=task,
            agent_result=agent_result,
            trace=trace,
            replay=replay,
            judge_result=judge_result,
            score=score,
        )