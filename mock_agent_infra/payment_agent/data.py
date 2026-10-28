"""In-memory mock payment data for investigation demos."""

from __future__ import annotations

from typing import Any

TRANSACTIONS: dict[str, dict[str, Any]] = {
    "TXN101": {
        "transaction_id": "TXN101",
        "amount": 250.00,
        "currency": "USD",
        "status": "failed",
        "failure_code": "INSUFFICIENT_FUNDS",
        "payer": "alice@example.com",
        "payee": "merchant_acme",
        "bank_ref": "BR-7788",
        "created_at": "2026-10-27T10:15:00Z",
    },
    "TXN102": {
        "transaction_id": "TXN102",
        "amount": 89.50,
        "currency": "USD",
        "status": "pending",
        "failure_code": None,
        "payer": "bob@example.com",
        "payee": "merchant_beta",
        "bank_ref": "BR-8899",
        "created_at": "2026-10-28T08:00:00Z",
    },
    "TXN103": {
        "transaction_id": "TXN103",
        "amount": 1200.00,
        "currency": "EUR",
        "status": "failed",
        "failure_code": "COMPLIANCE_HOLD",
        "payer": "carol@example.com",
        "payee": "merchant_gamma",
        "bank_ref": "BR-9900",
        "created_at": "2026-10-26T14:30:00Z",
    },
}

BANK_STATUSES: dict[str, dict[str, Any]] = {
    "BR-7788": {
        "bank_ref": "BR-7788",
        "bank_name": "First National",
        "rail_status": "rejected",
        "rail_message": "Account balance below required amount",
        "last_updated": "2026-10-27T10:16:00Z",
    },
    "BR-8899": {
        "bank_ref": "BR-8899",
        "bank_name": "City Trust",
        "rail_status": "processing",
        "rail_message": "Awaiting settlement window",
        "last_updated": "2026-10-28T08:05:00Z",
    },
    "BR-9900": {
        "bank_ref": "BR-9900",
        "bank_name": "EuroClear Bank",
        "rail_status": "held",
        "rail_message": "Compliance review in progress",
        "last_updated": "2026-10-26T15:00:00Z",
    },
}

GUIDELINES: dict[str, dict[str, Any]] = {
    "INSUFFICIENT_FUNDS": {
        "topic": "INSUFFICIENT_FUNDS",
        "summary": "Payment rejected because the payer account lacked funds.",
        "recommended_actions": [
            "Ask the payer to fund the account and retry.",
            "Offer an alternate payment method.",
            "Do not retry automatically within 24 hours.",
        ],
        "sla_hours": 24,
    },
    "COMPLIANCE_HOLD": {
        "topic": "COMPLIANCE_HOLD",
        "summary": "Payment held pending compliance or sanctions review.",
        "recommended_actions": [
            "Escalate to the compliance team.",
            "Collect additional KYC documents from the payer.",
            "Do not release funds until the hold is cleared.",
        ],
        "sla_hours": 72,
    },
    "PENDING": {
        "topic": "PENDING",
        "summary": "Payment is still processing on the bank rail.",
        "recommended_actions": [
            "Wait for the next settlement window.",
            "Re-check bank status after 2 hours.",
            "Notify the customer that no action is required yet.",
        ],
        "sla_hours": 4,
    },
}
