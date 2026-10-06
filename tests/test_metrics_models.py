"""Unit tests for metrics and regression models."""

import unittest

from agent_eval.models.metrics import (
    EvalResult,
    EvalRun,
    RegressionReport,
)


class TestMetricsModels(unittest.TestCase):
    def test_eval_result(self):
        res = EvalResult(
            result_id="res_001",
            run_id="run_101",
            task_id="refund_order_1234",
            score=0.95,
            passed=True,
            latency_ms=1800.0,
            tokens=1240
        )
        self.assertEqual(res.score, 0.95)
        self.assertTrue(res.passed)
        self.assertEqual(res.tokens, 1240)

    def test_eval_result_accepts_safety_trajectory_and_side_effect_metrics(self):
        res = EvalResult(
            result_id="res_metrics",
            run_id="run_101",
            task_id="refund_order_1234",
            score=0.95,
            passed=True,
            resolved=True,
            safety_compliant=True,
            policy_violations=[],
            side_effects_intended=True,
            unexpected_side_effects=[],
            tool_calls=3,
            agent_turns=4,
        )

        self.assertTrue(res.safety_compliant)
        self.assertEqual(res.tool_calls, 3)
        self.assertEqual(res.agent_turns, 4)

    def test_metric_collections_are_not_shared_between_results(self):
        first = EvalResult(
            result_id="res_first",
            run_id="run_101",
            task_id="task_first",
            score=0.0,
            passed=False,
        )
        second = EvalResult(
            result_id="res_second",
            run_id="run_101",
            task_id="task_second",
            score=0.0,
            passed=False,
        )

        first.policy_violations.append("privacy")
        first.unexpected_side_effects.append("unexpected write")

        self.assertEqual(second.policy_violations, [])
        self.assertEqual(second.unexpected_side_effects, [])

    def test_eval_run(self):
        run = EvalRun(
            run_id="run_101",
            model_version="Model-A",
            prompt_version="v12",
            dataset_version="v5",
            mean_score=0.89,
            pass_rate=0.92,
            total_tasks=25,
            passed_tasks=23,
            failed_tasks=2,
            token_cost=1.42,
            cost_per_resolved_task=0.0617,
            resolved_tasks=23,
            total_tokens=31000,
            tokens_per_task=1240.0,
            tool_calls_per_task=2.4,
            agent_turns_per_task=3.2,
            p50_latency_ms=1700.0,
            p95_latency_ms=3200.0
        )
        self.assertEqual(run.mean_score, 0.89)
        self.assertEqual(run.pass_rate, 0.92)
        self.assertEqual(run.total_tasks, 25)
        self.assertEqual(run.resolved_tasks, 23)
        self.assertEqual(run.p50_latency_ms, 1700.0)
        self.assertEqual(run.p95_latency_ms, 3200.0)
        self.assertEqual(run.tokens_per_task, 1240.0)
        self.assertEqual(run.cost_per_resolved_task, 0.0617)

    def test_regression_report(self):
        report = RegressionReport(
            baseline_run_id="run_100",
            candidate_run_id="run_101",
            mean_score_diff=-0.12,
            pass_rate_diff=-0.12,
            latency_diff_ms=400.0,
            regression_detected=True,
            regressed_tasks=["refund_order_1234"],
            summary="Mean score dropped from 0.91 to 0.79. Pass rate dropped from 94% to 82%."
        )
        self.assertTrue(report.regression_detected)
        self.assertIn("refund_order_1234", report.regressed_tasks)
        self.assertEqual(report.mean_score_diff, -0.12)


if __name__ == "__main__":
    unittest.main()
