from __future__ import annotations

import json
from pathlib import Path

import wallet_inventory
from tests.support.helpers import write_csv


def test_profile_wallet_identifiers_extracts_ledger_live_accounts(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/ledger_live_wallets/raw")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers(
        "ledger-live-main",
        raw_dir,
        adapter_name="ledger_live",
    )

    wallet_ids = {row["wallet_id"] for row in evidence}
    assert "btc_xpub:xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111" in wallet_ids
    assert "evm_address:0x2222222222222222222222222222222222222222" in wallet_ids
    assert "cardano_account_key:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in wallet_ids
    assert issues == []
    assert summary["status"] == "passed"
    assert summary["adapter"] == "ledger_live"


def test_profile_wallet_identifiers_extracts_metamask_app_accounts_and_snap_addresses(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/metamask_wallets/raw")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("MetaMask app", raw_dir)

    wallet_ids = {row["wallet_id"] for row in evidence}
    assert "evm_address:0x1111111111111111111111111111111111111111" in wallet_ids
    assert "evm_address:0x2222222222222222222222222222222222222222" in wallet_ids
    assert "btc_address:bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in wallet_ids
    assert "tron_address:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" in wallet_ids
    assert "solana_address:F11111111111111111111111111111111111111111" in wallet_ids
    assert issues == []
    assert summary["status"] == "passed"


def test_build_wallet_inventory_includes_gtrade_alias_issue(copy_fixture_tree) -> None:
    repo_root = copy_fixture_tree("repos/minimal_wallet_inventory_repo")

    inventory_rows, evidence_rows, issue_rows, summary = wallet_inventory.build_wallet_inventory(repo_root)

    assert any(row["wallet_id"] == "address_alias:bb4d" for row in evidence_rows)
    assert any(row["issue_kind"] == "partial_identifier_only" for row in issue_rows)
    assert summary["wallet_count"] == len(inventory_rows)


def test_refresh_wallet_inventory_writes_artifacts(copy_fixture_tree, tmp_path: Path) -> None:
    repo_root = copy_fixture_tree("repos/minimal_wallet_inventory_repo")
    out_dir = tmp_path / "inventory"

    summary = wallet_inventory.refresh_wallet_inventory(repo_root, out_dir=out_dir)

    with (out_dir / "wallet_inventory.csv").open(encoding="utf-8") as handle:
        inventory_rows = list(handle)
    with (out_dir / "wallet_inventory_evidence.csv").open(encoding="utf-8") as handle:
        evidence_rows = list(handle)
    issues = json.loads((out_dir / "wallet_inventory_summary.json").read_text(encoding="utf-8"))

    assert summary["inventory_path"] == str(out_dir / "wallet_inventory.csv")
    assert any("wallet_id" in line for line in inventory_rows[:1])
    assert any("source,capture_path" in line for line in evidence_rows[:1])
    assert summary["wallet_count"] == issues["wallet_count"]


def test_profile_wallet_identifiers_flags_empty_chain_scoped_capture(tmp_path: Path) -> None:
    raw_dir = tmp_path
    write_csv(raw_dir / "export-empty.csv", ["Transaction Hash", "DateTime (UTC)"], [])

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("eth-metamask1", raw_dir)

    assert evidence == []
    assert summary["status"] == "needs_review"
    assert any(row["issue_kind"] == "missing_identifier" for row in issues)


def test_profile_wallet_identifiers_resolves_adapter_from_profile_without_hint(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/near_wallet/raw")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("capture-near", raw_dir)

    assert any(row["identifier_kind"] == "near_account" for row in evidence)
    assert issues == []
    assert summary["adapter"] == "near"
