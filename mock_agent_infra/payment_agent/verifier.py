"""Deterministic verifier: checks report claims against tool evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from payment_agent.tools import ToolResult

# Past-tense / completed money-movement assertions. The tools expose no
# refund, settlement, or transfer data, so such claims can never be supported
# unless the sentence is quoted verbatim from tool evidence.
_MONEY_MOVEMENT = re.compile(
    r"\b(refunded|refund (?:has been|was|is) (?:issued|processed|sent)|"
    r"settled|reversed|credited|debited|charged back|"
    r"funds? (?:has|have|was|were|is|are) (?:been )?"
    r"(?:released|returned|transferred|sent|moved|credited|debited|refunded)|"
    r"(?:released|returned|transferred) the (?:funds?|money|payment))\b",
    re.IGNORECASE,
)


@dataclass
class Verification:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.passed:
            return "PASS: all claims match tool evidence."
        return "FAIL:\n" + "\n".join(f"- {issue}" for issue in self.issues)


def _first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def _evidence(results: list[ToolResult], tool: str) -> dict[str, Any] | None:
    for r in results:
        if r.tool_name == tool and r.ok and isinstance(r.content, dict):
            return r.content
    return None


def verify_report(report: str, tool_results: list[ToolResult]) -> Verification:
    """Compare structured claims in ``report`` with retrieved evidence."""
    issues: list[str] = []
    txn = _evidence(tool_results, "lookup_transaction")
    bank = _evidence(tool_results, "lookup_bank_status")
    guideline = _evidence(tool_results, "lookup_payment_guideline")

    if txn is None:
        return Verification(False, ["No successful transaction lookup to verify against."])

    # 1. Transaction claims
    claimed_id = _first(r"Investigation for\s+(\S+?):", report)
    if claimed_id != txn["transaction_id"]:
        issues.append(
            f"Transaction id claimed {claimed_id!r}, evidence {txn['transaction_id']!r}."
        )
    claimed_status = _first(r"^\s*-\s*Status:\s*(\S+)", report)
    if claimed_status is None:
        issues.append("Report has no transaction status claim.")
    elif claimed_status.lower() != str(txn["status"]).lower():
        issues.append(
            f"Status claimed {claimed_status!r}, evidence {txn['status']!r}."
        )
    claimed_code = _first(r"^\s*-\s*Failure code:\s*(\S+)", report)
    expected_code = txn.get("failure_code") or "n/a"
    if claimed_code is None or claimed_code != expected_code:
        issues.append(f"Failure code claimed {claimed_code!r}, evidence {expected_code!r}.")

    # 2. Bank claims
    if txn.get("bank_ref"):
        if bank is None:
            issues.append("Bank status was never successfully retrieved.")
        else:
            claimed_rail = _first(r"^\s*-\s*Bank status:\s*(\S+)", report)
            if claimed_rail is None:
                issues.append("Report has no bank status claim.")
            elif claimed_rail.lower() != str(bank["rail_status"]).lower():
                issues.append(
                    f"Bank status claimed {claimed_rail!r}, evidence {bank['rail_status']!r}."
                )

    # 3. Guideline / recommendations
    expected_topic = txn.get("failure_code") or (
        "PENDING" if txn.get("status") == "pending" else None
    )
    allowed_actions: set[str] = set()
    if expected_topic:
        if guideline is None or guideline.get("topic") != expected_topic:
            issues.append(f"Applicable guideline {expected_topic!r} was not retrieved.")
        else:
            allowed_actions = set(guideline["recommended_actions"])
            claimed_summary = _first(r"^\s*-\s*Guideline:\s*(.+)$", report)
            if claimed_summary != guideline["summary"]:
                issues.append("Guideline summary does not match the retrieved guideline.")
    claimed_actions = re.findall(r"^\s*\*\s*(.+?)\s*$", report, re.MULTILINE)
    if expected_topic and not claimed_actions:
        issues.append("Report has no recommended actions.")
    for action in claimed_actions:
        if action not in allowed_actions:
            issues.append(f"Recommended action not supported by guideline: {action!r}.")

    # 4. Unsupported money-movement claims. Strip text quoted from evidence.
    scrubbed = report
    quoted: list[str] = list(allowed_actions)
    if bank:
        quoted.append(str(bank.get("rail_message", "")))
    if guideline:
        quoted.append(str(guideline.get("summary", "")))
    for text in filter(None, quoted):
        scrubbed = scrubbed.replace(text, "")
    for match in _MONEY_MOVEMENT.finditer(scrubbed):
        issues.append(f"Unsupported money-movement claim: {match.group(0)!r}.")

    return Verification(passed=not issues, issues=issues)
