from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.near.adapter import NearAdapter
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter
from tests.support.services import build_source_profile


def test_near_adapter_extracts_wallet_inventory_and_staking_split_events(tmp_path: Path) -> None:
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
    profile = build_source_profile(adapter_id="near", source="near-main", raw_dir=str(raw_dir))

    wallet_inventory, wallet_issues = adapter.extract_wallet_inventory("near-main", raw_dir, profile)
    result = adapter.normalize(profile, raw_dir)

    assert not wallet_issues
    assert wallet_inventory[0].identifier_kind == "near_account"
    assert wallet_inventory[0].identifier_value == "example.near"
    assert len(result.canonical_events) == 3
    assert any(str(event.source) == "near-main - Staking" for event in result.canonical_events)


def test_near_adapter_uses_block_time_when_time_column_is_missing(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "example.near_transactions.csv"
    path.write_text(
        "Block Time,Method,Deposit Value,Txn Fee,Txn Hash\n2023-08-06 10:00:00,transfer,2.5,0.1,tx-transfer\n",
        encoding="utf-8",
    )

    result = NearAdapter().normalize(
        build_source_profile(adapter_id="near", source="near-main", raw_dir=str(raw_dir)),
        raw_dir,
    )

    assert len(result.canonical_events) == 1
    assert result.canonical_events[0].event_kind == "Deposit"
    assert str(result.canonical_events[0].timestamp) == "2023-08-06 10:00:00"


def test_near_adapter_normalizes_transfer_and_stake_rows() -> None:
    raw_dir = fixture_raw_dir("near", "staking_and_wallet")

    profile, adapter = profile_and_adapter("capture-near", raw_dir)
    result = adapter.normalize(profile, raw_dir)

    assert str(profile.adapter_id) == "near"
    assert [event.event_kind for event in result.canonical_events] == ["Deposit", "Withdrawal", "Deposit"]
    assert any(str(event.source).endswith("Staking") for event in result.canonical_events)
    assert result.issues == ()


def test_near_wallet_capture_extracts_near_account_identifiers() -> None:
    raw_dir = fixture_raw_dir("near", "wallet_capture")

    profile, adapter = profile_and_adapter("capture-near", raw_dir)
    evidence, issues = adapter.extract_wallet_inventory("capture-near", raw_dir, profile)

    assert str(profile.adapter_id) == "near"
    assert issues == ()
    assert any(row.identifier_kind == "near_account" for row in evidence)
