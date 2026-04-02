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


def test_coinbase_adapter_uses_retail_family_without_source_label() -> None:
    raw_dir = FIXTURE_ROOT / "coinbase" / "retail_buy_renamed" / "raw"

    profile, adapter = _profile_and_adapter("Future Exchange", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "coinbase"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].raw_file == "retail-export.csv"
    assert result.canonical_events[0].event_kind == "Trade"
    assert result.issues == ()


def test_wealthsimple_fixture_exercises_supported_and_unsupported_rows() -> None:
    raw_dir = FIXTURE_ROOT / "wealthsimple" / "mixed_activity_review" / "raw"

    profile, adapter = _profile_and_adapter("Future Broker", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "wealthsimple"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Trade"
    assert str(result.canonical_events[0].timestamp) == "2023-09-22 00:00:00"
    assert result.canonical_events[0].render_match_window_seconds == "86399"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"
    assert "Staking/REWARD" in result.issues[0].message


def test_crypto_com_adapter_uses_transaction_kinds_without_source_label() -> None:
    raw_dir = FIXTURE_ROOT / "crypto_com" / "transaction_kinds" / "raw"

    profile, adapter = _profile_and_adapter("Future Card", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "crypto_com"
    assert [event.event_kind for event in result.canonical_events] == ["Deposit", "Trade", "Withdrawal"]
    assert {event.raw_file for event in result.canonical_events} == {"records-a.csv", "records-b.csv"}
    assert result.issues == ()


def test_evm_explorer_chain_scoped_capture_accepts_neutral_filenames() -> None:
    raw_dir = FIXTURE_ROOT / "evm_explorer" / "chain_scoped_deposit" / "raw"

    profile, adapter = _profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.normalize(profile, raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("bsc-wallet", raw_dir, profile)

    assert str(profile.adapter_id) == "evm_explorer"
    assert issues == ()
    assert [row.wallet_id for row in evidence] == ["evm_address:0x1111111111111111111111111111111111111111"]
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Deposit"
    assert str(result.canonical_events[0].asset_in) == "BNB"
    assert str(result.canonical_events[0].amount_in) == "1.50000000"


def test_evm_explorer_chain_scoped_capture_works_from_nested_bundle_paths(tmp_path: Path) -> None:
    nested = tmp_path / "raw" / "2024-03" / "bundle-01"
    nested.mkdir(parents=True)
    source_path = FIXTURE_ROOT / "evm_explorer" / "chain_scoped_deposit" / "raw" / "transactions.csv"
    (nested / "transactions.csv").write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    profile, adapter = _profile_and_adapter("bsc-wallet", tmp_path / "raw")
    result = adapter.normalize(profile, tmp_path / "raw")

    assert str(profile.adapter_id) == "evm_explorer"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Deposit"


def test_evm_explorer_suspicious_nft_fixture_surfaces_review_without_auto_import() -> None:
    raw_dir = FIXTURE_ROOT / "evm_explorer" / "suspicious_nft_review" / "raw"

    profile, adapter = _profile_and_adapter("bsc-wallet", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert result.canonical_events == ()
    assert len(result.issues) == 1
    assert result.issues[0].kind == "review_required"
    assert "suspicious NFT airdrop" in result.issues[0].message
