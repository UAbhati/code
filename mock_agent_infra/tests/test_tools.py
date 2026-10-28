"""Unit tests for tool registry validation and execution."""

from __future__ import annotations

import unittest

from payment_agent.tools import ToolRegistry, ToolSpec


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()

    def test_lookup_transaction_success(self) -> None:
        result = self.registry.execute(
            "lookup_transaction", {"transaction_id": "TXN101"}
        )
        self.assertTrue(result.ok)
        assert isinstance(result.content, dict)
        self.assertEqual(result.content["failure_code"], "INSUFFICIENT_FUNDS")

    def test_lookup_bank_status_success(self) -> None:
        result = self.registry.execute("lookup_bank_status", {"bank_ref": "BR-7788"})
        self.assertTrue(result.ok)
        assert isinstance(result.content, dict)
        self.assertEqual(result.content["rail_status"], "rejected")

    def test_lookup_guideline_success(self) -> None:
        result = self.registry.execute(
            "lookup_payment_guideline", {"topic": "INSUFFICIENT_FUNDS"}
        )
        self.assertTrue(result.ok)
        assert isinstance(result.content, dict)
        self.assertIn("recommended_actions", result.content)

    def test_unknown_tool(self) -> None:
        result = self.registry.execute("not_a_tool", {"x": 1})
        self.assertFalse(result.ok)
        self.assertIn("Unknown tool", result.error or "")

    def test_missing_required_args(self) -> None:
        result = self.registry.execute("lookup_transaction", {})
        self.assertFalse(result.ok)
        self.assertIn("Missing required arguments", result.error or "")

    def test_empty_required_args(self) -> None:
        result = self.registry.execute(
            "lookup_transaction", {"transaction_id": ""}
        )
        self.assertFalse(result.ok)
        self.assertIn("Empty required arguments", result.error or "")

    def test_tool_not_found_data(self) -> None:
        result = self.registry.execute(
            "lookup_transaction", {"transaction_id": "TXN000"}
        )
        self.assertFalse(result.ok)
        self.assertIn("not found", result.error or "")

    def test_tool_handler_failure(self) -> None:
        def boom(_: dict) -> dict:
            raise RuntimeError("boom")

        registry = ToolRegistry(tools=())
        registry.register(
            ToolSpec(
                name="broken",
                description="always fails",
                properties={"x": {"type": "string"}},
                required=("x",),
                handler=boom,
            )
        )
        result = registry.execute("broken", {"x": "1"})
        self.assertFalse(result.ok)
        self.assertIn("Tool failure", result.error or "")

    def test_unexpected_argument_rejected(self) -> None:
        result = self.registry.execute(
            "lookup_transaction", {"transaction_id": "TXN101", "extra": 1}
        )
        self.assertFalse(result.ok)
        self.assertIn("Unexpected arguments", result.error or "")

    def test_wrong_type_rejected(self) -> None:
        result = self.registry.execute("lookup_transaction", {"transaction_id": 101})
        self.assertFalse(result.ok)
        self.assertIn("must be of type", result.error or "")

    def test_bad_format_rejected(self) -> None:
        result = self.registry.execute("lookup_transaction", {"transaction_id": "abc"})
        self.assertIn("invalid format", result.error or "")


if __name__ == "__main__":
    unittest.main()
