from __future__ import annotations

from pathlib import Path

import wallet_inventory


def test_build_wallet_inventory_uses_isolated_fixture_repo(copy_fixture_tree) -> None:
    repo_root = copy_fixture_tree("repos/minimal_wallet_inventory_repo")

    inventory_rows, evidence_rows, issue_rows, summary = wallet_inventory.build_wallet_inventory(repo_root)

    assert summary["status"] == "needs_review"
    assert summary["wallet_count"] == 2
    assert {row["wallet_id"] for row in inventory_rows} == {
        "address_alias:bb4d",
        "evm_address:0x1111111111111111111111111111111111111111",
    }
    assert any(row["wallet_id"] == "address_alias:bb4d" and row["status"] == "needs_linked_evidence" for row in inventory_rows)
    assert any(row["wallet_id"] == "address_alias:bb4d" for row in evidence_rows)
    assert any(row["issue_kind"] == "partial_identifier_only" for row in issue_rows)
    assert any(row["issue_kind"] == "missing_capture_path" for row in issue_rows)


def test_profile_wallet_identifiers_reports_ledger_live_account_conflict(copy_fixture_tree) -> None:
    raw_dir = copy_fixture_tree("raw_sources/ledger_live_conflict/raw")

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers(
        "ledger-live-main",
        raw_dir,
        adapter_name="ledger_live",
    )

    assert summary["adapter"] == "ledger_live"
    assert summary["status"] == "needs_review"
    assert len(evidence) == 2
    assert any(issue["issue_kind"] == "account_identifier_conflict" for issue in issues)


def test_profile_wallet_identifiers_reports_missing_metamask_state(tmp_path: Path) -> None:
    raw_dir = tmp_path / "metamask" / "raw"
    raw_dir.mkdir(parents=True)

    evidence, issues, summary = wallet_inventory.profile_wallet_identifiers("MetaMask app", raw_dir)

    assert evidence == []
    assert summary["status"] == "needs_review"
    assert any(issue["issue_kind"] == "missing_identifier" for issue in issues)
