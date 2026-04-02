from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.platforms.wealthsimple.adapter import WealthsimpleAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, LegKind, ProjectionHint, TaxTreatmentHint
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_wealthsimple_fixture_exercises_supported_and_unsupported_rows() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "mixed_activity_review")

    profile, adapter = profile_and_adapter("WealthSimple", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.SPOT_TRADE
    assert facts[0].projection_hint == ProjectionHint.TRADE
    assert facts[0].accounting_intent_hint == AccountingIntentHint.ASSET_EXCHANGE
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.CAPITAL_EXCHANGE
    assert facts[0].timestamp == datetime(2023, 9, 21, 0, 0, 0, tzinfo=UTC)
    assert facts[0].effective_at == datetime(2023, 9, 22, 0, 0, 0, tzinfo=UTC)
    assert facts[0].effective_precision == TemporalPrecision.DATE
    primary_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.PRIMARY)
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert primary_legs[0].leg_id == "primary_in"
    assert primary_legs[0].quantity == Decimal("0.5")
    assert str(primary_legs[0].instrument_id) == "symbol:BTC@wealthsimple"
    assert primary_legs[1].leg_id == "primary_out"
    assert primary_legs[1].quantity == Decimal("-9998.75")
    assert str(primary_legs[1].instrument_id) == "symbol:CAD@wealthsimple"
    assert charge_legs[0].leg_id == "charge"
    assert charge_legs[0].quantity == Decimal("-1.25")
    assert str(charge_legs[0].instrument_id) == "symbol:CAD@wealthsimple"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "Staking/REWARD" in result.issues[0].message


def test_wealthsimple_adapter_uses_broker_activity_family_without_filename_dependency() -> None:
    raw_dir = fixture_raw_dir("wealthsimple", "broker_trade")

    profile, adapter = profile_and_adapter("Future Broker", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(facts) == 1
    assert facts[0].raw_file == "broker-export.csv"
    assert facts[0].projection_hint == ProjectionHint.TRADE
    primary_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.PRIMARY)
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert primary_legs[0].leg_id == "primary_in"
    assert primary_legs[0].quantity == Decimal("0.5")
    assert str(primary_legs[0].instrument_id) == "symbol:BTC@wealthsimple"
    assert primary_legs[1].leg_id == "primary_out"
    assert primary_legs[1].quantity == Decimal("-17500")
    assert str(primary_legs[1].instrument_id) == "symbol:CAD@wealthsimple"
    assert charge_legs[0].leg_id == "charge"
    assert charge_legs[0].quantity == Decimal("-12")
    assert str(charge_legs[0].instrument_id) == "symbol:CAD@wealthsimple"
    assert not result.issues


def test_wealthsimple_adapter_ignores_unrecognized_csv_files(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "broker-export.csv").write_text(
        ",".join(
            (
                "transaction_date",
                "settlement_date",
                "account_id",
                "account_type",
                "activity_type",
                "activity_sub_type",
                "direction",
                "symbol",
                "name",
                "currency",
                "quantity",
                "unit_price",
                "commission",
                "net_cash_amount",
            )
        )
        + "\n2023-09-20,2023-09-22,acct-1,Crypto,trade,BUY,,BTC,Bitcoin,CAD,0.1,30000,10,-3000\n",
        encoding="utf-8",
    )
    (raw_dir / "other.csv").write_text("a,b,c\nbad,row,data\n", encoding="utf-8")

    result = WealthsimpleAdapter().translate(
        build_source_profile(adapter_id="wealthsimple", raw_dir=str(raw_dir), source="Wealthsimple"),
        raw_dir,
    )

    facts = compile_activity_drafts(result.drafts)
    assert len(facts) == 1
    assert facts[0].projection_hint == ProjectionHint.TRADE
    assert not result.issues
