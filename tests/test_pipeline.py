"""End-to-end Phase 2 evaluation workflow tests."""

from __future__ import annotations

from pathlib import Path

from agent_eval.agent import Agent, FakeLLM, create_default_tools
from agent_eval.evaluation import EvaluationPipeline
from agent_eval.schema.dataset import EvaluationDataset


def test_refund_task_runs_agent_trace_replay_judge_and_score() -> None:
    dataset = EvaluationDataset.load_from_yaml(
        Path(__file__).resolve().parent.parent / "datasets" / "refund.yaml"
    )
    task = dataset.get_task("refund_order_1234")
    assert task is not None
    agent = Agent(
        llm=FakeLLM(),
        tools=create_default_tools(),
        approval_handler=lambda _name, _arguments: True,
    )

    outcome = EvaluationPipeline(agent).evaluate(task, run_id="phase-two-test")

    assert outcome.agent_result.final_response == (
        "Your refund for order 1234 has been processed."
    )
    assert outcome.trace.task_id == task.id
    assert outcome.trace.tool_names_called == [
        "lookup_order",
        "check_refund_eligibility",
        "refund_order",
    ]
    assert len(outcome.trace.llm_calls) == 4
    assert outcome.replay.agent_result.final_response == (
        outcome.agent_result.final_response
    )
    assert outcome.judge_result.passed
    assert outcome.score.passed
    assert outcome.score.score == 1.0
    assert outcome.score.resolved is True
    assert outcome.score.tool_calls == 3
    assert outcome.score.agent_turns == 4