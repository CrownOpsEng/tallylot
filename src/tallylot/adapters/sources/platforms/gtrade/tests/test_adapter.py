from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.platforms.gtrade.adapter import _GTradeAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_gtrade_adapter_surfaces_report_limits_without_guessing() -> None:
    raw_dir = fixture_raw_dir("gtrade", "realized_pnl_alias")

    profile, adapter = profile_and_adapter("GTrade 1CT", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "gtrade"
    assert [event.economic_kind for event in facts] == [
        EconomicKind.DERIVATIVE_REALIZED_PROFIT,
        EconomicKind.DERIVATIVE_REALIZED_LOSS,
    ]
    assert [event.projection_hint for event in facts] == [
        ProjectionHint.DERIVATIVES_FUTURES_PROFIT,
        ProjectionHint.DERIVATIVES_FUTURES_LOSS,
    ]
    assert [event.accounting_intent_hint for event in facts] == [
        AccountingIntentHint.INCOME_RECOGNITION,
        AccountingIntentHint.EXPENSE_RECOGNITION,
    ]
    assert [event.tax_treatment_hint for event in facts] == [
        TaxTreatmentHint.DERIVATIVE_REALIZED_GAIN,
        TaxTreatmentHint.DERIVATIVE_REALIZED_LOSS,
    ]
    assert facts[0].legs[0].quantity == Decimal("10")
    assert facts[1].legs[0].quantity == Decimal("-5")
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"


def test_gtrade_location_inventory_includes_alias_issue() -> None:
    raw_dir = fixture_raw_dir("gtrade", "realized_pnl_alias")

    profile, adapter = profile_and_adapter("GTrade 1CT", raw_dir)
    evidence, issues = adapter.extract_location_inventory("GTrade 1CT", raw_dir, profile)

    assert str(profile.adapter_id) == "gtrade"
    assert any(str(row.location_id) == "gtrade_1ct:alias:bb4d" for row in evidence)
    assert any(issue.kind == "partial_identifier_only" for issue in issues)


def test_gtrade_adapter_surfaces_invalid_rows_without_crashing(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "report.csv").write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\nbad-date,BTCUSD,bb4d,broken row,not-a-number\n",
        encoding="utf-8",
    )

    result = _GTradeAdapter().translate(
        build_source_profile(adapter_id="gtrade", raw_dir=str(raw_dir), source="GTrade"),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
