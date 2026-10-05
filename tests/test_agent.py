"""Tests for the provider-independent agent layer."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

import agent_eval.agent.tools as tool_module
from agent_eval.agent import (
    Agent,
    FakeLLM,
    InvalidLLMResponseError,
    InvalidToolArgumentsError,
    MaxIterationsExceededError,
    Tool,
    ToolExecutionError,
    ToolRegistry,
    UnknownToolError,
    create_default_tools,
)
from agent_eval.agent.llm import LLM
from agent_eval.agent.tools import (
    check_refund_eligibility,
    lookup_order,
    refund_order,
)


class ScriptedLLM(LLM):
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.messages: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        return self.responses.pop(0)


def response(value: dict[str, Any]) -> str:
    return json.dumps(value)


def test_fake_llm_can_return_scripted_response() -> None:
    llm = FakeLLM(['{"final_response":"Done."}'])

    assert llm.generate([{"role": "user", "content": "anything"}]) == (
        '{"final_response":"Done."}'
    )


def test_fake_llm_drives_refund_workflow_deterministically() -> None:
    llm = FakeLLM()
    messages = [{"role": "user", "content": "Refund order 1234"}]

    first = json.loads(llm.generate(messages))
    messages.extend(
        [
            {"role": "assistant", "content": json.dumps(first)},
            {
                "role": "tool",
                "name": "lookup_order",
                "content": '{"order_id":"1234","status":"delivered","amount":100.0}',
            },
        ]
    )
    second = json.loads(llm.generate(messages))

    assert first["tool_call"]["name"] == "lookup_order"
    assert second["tool_call"]["name"] == "check_refund_eligibility"


def test_lookup_order_returns_seeded_order() -> None:
    assert lookup_order("1234") == {
        "order_id": "1234",
        "status": "delivered",
        "amount": 100.0,
    }


def test_lookup_order_rejects_unknown_order() -> None:
    with pytest.raises(ValueError, match="Order missing was not found"):
        lookup_order("missing")


def test_check_refund_eligibility_for_seeded_order() -> None:
    assert check_refund_eligibility("1234") == {
        "order_id": "1234",
        "eligible": True,
    }


def test_unknown_order_is_not_refund_eligible() -> None:
    assert check_refund_eligibility("missing") == {
        "order_id": "missing",
        "eligible": False,
    }


def test_refund_order_processes_eligible_order() -> None:
    tool_module._REFUND_RESULTS.clear()

    assert refund_order("1234") == {
        "order_id": "1234",
        "refund_status": "processed",
    }


def test_refund_order_rejects_unknown_and_ineligible_orders() -> None:
    with pytest.raises(ValueError, match="Order missing was not found"):
        refund_order("missing")

    with pytest.raises(ValueError, match="Order 5678 is not eligible"):
        refund_order("5678")


def test_repeated_refund_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_module._REFUND_RESULTS.clear()
    process_calls: list[str] = []

    def count_refund(order_id: str) -> dict[str, str]:
        process_calls.append(order_id)
        return {"order_id": order_id, "refund_status": "processed"}

    monkeypatch.setattr(tool_module, "_process_refund", count_refund)

    first_result = refund_order("1234")
    second_result = refund_order("1234")

    assert first_result == second_result
    assert process_calls == ["1234"]


def test_tool_registry_looks_up_injected_tools() -> None:
    registry = ToolRegistry(create_default_tools())

    assert registry.get("lookup_order") is not None
    assert registry.get("not_registered") is None
    assert registry.names == (
        "lookup_order",
        "check_refund_eligibility",
        "refund_order",
    )


def test_agent_runs_full_refund_workflow() -> None:
    agent = Agent(llm=FakeLLM(), tools=create_default_tools())

    result = agent.run("Refund order 1234")

    assert result.final_response == "Your refund for order 1234 has been processed."
    assert [call.name for call in result.tool_calls] == [
        "lookup_order",
        "check_refund_eligibility",
        "refund_order",
    ]
    assert result.tool_calls[-1].result["refund_status"] == "processed"


def test_agent_rejects_unknown_tool() -> None:
    llm = ScriptedLLM(
        response(
            {
                "tool_call": {
                    "name": "delete_everything",
                    "arguments": {"order_id": "1234"},
                }
            }
        )
    )
    agent = Agent(llm=llm, tools=create_default_tools())

    with pytest.raises(UnknownToolError, match="unknown tool"):
        agent.run("Do something")


def test_agent_rejects_invalid_tool_arguments() -> None:
    llm = ScriptedLLM(
        response(
            {
                "tool_call": {
                    "name": "lookup_order",
                    "arguments": {"wrong_argument": "1234"},
                }
            }
        )
    )
    agent = Agent(llm=llm, tools=create_default_tools())

    with pytest.raises(InvalidToolArgumentsError, match="Invalid arguments"):
        agent.run("Find an order")


def test_agent_wraps_tool_execution_failure() -> None:
    class EmptyInput(BaseModel):
        pass

    class ToolOutput(BaseModel):
        value: str

    def fail(_arguments: EmptyInput) -> ToolOutput:
        raise RuntimeError("backend unavailable")

    failing_tool = Tool(
        name="fail",
        description="A tool that fails.",
        function=fail,
        input_model=EmptyInput,
        output_model=ToolOutput,
    )
    llm = ScriptedLLM(response({"tool_call": {"name": "fail", "arguments": {}}}))
    agent = Agent(llm=llm, tools=[failing_tool])

    with pytest.raises(ToolExecutionError, match="backend unavailable"):
        agent.run("Run the failing tool")


def test_agent_rejects_invalid_tool_output() -> None:
    class EmptyInput(BaseModel):
        pass

    class ToolOutput(BaseModel):
        value: str

    def invalid_output(_arguments: EmptyInput) -> Any:
        return {"unexpected_field": "invalid"}

    invalid_tool = Tool(
        name="invalid_output",
        description="A tool that returns a value outside its output schema.",
        function=invalid_output,
        input_model=EmptyInput,
        output_model=ToolOutput,
    )
    llm = ScriptedLLM(
        response({"tool_call": {"name": "invalid_output", "arguments": {}}})
    )
    agent = Agent(llm=llm, tools=[invalid_tool])

    with pytest.raises(ToolExecutionError, match="invalid_output"):
        agent.run("Run the invalid-output tool")


def test_agent_rejects_invalid_llm_response() -> None:
    agent = Agent(llm=ScriptedLLM("not JSON"), tools=create_default_tools())

    with pytest.raises(InvalidLLMResponseError, match="valid JSON"):
        agent.run("Do something")


def test_agent_enforces_maximum_iterations() -> None:
    lookup_call = response(
        {
            "tool_call": {
                "name": "lookup_order",
                "arguments": {"order_id": "1234"},
            }
        }
    )
    agent = Agent(
        llm=ScriptedLLM(lookup_call, lookup_call, lookup_call),
        tools=create_default_tools(),
        max_iterations=2,
    )

    with pytest.raises(MaxIterationsExceededError, match="2 iterations"):
        agent.run("Find an order")