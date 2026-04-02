from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.gtrade.adapter import GTradeAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
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
    assert [event.projection_type for event in facts] == [
        ProjectionType.DERIVATIVES_FUTURES_PROFIT,
        ProjectionType.DERIVATIVES_FUTURES_LOSS,
    ]
    assert [event.journal_intent for event in facts] == [
        JournalIntent.INCOME_RECOGNITION,
        JournalIntent.EXPENSE_RECOGNITION,
    ]
    assert [event.tax_treatment_code for event in facts] == [
        TaxTreatmentCode.DERIVATIVE_REALIZED_GAIN,
        TaxTreatmentCode.DERIVATIVE_REALIZED_LOSS,
    ]
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"


def test_gtrade_wallet_inventory_includes_alias_issue() -> None:
    raw_dir = fixture_raw_dir("gtrade", "realized_pnl_alias")

    profile, adapter = profile_and_adapter("GTrade 1CT", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("GTrade 1CT", raw_dir, profile)

    assert str(profile.adapter_id) == "gtrade"
    assert any(row.wallet_id == "address_alias:bb4d" for row in evidence)
    assert any(issue.kind == "partial_identifier_only" for issue in issues)


def test_gtrade_adapter_surfaces_invalid_rows_without_crashing(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "report.csv").write_text(
        "DATE,PAIR,ADDR,DESCRIPTION,PNL\nbad-date,BTCUSD,bb4d,broken row,not-a-number\n",
        encoding="utf-8",
    )

    result = GTradeAdapter().translate(
        build_source_profile(adapter_id="gtrade", raw_dir=str(raw_dir), source="GTrade"),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
