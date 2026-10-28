"""Tests for provider message translation (no network)."""

from __future__ import annotations

import json
import unittest

from payment_agent.model import InvalidModelResponse, Message, ToolCall
from payment_agent.providers import parse_openai_response, to_openai_messages


class ProviderTests(unittest.TestCase):
    def test_tool_call_ids_preserved(self) -> None:
        msgs = [
            Message(
                role="assistant",
                content="",
                tool_calls=[ToolCall("abc", "lookup_transaction", {"transaction_id": "TXN101"})],
            ),
            Message(role="tool", content="{}", tool_call_id="abc"),
        ]
        out = to_openai_messages(msgs)
        self.assertEqual(out[0]["tool_calls"][0]["id"], "abc")
        self.assertEqual(out[1]["tool_call_id"], "abc")

    def test_parse_tool_call(self) -> None:
        body = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "lookup_bank_status",
                                       "arguments": json.dumps({"bank_ref": "BR-7788"})}}]}}]}
        resp = parse_openai_response(body)
        self.assertEqual(resp.tool_calls[0].arguments, {"bank_ref": "BR-7788"})

    def test_malformed_rejected(self) -> None:
        with self.assertRaises(InvalidModelResponse):
            parse_openai_response({})


if __name__ == "__main__":
    unittest.main()
