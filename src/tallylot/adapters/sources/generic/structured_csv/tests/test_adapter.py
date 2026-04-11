from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.generic.structured_csv.adapter import (
    _StructuredCsvSourceAdapter,
)
from tallylot.adapters.sources.generic.structured_csv.contracts import REQUIRED_HEADER
from tallylot.adapters.sources.generic.structured_csv.feedback import (
    StructuredCsvFeedbackFactory,
)
from tallylot.adapters.sources.generic.structured_csv.normalization import (
    translate_structured_csv,
)
from tallylot.adapters.sources.generic.structured_csv.validation import (
    StructuredCsvRowValidator,
)
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import LegKind
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.services import build_source_profile


def test_structured_csv_adapter_matches_transactions_header(tmp_path: Path) -> None:
    score = _StructuredCsvSourceAdapter().match(
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
            "charge_asset": "",
            "charge_amount": "",
            "charge_side": "",
            "rebate_asset": "",
            "rebate_amount": "",
            "rebate_side": "",
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


def test_translate_structured_csv_rejects_invalid_schema(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "timestamp,category,asset_in\n2023-08-06 10:00:00,trade,BTC\n",
        encoding="utf-8",
    )

    result = translate_structured_csv(
        build_source_profile(
            adapter_id="structured_csv",
            raw_dir=str(raw_dir),
            source="Structured Example",
        ),
        raw_dir,
        adapter_id="structured_csv",
    )

    assert not compile_activity_drafts(result.drafts)
    assert not result.balance_references
    assert len(result.issues) == 1
    assert result.issues[0].kind == "invalid_schema"


def test_translate_structured_csv_preserves_title_row_line_numbers(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "Transactions\n"
        "User,Example,acct\n"
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,charge_asset,"
        "charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,tx_hash,"
        "description,account,wallet\n"
        "2023-08-06 10:00:00,trade,BTC,1.0,CAD,-100.0,CAD,-1.0,out,BTC,0.01,in,"
        "tx-1,fixture,Primary,Primary\n",
        encoding="utf-8",
    )

    result = translate_structured_csv(
        build_source_profile(
            adapter_id="structured_csv",
            raw_dir=str(raw_dir),
            source="Structured Example",
        ),
        raw_dir,
        adapter_id="structured_csv",
    )

    assert len(result.drafts) == 1
    assert result.drafts[0].raw_row_ref == "4"
def test_structured_csv_validator_rejects_side_attribution_without_matching_primary_leg() -> (
    None
):
    feedback = StructuredCsvFeedbackFactory(
        profile=build_source_profile(adapter_id="structured_csv"),
        adapter_id="structured_csv",
    )
    validator = StructuredCsvRowValidator(feedback=feedback)

    issue = validator.validate_row(
        {
            "timestamp": "2023-08-06 10:00:00",
            "category": "deposit",
            "asset_in": "BTC",
            "amount_in": "1.0",
            "asset_out": "",
            "amount_out": "",
            "charge_asset": "BTC",
            "charge_amount": "0.1",
            "charge_side": "out",
            "rebate_asset": "",
            "rebate_amount": "",
            "rebate_side": "",
            "tx_hash": "tx-1",
            "description": "fixture",
            "account": "Primary",
            "wallet": "Primary",
        },
        2,
    )

    assert issue is not None
    assert issue.kind == "invalid_side_attribution"


def test_translate_structured_csv_maps_charge_and_rebate_legs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
        "2023-08-06 10:00:00,trade,BTC,1.0,CAD,-100.0,CAD,-1.0,out,BTC,0.01,in,tx-1,fixture,Primary,Primary\n",
        encoding="utf-8",
    )

    result = translate_structured_csv(
        build_source_profile(
            adapter_id="structured_csv",
            raw_dir=str(raw_dir),
            source="Structured Example",
        ),
        raw_dir,
        adapter_id="structured_csv",
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    rebate_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.REBATE)
    assert charge_legs[0].quantity == Decimal("-1.0")
    assert charge_legs[0].attributed_to_leg_id == "primary_out"
    assert rebate_legs[0].quantity == Decimal("0.01")
    assert rebate_legs[0].attributed_to_leg_id == "primary_in"
