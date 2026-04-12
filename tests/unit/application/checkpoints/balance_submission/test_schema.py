from __future__ import annotations

from tallylot.application.checkpoints.balance_submission import (
    BALANCE_REFERENCES_HEADER,
    BALANCE_SNAPSHOTS_HEADER,
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
)


def test_manual_balance_submission_headers_match_contract() -> None:
    assert BALANCE_SNAPSHOTS_HEADER == (
        "source",
        "account",
        "wallet",
        "instrument_id",
        "quantity",
        "target_at",
        "target_precision",
        "balance_kind",
        "notes",
    )
    assert BALANCE_REFERENCES_HEADER == (
        "source",
        "account",
        "wallet",
        "instrument_id",
        "quantity",
        "target_at",
        "target_precision",
        "balance_kind",
        "reference_kind",
        "observed_at",
        "observed_precision",
        "support_ref",
        "reviewed_by",
        "reviewed_at",
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
