from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.near.adapter import NearAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, LegKind, ProjectionHint, TaxTreatmentHint
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_near_adapter_extracts_location_inventory_and_staking_split_events(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "example.near_transactions.csv"
    path.write_text(
        "Time,Method,Deposit Value,Txn Fee,Txn Hash\n"
        "2023-08-06 10:00:00,transfer,2.5,0.1,tx-transfer\n"
        "2023-08-07 11:00:00,deposit_and_stake,3.0,0.1,tx-stake\n",
        encoding="utf-8",
    )

    adapter = NearAdapter()
    profile = build_source_profile(adapter_id="near", source="wallet-a", raw_dir=str(raw_dir))

    location_inventory, location_issues = adapter.extract_location_inventory("wallet-a", raw_dir, profile)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert not location_issues
    assert location_inventory[0].identifier_kind == "near_account"
    assert location_inventory[0].identifier_value == "example.near"
    assert str(location_inventory[0].location_id) == "near:example.near"
    assert len(facts) == 3
    assert any(str(event.location_id) == "near:example.near:staking" for event in facts)


def test_near_adapter_uses_block_time_when_time_column_is_missing(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "example.near_transactions.csv"
    path.write_text(
        "Block Time,Method,Deposit Value,Txn Fee,Txn Hash\n2023-08-06 10:00:00,transfer,2.5,0.1,tx-transfer\n",
        encoding="utf-8",
    )

    result = NearAdapter().translate(
        build_source_profile(adapter_id="near", source="wallet-a", raw_dir=str(raw_dir)),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT
    assert facts[0].accounting_intent_hint == AccountingIntentHint.FUNDING_INFLOW
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN
    assert facts[0].timestamp == datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC)


def test_near_adapter_normalizes_transfer_and_stake_rows() -> None:
    raw_dir = fixture_raw_dir("near", "staking_and_wallet")

    profile, adapter = profile_and_adapter("capture-near", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "near"
    assert [event.economic_kind for event in facts] == [
        EconomicKind.CHAIN_TRANSFER_IN,
        EconomicKind.STAKING_TRANSFER_OUT,
        EconomicKind.STAKING_TRANSFER_IN,
    ]
    assert [event.projection_hint for event in facts] == [
        ProjectionHint.DEPOSIT,
        ProjectionHint.WITHDRAWAL,
        ProjectionHint.DEPOSIT,
    ]
    assert [event.accounting_intent_hint for event in facts] == [
        AccountingIntentHint.FUNDING_INFLOW,
        AccountingIntentHint.FUNDING_OUTFLOW,
        AccountingIntentHint.FUNDING_INFLOW,
    ]
    assert [event.tax_treatment_hint for event in facts] == [
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
    ]
    transfer_charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert facts[0].legs[0].leg_id == "primary_in"
    assert facts[0].legs[0].quantity == Decimal("1")
    assert str(facts[0].legs[0].instrument_id) == "symbol:NEAR@near"
    assert transfer_charge_legs[0].leg_id == "charge"
    assert transfer_charge_legs[0].quantity == Decimal("-0.01")
    assert any(str(event.location_id).endswith(":staking") for event in facts)
    assert result.issues == ()


def test_near_wallet_capture_extracts_near_account_identifiers() -> None:
    raw_dir = fixture_raw_dir("near", "wallet_capture")

    profile, adapter = profile_and_adapter("capture-near", raw_dir)
    evidence, issues = adapter.extract_location_inventory("capture-near", raw_dir, profile)

    assert str(profile.adapter_id) == "near"
    assert issues == ()
    assert any(row.identifier_kind == "near_account" for row in evidence)
    assert {str(row.location_id) for row in evidence} == {"near:example.near"}


def test_near_adapter_surfaces_unsupported_methods_without_crashing(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "example.near_transactions.csv"
    path.write_text(
        "Time,Method,Deposit Value,Txn Fee,Txn Hash\n2023-08-06 10:00:00,unstake,2.5,0.1,tx-unstake\n",
        encoding="utf-8",
    )

    result = NearAdapter().translate(
        build_source_profile(adapter_id="near", source="wallet-a", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
