"""Unit tests for trajectory and execution models."""

import unittest
from datetime import datetime, timezone

from agent_eval.models.trajectory import (
    LLMCall,
    StepType,
    ToolCall,
    ToolResponse,
    Trajectory,
)


class TestTrajectoryModels(unittest.TestCase):
    def test_tool_call_and_response(self):
        call = ToolCall(
            tool="lookup_order",
            arguments={"order_id": "1234"},
            call_id="call_abc",
            timestamp=datetime.now(timezone.utc)
        )
        self.assertEqual(call.tool, "lookup_order")
        self.assertEqual(call.arguments["order_id"], "1234")

        response = ToolResponse(
            tool="lookup_order",
            input={"order_id": "1234"},
            output={"status": "delivered", "amount": 100},
            latency_ms=120.5,
            call_id="call_abc"
        )
        self.assertEqual(response.output["status"], "delivered")
        self.assertEqual(response.latency_ms, 120.5)

    def test_llm_call(self):
        llm = LLMCall(
            model="gemini-2.5-pro",
            prompt="Refund order #1234",
            response="Calling lookup_order",
            input_tokens=100,
            output_tokens=30,
            total_tokens=130,
            latency_ms=450.0
        )
        self.assertEqual(llm.model, "gemini-2.5-pro")
        self.assertEqual(llm.total_tokens, 130)
        self.assertEqual(llm.latency_ms, 450.0)

    def test_trajectory_accumulation(self):
        traj = Trajectory(
            run_id="run_101",
            task_id="refund_order_1234",
            agent_version="v1.0",
            prompt_version="v2.1",
            model_name="gemini-2.5-pro"
        )

        # 1. LLM call step
        llm1 = LLMCall(
            model="gemini-2.5-pro",
            prompt="User request",
            response="I will check your order.",
            input_tokens=50,
            output_tokens=20,
            total_tokens=70,
            latency_ms=300.0
        )
        traj.record_llm_call(llm1)

        # 2. Tool call step
        tc = ToolCall(tool="lookup_order", arguments={"order_id": "1234"})
        traj.record_tool_call(tc)

        # 3. Tool response step
        tr = ToolResponse(
            tool="lookup_order",
            input={"order_id": "1234"},
            output={"status": "delivered"},
            latency_ms=150.0
        )
        traj.record_tool_response(tr)

        # 4. Final response step
        traj.set_final_response("Order #1234 refund has been processed.")

        self.assertEqual(len(traj.steps), 4)
        self.assertEqual(traj.steps[0].type, StepType.LLM_CALL)
        self.assertEqual(traj.steps[1].type, StepType.TOOL_CALL)
        self.assertEqual(traj.steps[2].type, StepType.TOOL_RESPONSE)
        self.assertEqual(traj.steps[3].type, StepType.FINAL_RESPONSE)

        self.assertIn("lookup_order", traj.tool_names_called)
        self.assertEqual(traj.total_tokens, 70)
        self.assertEqual(traj.total_latency_ms, 450.0)
        self.assertEqual(traj.final_response, "Order #1234 refund has been processed.")


if __name__ == "__main__":
    unittest.main()

