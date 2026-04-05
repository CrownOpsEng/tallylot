from __future__ import annotations

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_EVIDENCE_HEADER,
    BALANCES_HEADER,
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
)


def test_manual_balance_submission_headers_match_contract() -> None:
    assert BALANCES_HEADER == (
        "source",
        "account",
        "wallet",
        "instrument_id",
        "quantity",
        "as_of_at",
        "as_of_precision",
        "balance_kind",
        "notes",
    )
    assert BALANCE_EVIDENCE_HEADER == (
        "source",
        "account",
        "wallet",
        "instrument_id",
        "quantity",
        "as_of_at",
        "as_of_precision",
        "balance_kind",
        "evidence_ref",
        "notes",
    )
    assert LOCATION_INVENTORY_HEADER == (
        "source",
        "account",
        "wallet",
        "identifier_kind",
        "identifier_value",
        "network_scope",
        "controller",
        "confidence",
        "notes",
    )
    assert ISSUE_HEADER == (
        "file_name",
        "row_number",
        "column_name",
        "issue_kind",
        "message",
    )
