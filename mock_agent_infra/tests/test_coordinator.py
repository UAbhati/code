"""Unit tests for verifier and coordinator revision."""

from __future__ import annotations

import unittest

from payment_agent.coordinator import Coordinator
from payment_agent.model import MockModelClient, ModelResponse, ToolCall
from payment_agent.tools import ToolRegistry
from payment_agent.verifier import verify_report


def _evidence(txn_id: str, bank_ref: str, topic: str):
    reg = ToolRegistry()
    return [
        reg.execute("lookup_transaction", {"transaction_id": txn_id}),
        reg.execute("lookup_bank_status", {"bank_ref": bank_ref}),
        reg.execute("lookup_payment_guideline", {"topic": topic}),
    ]


def _good_report() -> str:
    from payment_agent.agent import Agent

    return Agent(model=MockModelClient()).run("TXN101")


class VerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = _evidence("TXN101", "BR-7788", "INSUFFICIENT_FUNDS")
        self.report = _good_report()

    def test_correct_report_passes(self) -> None:
        self.assertTrue(verify_report(self.report, self.evidence).passed)

    def test_wrong_status_fails(self) -> None:
        bad = self.report.replace("Status: failed", "Status: completed")
        v = verify_report(bad, self.evidence)
        self.assertFalse(v.passed)
        self.assertIn("Status claimed", v.issues[0])

    def test_wrong_bank_status_fails(self) -> None:
        bad = self.report.replace("Bank status: rejected", "Bank status: approved")
        self.assertFalse(verify_report(bad, self.evidence).passed)

    def test_unsupported_action_fails(self) -> None:
        bad = self.report + "\n  * Issue a full refund to the payer."
        v = verify_report(bad, self.evidence)
        self.assertFalse(v.passed)

    def test_money_movement_claim_fails(self) -> None:
        bad = self.report + "\nThe payment was refunded and funds were returned."
        v = verify_report(bad, self.evidence)
        self.assertTrue(any("money-movement" in i for i in v.issues))

    def test_keywords_alone_do_not_pass(self) -> None:
        v = verify_report("status bank recommended action", self.evidence)
        self.assertFalse(v.passed)

    def test_guideline_quote_about_funds_is_not_flagged(self) -> None:
        ev = _evidence("TXN103", "BR-9900", "COMPLIANCE_HOLD")
        report = _report_for("TXN103")
        self.assertIn("Do not release funds", report)
        self.assertTrue(verify_report(report, ev).passed)


def _report_for(txn_id: str) -> str:
    from payment_agent.agent import Agent

    return Agent(model=MockModelClient()).run(txn_id)


class CoordinatorTests(unittest.TestCase):
    def test_successful_investigation_is_accepted(self) -> None:
        result = Coordinator().investigate("Please investigate TXN101")
        self.assertTrue(result.accepted)
        self.assertEqual(result.revisions, 0)
        self.assertIn("ACCEPTED", result.final_response)

    def test_compliance_hold_path(self) -> None:
        result = Coordinator().investigate("Look into TXN103")
        self.assertIn("COMPLIANCE_HOLD", result.research)
        self.assertTrue(result.accepted)

    def test_unknown_transaction_is_rejected(self) -> None:
        result = Coordinator().investigate("TXN999")
        self.assertFalse(result.accepted)
        self.assertEqual(result.revisions, 1)  # bounded to one revision

    def test_revision_corrects_report(self) -> None:
        """First report is wrong; feedback leads to a corrected second one."""
        good = _good_report()

        class Flaky:
            def __init__(self) -> None:
                self.inner = MockModelClient()
                self.prompts: list[str] = []

            def complete(self, messages, tools=None):
                prompt = messages[1].content
                response = self.inner.complete(messages, tools)
                if response.is_final:
                    self.prompts.append(prompt)
                    if "verifier found" not in prompt:
                        return ModelResponse(
                            content=response.content.replace(
                                "Status: failed", "Status: completed"
                            )
                        )
                return response

        model = Flaky()
        result = Coordinator(researcher_model=model).investigate("TXN101")
        self.assertEqual(result.revisions, 1)
        self.assertFalse(result.attempts[0].verification.passed)
        self.assertTrue(result.accepted)
        self.assertEqual(result.research, good)

    def test_revision_is_bounded_even_if_still_failing(self) -> None:
        class AlwaysWrong:
            def complete(self, messages, tools=None):
                return ModelResponse(content="Investigation for TXN101:\n- Status: ok")

        result = Coordinator(
            researcher_model=AlwaysWrong(), max_revisions=10
        ).investigate("TXN101")
        self.assertFalse(result.accepted)
        self.assertEqual(len(result.attempts), 2)


if __name__ == "__main__":
    unittest.main()
