"""Run one full refund evaluation with ``python -m agent_eval.evaluation.demo``."""

from pathlib import Path

from agent_eval.agent import Agent, FakeLLM, create_default_tools
from agent_eval.evaluation.pipeline import EvaluationPipeline
from agent_eval.schema.dataset import EvaluationDataset


def main() -> None:
    dataset_path = Path(__file__).resolve().parents[2] / "datasets" / "refund.yaml"
    dataset = EvaluationDataset.load_from_yaml(dataset_path)
    task = dataset.get_task("refund_order_1234")
    if task is None:
        raise RuntimeError("The refund demonstration task is missing from the dataset.")

    agent = Agent(
        llm=FakeLLM(),
        tools=create_default_tools(),
        approval_handler=lambda tool_name, _arguments: tool_name == "refund_order",
    )
    outcome = EvaluationPipeline(agent).evaluate(task)

    print(f"Task: {task.id}")
    print(f"Agent response: {outcome.agent_result.final_response}")
    print(f"Trace tool sequence: {outcome.trace.tool_names_called}")
    print(
        "Replay response: "
        f"{outcome.replay.agent_result.final_response}"
    )
    print(
        f"Judge: {outcome.judge_result.passed} "
        f"({len(outcome.judge_result.rubric_evaluations)} binary checks, "
        f"score={outcome.judge_result.overall_score:.2f})"
    )
    print(
        f"Final score: passed={outcome.score.passed}, "
        f"tool_calls={outcome.score.tool_calls}, "
        f"agent_turns={outcome.score.agent_turns}"
    )


if __name__ == "__main__":
    main()
