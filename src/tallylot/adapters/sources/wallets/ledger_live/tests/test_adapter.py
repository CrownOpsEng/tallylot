from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, JournalIntent, LegKind, ProjectionType, TaxTreatmentCode
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_ledger_live_adapter_normalizes_grouped_trade_rows() -> None:
    raw_dir = fixture_raw_dir("ledger_live", "grouped_swap")

    profile, adapter = profile_and_adapter("ledger-live-main", raw_dir)
    result = adapter.translate(profile, raw_dir)
    facts = compile_activity_drafts(result.drafts)

    assert str(profile.adapter_id) == "ledger_live"
    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.ASSET_SWAP
    assert facts[0].projection_type == ProjectionType.TRADE
    assert facts[0].journal_intent == JournalIntent.ASSET_EXCHANGE
    assert facts[0].tax_treatment_code == TaxTreatmentCode.CAPITAL_EXCHANGE
    assert facts[0].legs[0].direction == "in"
    assert facts[0].legs[1].direction == "out"
    assert str(facts[0].legs[0].amount) == "0.01000000"
    assert str(facts[0].legs[1].asset) == "ETH"
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert str(charge_legs[0].amount) == "0.01000000"
    assert result.issues == ()


def test_ledger_live_wallet_inventory_extracts_fixture_accounts() -> None:
    raw_dir = fixture_raw_dir("ledger_live", "wallets_and_operations")

    profile, adapter = profile_and_adapter("ledger-live-main", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("ledger-live-main", raw_dir, profile)

    assert str(profile.adapter_id) == "ledger_live"
    assert {row.wallet_id for row in evidence} == {
        "btc_xpub:xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "evm_address:0x2222222222222222222222222222222222222222",
        "cardano_account_key:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
    assert issues == ()


def test_ledger_live_wallet_inventory_reports_account_conflict() -> None:
    raw_dir = fixture_raw_dir("ledger_live", "account_conflict_wallets")

    profile, adapter = profile_and_adapter("ledger-live-main", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("ledger-live-main", raw_dir, profile)

    assert str(profile.adapter_id) == "ledger_live"
    assert len(evidence) == 2
    assert any(issue.kind == "account_identifier_conflict" for issue in issues)


def test_ledger_live_adapter_surfaces_duplicate_group_rows_without_truncating(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "operations.csv").write_text(
        "Operation Hash,Transaction ID,Operation Type,Operation Date,Account Name,Currency Ticker,Operation Amount\n"
        "swap-1,,IN,2024-01-01T00:00:00.000Z,Main,BTC,0.01\n"
        "swap-1,,OUT,2024-01-01T00:00:00.000Z,Main,ETH,0.2\n"
        "swap-1,,FEES,2024-01-01T00:00:00.000Z,Main,ETH,0.001\n"
        "swap-1,,FEES,2024-01-01T00:00:00.000Z,Main,ETH,0.002\n",
        encoding="utf-8",
    )

    profile = build_source_profile(adapter_id="ledger_live", source="ledger-live-main", raw_dir=str(raw_dir))
    adapter = profile_and_adapter("ledger-live-main", raw_dir)[1]
    result = adapter.translate(profile, raw_dir)

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_group"
