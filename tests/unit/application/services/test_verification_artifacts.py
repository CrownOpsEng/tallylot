from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.models.verification import VerificationCompareRequest
from crypto_reconciliation.application.services.verification import (
    VerificationCompareService,
    _summary_headers,
    _summary_rows,
)
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.verification import VerificationFixtureSet, write_verification_set


def test_summary_rows_stringifies_scalar_values_and_ignores_non_dict_entries() -> None:
    rows = _summary_rows(
        {
            "new_missing_transaction_rows": [
                {"Type": "Trade", "Count": 1},
                "ignore-me",
                {"Type": "Deposit", "Count": None},
            ]
        },
        "new_missing_transaction_rows",
    )

    assert rows == [
        {"Type": "Trade", "Count": "1"},
        {"Type": "Deposit", "Count": ""},
    ]


def test_summary_headers_expand_dynamic_columns() -> None:
    headers = _summary_headers(
        {
            "current_duplicate_transaction_rows": [
                {"Issue": "duplicate", "Trade ID": "tx-1"},
                {"Issue": "duplicate", "Reason": "hash"},
            ]
        },
        "current_duplicate_transaction_rows",
        default=("Issue",),
    )

    assert headers == ("Issue", "Reason", "Trade ID")


def test_verification_compare_service_writes_duplicate_rows_with_dynamic_headers(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    output_dir = tmp_path / "verification"
    previous_dir.mkdir()
    current_dir.mkdir()
    empty_fixture = VerificationFixtureSet(
        validate_rows=(),
        missing_rows=(),
        duplicate_rows=(),
        current_balance_rows=(),
        exchange_rows=(),
    )
    write_verification_set(previous_dir, empty_fixture)
    write_verification_set(current_dir, empty_fixture)
    write_rows(
        current_dir / "Duplicate Transactions.csv",
        ("Issue", "Trade ID", "Reason"),
        (
            {"Issue": "duplicate", "Trade ID": "tx-1", "Reason": ""},
            {"Issue": "duplicate", "Trade ID": "", "Reason": "hash"},
        ),
    )

    VerificationCompareService(FilesystemArtifactStore()).execute(
        VerificationCompareRequest(previous_dir=previous_dir, current_dir=current_dir, output_dir=output_dir)
    )

    rows = FilesystemArtifactStore().read_rows(output_dir / "current_duplicate_transaction_rows.csv")

    assert rows == [
        {"Issue": "duplicate", "Reason": "", "Trade ID": "tx-1"},
        {"Issue": "duplicate", "Reason": "hash", "Trade ID": ""},
    ]
