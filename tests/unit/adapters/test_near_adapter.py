from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.near.adapter import NearAdapter
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
