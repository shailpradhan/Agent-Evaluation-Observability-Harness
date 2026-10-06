"""Deterministic binary rubric judging for recorded agent trajectories."""

from __future__ import annotations

from typing import Any

from agent_eval.models.judge import JudgeResult, RubricEvaluation
from agent_eval.models.trajectory import Trajectory
from agent_eval.schema.task import RubricCheck, Task


class BinaryRubricJudge:
    """Evaluate declared atomic assertions against a trajectory."""

    def evaluate(
        self,
        task: Task,
        trajectory: Trajectory,
        *,
        run_id: str | None = None,
    ) -> JudgeResult:
        if not task.rubric:
            raise ValueError(f"Task '{task.id}' has no binary rubric checks.")

        evaluations = [
            self._evaluate_check(check, trajectory) for check in task.rubric
        ]
        passed_count = sum(evaluation.passed for evaluation in evaluations)
        score = passed_count / len(evaluations)
        sequence_checks = [
            evaluation for evaluation, check in zip(evaluations, task.rubric)
            if check.kind == "tool_sequence"
        ]
        dimensions = {"correctness": score}
        if sequence_checks:
            dimensions["tool_usage"] = sum(
                evaluation.passed for evaluation in sequence_checks
            ) / len(sequence_checks)

        return JudgeResult(
            task_id=task.id,
            run_id=run_id or trajectory.run_id,
            overall_score=score,
            passed=passed_count == len(evaluations),
            dimension_scores=dimensions,
            rubric_evaluations=evaluations,
            explanation=(
                f"{passed_count} of {len(evaluations)} binary rubric checks passed."
            ),
            judge_model="deterministic-binary-rubric",
        )

    @staticmethod
    def _evaluate_check(
        check: RubricCheck,
        trajectory: Trajectory,
    ) -> RubricEvaluation:
        if check.kind == "tool_sequence":
            expected = check.expected
            if not isinstance(expected, list) or not all(
                isinstance(name, str) for name in expected
            ):
                raise ValueError(
                    f"Rubric check '{check.assertion}' expects a list of tool names."
                )
            actual = trajectory.tool_names_called
            passed = actual == expected
            evidence = f"Expected tool sequence {expected}; observed {actual}."
        elif check.kind == "tool_result_contains":
            expected = check.expected
            if not isinstance(expected, dict):
                raise ValueError(
                    f"Rubric check '{check.assertion}' expects a result mapping."
                )
            if not expected:
                raise ValueError(
                    f"Rubric check '{check.assertion}' must expect at least one field."
                )
            outputs = [
                response.output
                for response in trajectory.tool_responses
                if response.error is None
            ]
            passed = any(
                BinaryRubricJudge._mapping_contains(output, expected)
                for output in outputs
            )
            evidence = (
                f"Expected result fields {expected}; "
                f"observed successful tool outputs {outputs}."
            )
        elif check.kind == "final_response_contains":
            expected = check.expected
            if not isinstance(expected, str) or not expected:
                raise ValueError(
                    f"Rubric check '{check.assertion}' expects non-empty text."
                )
            actual = trajectory.final_response or ""
            passed = expected.casefold() in actual.casefold()
            evidence = f"Expected final response to contain {expected!r}; observed {actual!r}."
        else:
            raise ValueError(f"Unsupported rubric check kind: {check.kind}")

        return RubricEvaluation(
            assertion=check.assertion,
            passed=passed,
            explanation=evidence,
        )

    @staticmethod
    def _mapping_contains(actual: Any, expected: dict[str, Any]) -> bool:
        if not isinstance(actual, dict):
            return False
        for key, expected_value in expected.items():
            if key not in actual:
                if not any(
                    BinaryRubricJudge._mapping_contains(value, {key: expected_value})
                    for value in actual.values()
                ):
                    return False
            elif isinstance(expected_value, dict):
                if not BinaryRubricJudge._mapping_contains(actual[key], expected_value):
                    return False
            elif actual[key] != expected_value:
                return False
        return True