"""Tests for deterministic binary rubric evaluation."""

from __future__ import annotations

from pathlib import Path

from agent_eval.judge import BinaryRubricJudge
from agent_eval.models.trajectory import ToolCall, ToolResponse, Trajectory
from agent_eval.schema.dataset import EvaluationDataset


def load_refund_task():
    dataset = EvaluationDataset.load_from_yaml(
        Path(__file__).resolve().parent.parent / "datasets" / "refund.yaml"
    )
    task = dataset.get_task("refund_order_1234")
    assert task is not None
    return task


def refund_trace(tool_names: list[str]) -> Trajectory:
    trajectory = Trajectory(run_id="judge-test", task_id="refund_order_1234")
    outputs = {
        "lookup_order": {
            "order_id": "1234",
            "status": "delivered",
            "amount": 100.0,
        },
        "check_refund_eligibility": {"order_id": "1234", "eligible": True},
        "refund_order": {"order_id": "1234", "refund_status": "processed"},
    }
    for tool_name in tool_names:
        arguments = {"order_id": "1234"}
        trajectory.record_tool_call(ToolCall(tool=tool_name, arguments=arguments))
        trajectory.record_tool_response(
            ToolResponse(tool=tool_name, input=arguments, output=outputs[tool_name])
        )
    trajectory.set_final_response(
        "Your refund for order 1234 has been processed."
    )
    return trajectory


def test_judge_scores_each_binary_rubric_check() -> None:
    result = BinaryRubricJudge().evaluate(
        load_refund_task(),
        refund_trace(
            ["lookup_order", "check_refund_eligibility", "refund_order"]
        ),
    )

    assert result.passed
    assert result.overall_score == 1.0
    assert len(result.rubric_evaluations) == 4
    assert all(item.passed for item in result.rubric_evaluations)


def test_judge_fails_invalid_tool_sequence() -> None:
    result = BinaryRubricJudge().evaluate(
        load_refund_task(),
        refund_trace(
            ["lookup_order", "refund_order", "check_refund_eligibility"]
        ),
    )

    assert not result.passed
    assert result.overall_score < 1.0
    assert not result.rubric_evaluations[0].passed