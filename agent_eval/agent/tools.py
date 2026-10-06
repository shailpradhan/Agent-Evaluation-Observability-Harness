"""Tool definitions, registry, and deterministic in-memory refund tools."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolInput(BaseModel):
    """Base for tool inputs, rejecting misspelled or unexpected arguments."""

    model_config = ConfigDict(extra="forbid")


class OrderInput(ToolInput):
    order_id: str = Field(min_length=1)


class OrderDetails(BaseModel):
    order_id: str
    status: str
    amount: float


class RefundEligibility(BaseModel):
    order_id: str
    eligible: bool


class RefundResult(BaseModel):
    order_id: str
    refund_status: str


@dataclass(frozen=True)
class Tool(Generic[InputT, OutputT]):
    """A callable operation with validated input and output schemas."""

    name: str
    description: str
    function: Callable[[InputT], OutputT]
    input_model: type[InputT]
    output_model: type[OutputT]
    requires_approval: bool = False
    final_response_from_result: Callable[[OutputT], str] | None = None

    def validate_arguments(self, arguments: dict[str, Any]) -> InputT:
        """Validate raw LLM arguments against this tool's input schema."""
        return self.input_model.model_validate(arguments)

    def execute(self, arguments: InputT) -> OutputT:
        """Execute with validated arguments and validate the returned value."""
        raw_result = self.function(arguments)
        return self.output_model.model_validate(raw_result)

    def describe(self) -> dict[str, Any]:
        """Return the tool metadata and schemas for LLM context."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    """Discover tools by name while preserving their supplied order."""

    def __init__(self, tools: Iterable[Tool[Any, Any]]) -> None:
        self._tools: dict[str, Tool[Any, Any]] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool[Any, Any] | None:
        """Return a registered tool, or ``None`` when the name is unknown."""
        return self._tools.get(name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    @property
    def tools(self) -> tuple[Tool[Any, Any], ...]:
        """Return registered tools in their execution/discovery order."""
        return tuple(self._tools.values())

    def describe(self) -> list[dict[str, Any]]:
        return [tool.describe() for tool in self._tools.values()]


_ORDERS: dict[str, dict[str, str | float]] = {
    "1234": {"order_id": "1234", "status": "delivered", "amount": 100.0},
    "5678": {"order_id": "5678", "status": "cancelled", "amount": 75.0},
}
_REFUND_RESULTS: dict[str, dict[str, str]] = {}


def lookup_order(order_id: str) -> dict[str, str | float]:
    """Return seeded in-memory order details."""
    if order_id not in _ORDERS:
        raise ValueError(f"Order {order_id} was not found.")
    return dict(_ORDERS[order_id])


def check_refund_eligibility(order_id: str) -> dict[str, str | bool]:
    """Mark delivered seeded orders as eligible for a refund."""
    order = _ORDERS.get(order_id)
    eligible = order is not None and order["status"] == "delivered"
    return {"order_id": order_id, "eligible": eligible}


def refund_order(order_id: str) -> dict[str, str]:
    """Process an eligible refund once and return the same result on retries."""
    previous_result = _REFUND_RESULTS.get(order_id)
    if previous_result is not None:
        return dict(previous_result)

    if order_id not in _ORDERS:
        raise ValueError(f"Order {order_id} was not found.")

    eligibility = check_refund_eligibility(order_id)
    if not eligibility["eligible"]:
        raise ValueError(f"Order {order_id} is not eligible for a refund.")
    result = _process_refund(order_id)
    _REFUND_RESULTS[order_id] = result
    return dict(result)


def _process_refund(order_id: str) -> dict[str, str]:
    """Perform the deterministic in-memory refund operation."""
    return {"order_id": order_id, "refund_status": "processed"}


def _lookup_order_tool(arguments: OrderInput) -> OrderDetails:
    return OrderDetails.model_validate(lookup_order(arguments.order_id))


def _check_refund_eligibility_tool(arguments: OrderInput) -> RefundEligibility:
    return RefundEligibility.model_validate(
        check_refund_eligibility(arguments.order_id)
    )


def _refund_order_tool(arguments: OrderInput) -> RefundResult:
    return RefundResult.model_validate(refund_order(arguments.order_id))


def _refund_final_response(result: RefundResult) -> str:
    if result.refund_status == "processed":
        return f"Your refund for order {result.order_id} has been processed."
    return (
        f"Your refund for order {result.order_id} has status: "
        f"{result.refund_status}."
    )


def create_default_tools() -> list[Tool[Any, Any]]:
    """Create the initial deterministic order and refund tools."""
    return [
        Tool(
            name="lookup_order",
            description="Look up an order by its ID.",
            function=_lookup_order_tool,
            input_model=OrderInput,
            output_model=OrderDetails,
        ),
        Tool(
            name="check_refund_eligibility",
            description="Check whether an order is eligible for a refund.",
            function=_check_refund_eligibility_tool,
            input_model=OrderInput,
            output_model=RefundEligibility,
        ),
        Tool(
            name="refund_order",
            description="Process a refund for an eligible order.",
            function=_refund_order_tool,
            input_model=OrderInput,
            output_model=RefundResult,
            requires_approval=True,
            final_response_from_result=_refund_final_response,
        ),
    ]