"""Unit tests for Task and EvaluationDataset schema."""

import unittest
from pathlib import Path

from agent_eval.schema.dataset import EvaluationDataset
from agent_eval.schema.task import Task


class TestTaskSchema(unittest.TestCase):
    def test_valid_task_creation(self):
        task = Task(
            id="refund_order_1234",
            prompt="Refund order #1234",
            expected_outcome={"refund_processed": True},
            expected_tools=["lookup_order", "check_refund_policy", "refund_order"],
            rubric=["Correct order identified", "Refund executed"],
            metadata={"difficulty": "easy"}
        )
        self.assertEqual(task.id, "refund_order_1234")
        self.assertEqual(task.prompt, "Refund order #1234")
        self.assertEqual(len(task.expected_tools), 3)
        self.assertEqual(len(task.rubric), 2)
        self.assertTrue(task.expected_outcome["refund_processed"])

    def test_empty_id_raises_error(self):
        with self.assertRaises(ValueError):
            Task(id="", prompt="Refund order #1234")

    def test_empty_prompt_raises_error(self):
        with self.assertRaises(ValueError):
            Task(id="task_1", prompt="   ")

    def test_dataset_operations(self):
        dataset = EvaluationDataset(version="1.0.0", name="test_suite")
        task = Task(id="t1", prompt="Test prompt")
        dataset.add_task(task)

        self.assertEqual(len(dataset.tasks), 1)
        self.assertIn("t1", dataset.task_ids)
        self.assertEqual(dataset.get_task("t1").prompt, "Test prompt")
        self.assertIsNone(dataset.get_task("nonexistent"))

        # Duplicate ID check
        with self.assertRaises(ValueError):
            dataset.add_task(Task(id="t1", prompt="Duplicate ID"))

    def test_load_refund_yaml(self):
        dataset_path = Path(__file__).resolve().parent.parent / "datasets" / "refund.yaml"
        dataset = EvaluationDataset.load_from_yaml(dataset_path)

        self.assertEqual(dataset.version, "1.0.0")
        self.assertEqual(dataset.name, "refund_tasks")
        self.assertEqual(len(dataset.tasks), 2)

        task1 = dataset.get_task("refund_order_1234")
        self.assertIsNotNone(task1)
        self.assertIn("lookup_order", task1.expected_tools)
        self.assertEqual(len(task1.rubric), 4)

        task2 = dataset.get_task("refund_ineligible_order")
        self.assertIsNotNone(task2)
        self.assertFalse(task2.expected_outcome["refund_processed"])

    def test_load_cancellation_yaml(self):
        dataset_path = Path(__file__).resolve().parent.parent / "datasets" / "cancellation.yaml"
        dataset = EvaluationDataset.load_from_yaml(dataset_path)

        self.assertEqual(dataset.name, "order_cancellation_tasks")
        self.assertEqual(len(dataset.tasks), 1)
        task = dataset.get_task("cancel_order_5678")
        self.assertIsNotNone(task)
        self.assertIn("cancel_order", task.expected_tools)

    def test_load_bare_list_format(self):
        bare_data = [
            {
                "id": "t1",
                "prompt": "Do task 1",
                "expected_tools": ["tool_a"],
                "rubric": ["Rubric 1"],
            },
            {
                "id": "t2",
                "prompt": "Do task 2",
            }
        ]
        dataset = EvaluationDataset.load_from_dict(bare_data, name="bare_dataset")
        self.assertEqual(dataset.name, "bare_dataset")
        self.assertEqual(len(dataset.tasks), 2)
        self.assertEqual(dataset.tasks[0].id, "t1")


if __name__ == "__main__":
    unittest.main()

