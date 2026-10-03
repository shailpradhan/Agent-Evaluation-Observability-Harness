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
            p95_latency_ms=3200.0
        )
        self.assertEqual(run.mean_score, 0.89)
        self.assertEqual(run.pass_rate, 0.92)
        self.assertEqual(run.total_tasks, 25)

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

