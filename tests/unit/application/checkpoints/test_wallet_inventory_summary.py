from __future__ import annotations

from crypto_reconciliation.application.checkpoints.wallet_inventory_summary import summarize_wallet_inventory


def test_wallet_inventory_summary_marks_alias_rows_for_linked_evidence() -> None:
    inventory_rows, issue_rows = summarize_wallet_inventory(
        [
            {
                "source": "gtrade",
                "capture_path": "raw/gtrade.csv",
                "wallet_id": "address_alias:bb4d",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xbb4d",
                "display_identifier": "0xbb4d",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "account_label": "Trading",
                "evidence_kind": "statement_alias",
                "evidence_path": "normalized/gtrade.csv",
                "confidence": "medium",
                "note": "truncated alias only",
            }
        ]
    )

    assert inventory_rows[0]["status"] == "needs_linked_evidence"
    assert issue_rows == []


def test_wallet_inventory_summary_flags_missing_evidence_path() -> None:
    _, issue_rows = summarize_wallet_inventory(
        [
            {
                "source": "fixture",
                "capture_path": "raw/fixture.csv",
                "wallet_id": "wallet-1",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "account_label": "Primary",
                "evidence_kind": "wallet_state",
                "evidence_path": "",
                "confidence": "high",
                "note": "",
            }
        ]
    )

    assert issue_rows[0]["issue_kind"] == "missing_evidence_path"


def test_wallet_inventory_summary_flags_identifier_kind_conflicts() -> None:
    _, issue_rows = summarize_wallet_inventory(
        [
            {
                "source": "fixture",
                "capture_path": "raw/a.csv",
                "wallet_id": "wallet-1",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "account_label": "Primary",
                "evidence_kind": "wallet_state",
                "evidence_path": "a.csv",
                "confidence": "high",
                "note": "",
            },
            {
                "source": "fixture",
                "capture_path": "raw/b.csv",
                "wallet_id": "wallet-2",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "account_label": "Primary",
                "evidence_kind": "statement_alias",
                "evidence_path": "b.csv",
                "confidence": "medium",
                "note": "",
            },
        ]
    )

    assert any(row["issue_kind"] == "identifier_kind_conflict" for row in issue_rows)
