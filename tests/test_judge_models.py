"""Unit tests for judge scoring and rubric evaluation models."""

import unittest

from agent_eval.models.judge import (
    DimensionScores,
    JudgeResult,
    RubricEvaluation,
)


class TestJudgeModels(unittest.TestCase):
    def test_rubric_evaluation(self):
        item = RubricEvaluation(
            criterion="Correct order identified",
            score=1.0,
            passed=True,
            explanation="The agent extracted order #1234 correctly."
        )
        self.assertEqual(item.score, 1.0)
        self.assertTrue(item.passed)

    def test_dimension_scores(self):
        dims = DimensionScores(
            correctness=0.95,
            tool_usage=0.90,
            completeness=0.85,
            hallucination_absence=1.0,
            final_response=0.88
        )
        self.assertEqual(dims.correctness, 0.95)
        self.assertEqual(dims.hallucination_absence, 1.0)

    def test_judge_result(self):
        rubric_evals = [
            RubricEvaluation(criterion="Order identified", score=1.0, passed=True, explanation="OK"),
            RubricEvaluation(criterion="Refund executed", score=0.9, passed=True, explanation="Refund API called"),
        ]
        result = JudgeResult(
            task_id="refund_order_1234",
            run_id="run_001",
            overall_score=0.92,
            passed=True,
            dimension_scores={
                "correctness": 0.95,
                "tool_usage": 0.90,
                "final_response": 0.88,
            },
            rubric_evaluations=rubric_evals,
            explanation="Agent fulfilled all requirements accurately.",
            judge_model="gemini-2.5-pro",
            latency_ms=1250.0
        )

        self.assertEqual(result.overall_score, 0.92)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.rubric_evaluations), 2)
        self.assertEqual(result.dimension_scores["correctness"], 0.95)


if __name__ == "__main__":
    unittest.main()

