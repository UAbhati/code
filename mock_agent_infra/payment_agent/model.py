"""Model client interface and a deterministic mock implementation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class InvalidModelResponse(Exception):
    """Raised when a model response is neither a tool call nor a final answer."""


@dataclass
class ModelResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_final(self) -> bool:
        """A final answer has non-blank text and no tool calls."""
        return not self.tool_calls and bool(self.content.strip())

    def validate(self) -> None:
        if not self.tool_calls and not self.content.strip():
            raise InvalidModelResponse(
                "Model returned neither tool calls nor a final answer."
            )


class ModelClient(Protocol):
    """Interface for LLM clients used by the agent loop.

    ``tools`` is a list of provider-neutral tool definitions:
    ``{"name", "description", "parameters": <JSON schema>}``. A real client
    maps these to its provider's function-calling format and returns structured
    ``ToolCall`` objects (preserving the provider's call ids) or final content.
    Tool results arrive as ``role="tool"`` messages whose ``tool_call_id``
    matches the originating call and whose content is JSON.
    """

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        """Return either tool calls or a final natural-language answer."""


class MockModelClient:
    """
    Scripted stand-in for an LLM, used for tests and offline demos.

    It does NOT choose tools dynamically: it follows a fixed lookup order.
    The orchestration (tool schemas, validation, loop, verification) is what
    it exercises; see ``providers.OpenAIChatClient`` for a real model.

    Behavior:
    1. Extract a transaction id (e.g. TXN101) from the latest user message.
    2. Call lookup_transaction, then lookup_bank_status, then guideline lookup.
    3. Emit a final investigation summary.
    """

    def __init__(self) -> None:
        self._call_counter = 0

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        self._call_counter += 1
        call_id = f"call_{self._call_counter}"  # unique per mock instance

        user_text = _latest_user_text(messages)
        txn_id = _extract_txn_id(user_text)

        tool_results = [m for m in messages if m.role == "tool"]
        txn_result = _find_tool_result(tool_results, "lookup_transaction")
        bank_result = _find_tool_result(tool_results, "lookup_bank_status")
        guideline_result = _find_tool_result(tool_results, "lookup_payment_guideline")

        if txn_id is None:
            return ModelResponse(
                content=(
                    "I need a transaction id (for example TXN101) to investigate "
                    "a payment."
                )
            )

        if txn_result is None:
            return ModelResponse(
                tool_calls=[
                    ToolCall(
                        id=call_id,
                        name="lookup_transaction",
                        arguments={"transaction_id": txn_id},
                    )
                ]
            )

        if not txn_result.get("ok"):
            return ModelResponse(
                content=(
                    f"Could not investigate {txn_id}: "
                    f"{txn_result.get('error', 'unknown error')}."
                )
            )

        txn = txn_result.get("content") or {}
        bank_ref = txn.get("bank_ref")

        if bank_result is None and bank_ref:
            return ModelResponse(
                tool_calls=[
                    ToolCall(
                        id=call_id,
                        name="lookup_bank_status",
                        arguments={"bank_ref": bank_ref},
                    )
                ]
            )

        topic = _guideline_topic(txn)
        if guideline_result is None and topic:
            return ModelResponse(
                tool_calls=[
                    ToolCall(
                        id=call_id,
                        name="lookup_payment_guideline",
                        arguments={"topic": topic},
                    )
                ]
            )

        return ModelResponse(content=_build_summary(txn, bank_result, guideline_result))


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def _extract_txn_id(text: str) -> str | None:
    """Find an id like TXN101 (also accepts TXN-101 and normalizes it)."""
    match = re.search(r"TXN-?(\d+)", text.upper())
    return f"TXN{match.group(1)}" if match else None


def _find_tool_result(
    tool_messages: list[Message], tool_name: str
) -> dict[str, Any] | None:
    for message in tool_messages:
        parsed = _parse_tool_message(message.content)
        if parsed is not None and parsed.get("tool_name") == tool_name:
            return parsed
    return None


def _parse_tool_message(content: str) -> dict[str, Any] | None:
    """Parse a JSON tool-result message; None if malformed."""
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _guideline_topic(txn: dict[str, Any]) -> str | None:
    failure_code = txn.get("failure_code")
    if failure_code:
        return str(failure_code)
    status = txn.get("status")
    if status == "pending":
        return "PENDING"
    return None


def _build_summary(
    txn: dict[str, Any],
    bank_result: dict[str, Any] | None,
    guideline_result: dict[str, Any] | None,
) -> str:
    lines = [
        f"Investigation for {txn.get('transaction_id')}:",
        f"- Status: {txn.get('status')}",
        f"- Amount: {txn.get('amount')} {txn.get('currency')}",
        f"- Failure code: {txn.get('failure_code') or 'n/a'}",
    ]
    if bank_result and bank_result.get("ok"):
        bank = bank_result.get("content") or {}
        lines.append(
            f"- Bank status: {bank.get('rail_status')} ({bank.get('bank_name')}) — "
            f"{bank.get('rail_message')}"
        )
    elif bank_result and not bank_result.get("ok"):
        lines.append(f"- Bank lookup failed: {bank_result.get('error')}")

    if guideline_result and guideline_result.get("ok"):
        guide = guideline_result.get("content") or {}
        lines.append(f"- Guideline: {guide.get('summary')}")
        actions = guide.get("recommended_actions") or []
        if actions:
            lines.append("- Recommended actions:")
            for action in actions:
                lines.append(f"  * {action}")
    return "\n".join(lines)
