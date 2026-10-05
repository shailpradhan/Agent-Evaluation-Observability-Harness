"""Provider-neutral LLM interface and an offline deterministic implementation."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from agent_eval.agent.models import LLMDecision, ToolCallRequest


class LLM(ABC):
    """Interface implemented by real or simulated language-model providers."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]]) -> LLMDecision:
        """Return a normalized structured decision for the agent."""


class FakeLLM(LLM):
    """A deterministic refund-workflow simulator, not a reasoning model.

    Supply ``responses`` to script exact outputs. Without them, this fake
    implements only the demonstration refund workflow and returns a fixed
    explanation for other tasks.
    """

    def __init__(self, responses: Sequence[LLMDecision] | None = None) -> None:
        self._responses = tuple(responses) if responses is not None else None
        self._response_index = 0

    def generate(self, messages: list[dict[str, str]]) -> LLMDecision:
        if self._responses is not None:
            if self._response_index >= len(self._responses):
                raise RuntimeError("FakeLLM has no scripted responses remaining.")
            response = self._responses[self._response_index]
            self._response_index += 1
            return response

        task = next(
            (message["content"] for message in messages if message.get("role") == "user"),
            "",
        )
        if "refund" not in task.lower():
            return self._decision(
                final_response="FakeLLM only simulates the deterministic refund demonstration."
            )

        order_match = re.search(r"\border\s+#?([A-Za-z0-9_-]+)\b", task, re.IGNORECASE)
        if order_match is None:
            return self._decision(
                final_response="Please provide an order ID for the refund demonstration."
            )
        order_id = order_match.group(1)

        tool_messages = [
            message
            for message in messages
            if message.get("role") == "tool"
        ]
        if not tool_messages:
            return self._decision(
                tool_call={"name": "lookup_order", "arguments": {"order_id": order_id}}
            )

        last_tool = tool_messages[-1]
        if last_tool.get("name") == "lookup_order":
            return self._decision(
                tool_call={
                    "name": "check_refund_eligibility",
                    "arguments": {"order_id": order_id},
                }
            )
        if last_tool.get("name") == "check_refund_eligibility":
            eligibility = json.loads(last_tool["content"])
            if not eligibility["eligible"]:
                return self._decision(
                    final_response=f"Order {order_id} is not eligible for a refund."
                )
            return self._decision(
                tool_call={"name": "refund_order", "arguments": {"order_id": order_id}}
            )
        if last_tool.get("name") == "refund_order":
            return self._decision(
                final_response=f"Your refund for order {order_id} has been processed."
            )

        return self._decision(
            final_response="FakeLLM encountered an unsupported refund workflow step."
        )

    @staticmethod
    def _decision(
        *,
        tool_call: dict[str, object] | None = None,
        final_response: str | None = None,
    ) -> LLMDecision:
        if tool_call is not None:
            return LLMDecision(
                tool_call=ToolCallRequest.model_validate(tool_call)
            )
        if final_response is not None:
            return LLMDecision(final_response=final_response)
        raise ValueError("A tool call or final response is required.")
