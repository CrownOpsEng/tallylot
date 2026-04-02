from __future__ import annotations

from tallylot.domain.transactions import EconomicKind, ProjectionType
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_ledger_live_adapter_normalizes_grouped_trade_rows() -> None:
    raw_dir = fixture_raw_dir("ledger_live", "grouped_swap")

    profile, adapter = profile_and_adapter("ledger-live-main", raw_dir)
    result = adapter.translate(profile, raw_dir)

    assert str(profile.adapter_id) == "ledger_live"
    assert len(result.facts) == 1
    assert result.facts[0].economic_kind == EconomicKind.ASSET_SWAP
    assert result.facts[0].projection_type == ProjectionType.TRADE
    assert str(result.facts[0].amount_in) == "0.01000000"
    assert str(result.facts[0].asset_out) == "ETH"
    assert str(result.facts[0].fee_amount) == "0.01000000"
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
