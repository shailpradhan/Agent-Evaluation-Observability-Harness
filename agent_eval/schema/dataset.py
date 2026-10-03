"""Dataset schema and loader utilities for evaluation task corpora."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from agent_eval.models.base import BaseSchema, Field
from agent_eval.schema.task import Task


class EvaluationDataset(BaseSchema):
    """A versioned collection of evaluation tasks forming a test corpus."""
    version: str = Field(default="1.0.0", description="Semver version of the dataset")
    name: str = Field(default="evaluation_dataset", description="Dataset identifier or name")
    description: Optional[str] = Field(default=None, description="Detailed description of dataset purpose")
    tasks: List[Task] = Field(default_factory=list, description="List of tasks in this dataset")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset metadata")

    def __init__(self, **kwargs: Any) -> None:
        raw_tasks = kwargs.get("tasks", [])
        validated_tasks: List[Task] = []
        for t in raw_tasks:
            if isinstance(t, Task):
                validated_tasks.append(t)
            elif isinstance(t, dict):
                validated_tasks.append(Task(**t))
            else:
                raise TypeError(f"Expected Task or dict, got {type(t)}")
        kwargs["tasks"] = validated_tasks
        super().__init__(**kwargs)

    @property
    def task_ids(self) -> List[str]:
        """Return a list of all task IDs present in the dataset."""
        return [task.id for task in self.tasks]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Look up a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def add_task(self, task: Task) -> None:
        """Add a task to the dataset, enforcing unique task IDs."""
        if self.get_task(task.id) is not None:
            raise ValueError(f"Task with ID '{task.id}' already exists in dataset.")
        self.tasks.append(task)

    @classmethod
    def load_from_dict(cls, data: Union[Dict[str, Any], List[Dict[str, Any]]], name: str = "dataset") -> EvaluationDataset:
        """Load an EvaluationDataset from a dictionary or list of task dicts."""
        if isinstance(data, list):
            # Formatted as a bare list of tasks
            tasks = [Task(**item) for item in data]
            return cls(version="1.0.0", name=name, tasks=tasks)
        elif isinstance(data, dict):
            # Formatted with metadata wrapper
            version = str(data.get("version", "1.0.0"))
            dataset_name = str(data.get("name", name))
            description = data.get("description")
            raw_tasks = data.get("tasks", [])
            tasks = [Task(**item) if isinstance(item, dict) else item for item in raw_tasks]
            metadata = data.get("metadata", {})
            return cls(version=version, name=dataset_name, description=description, tasks=tasks, metadata=metadata)
        raise TypeError(f"Expected dict or list, got {type(data)}")

    @classmethod
    def load_from_yaml(cls, path: Union[str, Path]) -> EvaluationDataset:
        """Load an EvaluationDataset from a YAML file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        default_name = file_path.stem
        return cls.load_from_dict(data, name=default_name)

    @classmethod
    def load_from_json(cls, path: Union[str, Path]) -> EvaluationDataset:
        """Load an EvaluationDataset from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        default_name = file_path.stem
        return cls.load_from_dict(data, name=default_name)

    def to_yaml(self, path: Optional[Union[str, Path]] = None) -> str:
        """Serialize dataset to YAML string and optionally write to file."""
        data = self.model_dump(mode="json")
        yaml_content = yaml.dump(data, sort_keys=False, default_flow_style=False)
        if path:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
        return yaml_content

    def to_json(self, path: Optional[Union[str, Path]] = None, indent: int = 2) -> str:
        """Serialize dataset to JSON string and optionally write to file."""
        json_content = self.model_dump_json(indent=indent)
        if path:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_content)
        return json_content

