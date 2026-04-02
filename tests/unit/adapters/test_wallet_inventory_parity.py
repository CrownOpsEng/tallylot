from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.domain.models import SourceProfile
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.adapters import SourceAdapter

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "adapter_packs"


def _profile_and_adapter(source: str, raw_dir: Path) -> tuple[SourceProfile, SourceAdapter]:
    registry = build_registry()
    profile = ProfileService(registry, FilesystemArtifactStore()).create_profile(source, raw_dir)
    return profile, registry.source_adapter(str(profile.adapter_id))


def test_evm_wallet_missing_state_reports_missing_identifier() -> None:
    raw_dir = FIXTURE_ROOT / "evm_wallet" / "missing_state" / "raw"

    profile, adapter = _profile_and_adapter("EVM Wallet", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("EVM Wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert evidence == ()
    assert len(issues) == 1
    assert issues[0].kind == "missing_identifier"


def test_evm_wallet_extracts_accounts_and_identity_records() -> None:
    raw_dir = FIXTURE_ROOT / "evm_wallet" / "wallets" / "raw"

    profile, adapter = _profile_and_adapter("EVM Wallet", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("EVM Wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_wallet"
    assert issues == ()
    assert {row.wallet_id for row in evidence} >= {
        "evm_address:0x1111111111111111111111111111111111111111",
        "btc_address:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }


def test_evm_explorer_fixture_reports_multiple_primary_identifiers() -> None:
    raw_dir = FIXTURE_ROOT / "evm_explorer" / "multi_wallet_capture" / "raw"

    profile, adapter = _profile_and_adapter("bsc-wallet", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("bsc-wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_explorer"
    assert len({row.wallet_id for row in evidence}) == 2
    assert any(issue.kind == "multiple_primary_identifiers" for issue in issues)


def test_near_wallet_capture_extracts_near_account_identifiers() -> None:
    raw_dir = FIXTURE_ROOT / "near" / "wallet_capture" / "raw"

    profile, adapter = _profile_and_adapter("capture-near", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("capture-near", raw_dir, profile)

    assert str(profile.adapter_id) == "near"
    assert issues == ()
    assert any(row.identifier_kind == "near_account" for row in evidence)


def test_ledger_live_wallet_inventory_reports_account_conflict() -> None:
    raw_dir = FIXTURE_ROOT / "ledger_live" / "account_conflict_wallets" / "raw"

    profile, adapter = _profile_and_adapter("ledger-live-main", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("ledger-live-main", raw_dir, profile)

    assert str(profile.adapter_id) == "ledger_live"
    assert len(evidence) == 2
    assert any(issue.kind == "account_identifier_conflict" for issue in issues)


def test_gtrade_wallet_inventory_includes_alias_issue() -> None:
    raw_dir = FIXTURE_ROOT / "gtrade" / "realized_pnl_alias" / "raw"

    profile, adapter = _profile_and_adapter("gtrade-main", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("gtrade-main", raw_dir, profile)

    assert str(profile.adapter_id) == "gtrade"
    assert any(row.wallet_id.startswith("address_alias:") for row in evidence)
    assert any(issue.kind == "partial_identifier_only" for issue in issues)
