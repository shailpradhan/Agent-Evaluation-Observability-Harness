"""Tests for deterministic replay."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_eval.agent import Agent, FakeLLM, create_default_tools
from agent_eval.replay.engine import ReplayEngine, ReplayMismatchError
from agent_eval.schema.dataset import EvaluationDataset
from agent_eval.tracing import TraceRunner


def make_agent() -> Agent:
    return Agent(
        llm=FakeLLM(),
        tools=create_default_tools(),
        approval_handler=lambda _name, _arguments: True,
    )


def load_refund_task():
    dataset = EvaluationDataset.load_from_yaml(
        Path(__file__).resolve().parent.parent / "datasets" / "refund.yaml"
    )
    task = dataset.get_task("refund_order_1234")
    assert task is not None
    return task


def test_replay_reuses_recorded_llm_decisions_and_tool_results() -> None:
    agent = make_agent()
    task = load_refund_task()
    original = TraceRunner().run(agent, task, run_id="replay-test")

    replay = ReplayEngine().replay(agent, task, original.trajectory)

    assert replay.session.task_id == task.id
    assert len(replay.session.recorded_tools) == 3
    assert replay.agent_result.final_response == original.agent_result.final_response
    assert replay.trajectory.tool_names_called == (
        original.trajectory.tool_names_called
    )


def test_replay_fails_if_recorded_input_is_changed() -> None:
    agent = make_agent()
    task = load_refund_task()
    original = TraceRunner().run(agent, task, run_id="mismatch-test")
    original.trajectory.tool_calls[0].arguments["order_id"] = "other-order"

    with pytest.raises(ReplayMismatchError, match="mismatched tool call"):
        ReplayEngine().replay(agent, task, original.trajectory)


def test_replay_rejects_mismatched_recorded_call_and_response() -> None:
    agent = make_agent()
    task = load_refund_task()
    original = TraceRunner().run(agent, task, run_id="response-mismatch")
    original.trajectory.tool_responses[0].input["order_id"] = "different"

    with pytest.raises(ReplayMismatchError, match="mismatched tool call"):
        ReplayEngine().create_session(original.trajectory)