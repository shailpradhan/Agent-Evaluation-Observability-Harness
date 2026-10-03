"""Base schema definitions for agent-eval-harness.

Provides a dual-mode BaseSchema:
- If pydantic is installed, inherits from pydantic.BaseModel.
- If pydantic is not yet installed in the current environment, provides a
  zero-dependency fallback implementation providing model_dump, model_validate,
  model_dump_json, and standard field initialization.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T", bound="BaseSchema")

try:
    from pydantic import BaseModel as _PydanticBaseModel
    from pydantic import ConfigDict, Field

    _PYDANTIC_AVAILABLE = True

    class BaseSchema(_PydanticBaseModel):
        """Pydantic-backed base schema."""
        model_config = ConfigDict(
            arbitrary_types_allowed=True, # This setting allows you to use arbitrary Python classes as field types.
            populate_by_name=True,
            extra="ignore",
        )

except ImportError:
    _PYDANTIC_AVAILABLE = False

    def Field(default: Any = ..., default_factory: Any = None, description: Optional[str] = None, **kwargs: Any) -> Any:  # type: ignore
        """Lightweight fallback for pydantic.Field."""
        if default_factory is not None:
            return default_factory()
        return default

    class BaseSchema:  # type: ignore
        """Pure-Python fallback base schema for environments without pydantic installed."""

        def __init__(self, **kwargs: Any) -> None:
            # Collect annotations from class and all bases
            annotations: Dict[str, Any] = {}
            for cls in reversed(self.__class__.__mro__):
                if hasattr(cls, "__annotations__"):
                    annotations.update(cls.__annotations__)

            # Set values from kwargs or class defaults
            for key in annotations:
                if key in kwargs:
                    val = kwargs[key]
                elif hasattr(self.__class__, key):
                    default_val = getattr(self.__class__, key)
                    if callable(default_val) and not isinstance(default_val, type):
                        val = default_val()
                    else:
                        val = default_val
                else:
                    val = None
                setattr(self, key, val)

            # Assign any extra kwargs provided
            for key, val in kwargs.items():
                if key not in annotations:
                    setattr(self, key, val)

        def model_dump(self, mode: str = "python", exclude_none: bool = False) -> Dict[str, Any]:
            """Dump schema instance to dictionary."""
            result: Dict[str, Any] = {}
            for key, val in self.__dict__.items():
                if key.startswith("_"):
                    continue
                if exclude_none and val is None:
                    continue
                result[key] = self._serialize_value(val, mode=mode, exclude_none=exclude_none)
            return result

        @classmethod
        def _serialize_value(cls, val: Any, mode: str = "python", exclude_none: bool = False) -> Any:
            if hasattr(val, "model_dump"):
                return val.model_dump(mode=mode, exclude_none=exclude_none)
            elif isinstance(val, list):
                return [cls._serialize_value(item, mode=mode, exclude_none=exclude_none) for item in val]
            elif isinstance(val, dict):
                return {k: cls._serialize_value(v, mode=mode, exclude_none=exclude_none) for k, v in val.items()}
            elif isinstance(val, datetime):
                return val.isoformat() if mode == "json" else val
            elif hasattr(val, "value"):  # Enum
                return val.value
            return val

        def model_dump_json(self, indent: Optional[int] = None) -> str:
            """Dump schema instance to JSON string."""
            return json.dumps(self.model_dump(mode="json"), indent=indent, default=str)

        @classmethod
        def model_validate(cls: Type[T], obj: Any) -> T:
            """Validate and construct instance from dict or object."""
            if isinstance(obj, cls):
                return obj
            if isinstance(obj, dict):
                return cls(**obj)
            raise TypeError(f"Expected dict or {cls.__name__}, got {type(obj)}")

        def __repr__(self) -> str:
            attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_"))
            return f"{self.__class__.__name__}({attrs})"

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, self.__class__):
                return self.model_dump() == other.model_dump()
            return False


__all__ = ["BaseSchema", "Field"]

