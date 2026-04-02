from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.generic.structured_csv import StructuredCsvSourceAdapter
from crypto_reconciliation.adapters.sources.generic.structured_csv.contracts import REQUIRED_HEADER
from crypto_reconciliation.adapters.sources.generic.structured_csv.feedback import StructuredCsvFeedbackFactory
from crypto_reconciliation.adapters.sources.generic.structured_csv.normalization import normalize_structured_csv
from crypto_reconciliation.adapters.sources.generic.structured_csv.validation import StructuredCsvRowValidator
from crypto_reconciliation.domain.models import FileInventoryEntry
from tests.support.services import build_source_profile


def test_structured_csv_adapter_matches_transactions_header(tmp_path: Path) -> None:
    score = StructuredCsvSourceAdapter().match(
        "fixture",
        tmp_path,
        (
            FileInventoryEntry(
                relative_path="transactions.csv",
                suffix=".csv",
                size_bytes=1,
                sha256="fixture",
                header=REQUIRED_HEADER,
            ),
        ),
    )

    assert score == 100


def test_structured_csv_validator_reports_missing_required_fields() -> None:
    feedback = StructuredCsvFeedbackFactory(
        profile=build_source_profile(adapter_id="structured_csv"),
        adapter_id="structured_csv",
    )
    validator = StructuredCsvRowValidator(feedback=feedback)

    issue = validator.validate_row(
        {
            "timestamp": "",
            "category": "trade",
            "asset_in": "BTC",
            "amount_in": "1.0",
            "asset_out": "CAD",
            "amount_out": "10.0",
            "fee_asset": "",
            "fee_amount": "",
            "tx_hash": "tx-1",
            "description": "fixture",
            "account": "",
            "wallet": "Primary",
        },
        2,
    )

    assert issue is not None
    assert issue.kind == "missing_required_field"
    assert issue.raw_row_ref == "2"


def test_structured_csv_validator_canonicalizes_negative_outbound_amounts() -> None:
    feedback = StructuredCsvFeedbackFactory(
        profile=build_source_profile(adapter_id="structured_csv"),
        adapter_id="structured_csv",
    )
    validator = StructuredCsvRowValidator(feedback=feedback)

    amount, review = validator.normalize_outbound_amount(2, "amount_out", "-10.0")

    assert amount == Decimal("10")
    assert review is not None
    assert review.kind == "outbound_amount_sign_normalized"
    assert review.field_name == "amount_out"
    assert review.normalized_value == "10"


def test_normalize_structured_csv_rejects_invalid_schema(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "timestamp,category,asset_in\n2023-08-06 10:00:00,trade,BTC\n",
        encoding="utf-8",
    )

    result = normalize_structured_csv(
        build_source_profile(adapter_id="structured_csv", raw_dir=str(raw_dir), source="Structured Example"),
        raw_dir,
        adapter_id="structured_csv",
    )

    assert not result.transactions
    assert not result.balances
    assert len(result.issues) == 1
    assert result.issues[0].kind == "invalid_schema"
