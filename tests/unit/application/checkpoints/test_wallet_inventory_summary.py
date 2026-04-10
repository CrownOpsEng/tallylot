from __future__ import annotations

from tallylot.application.checkpoints.location_inventory_summary import (
    summarize_location_inventory,
)


def test_location_inventory_summary_marks_alias_rows_for_linked_evidence() -> None:
    inventory_rows, issue_rows = summarize_location_inventory(
        [
            {
                "source": "gtrade",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "location_id": "gtrade:alias:bb4d",
                "location_kind": "other",
                "location_label": "bb4d",
                "parent_location_id": "",
                "location_path": "",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xbb4d",
                "display_identifier": "0xbb4d",
                "network_scope": "arbitrum",
                "controller": "EVM Wallet",
                "parent_location_label": "",
                "evidence_kind": "statement_alias",
                "evidence_path": "normalized/gtrade.csv",
                "confidence": "medium",
                "note": "truncated alias only",
            }
        ]
    )

    assert inventory_rows[0]["status"] == "needs_linked_evidence"
    assert issue_rows == []


def test_location_inventory_summary_flags_missing_evidence_path() -> None:
    _, issue_rows = summarize_location_inventory(
        [
            {
                "source": "fixture",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "location_id": "fixture:wallet-1",
                "location_kind": "address",
                "location_label": "Primary",
                "parent_location_id": "",
                "location_path": "",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "parent_location_label": "",
                "evidence_kind": "wallet_state",
                "evidence_path": "",
                "confidence": "high",
                "note": "",
            }
        ]
    )

    assert issue_rows[0]["issue_kind"] == "missing_evidence_path"


def test_location_inventory_summary_flags_identifier_kind_conflicts() -> None:
    _, issue_rows = summarize_location_inventory(
        [
            {
                "source": "fixture",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "location_id": "fixture:wallet-1",
                "location_kind": "address",
                "location_label": "Primary",
                "parent_location_id": "",
                "location_path": "",
                "identifier_kind": "address",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "parent_location_label": "",
                "evidence_kind": "wallet_state",
                "evidence_path": "a.csv",
                "confidence": "high",
                "note": "",
            },
            {
                "source": "fixture",
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                "location_id": "fixture:wallet-2",
                "location_kind": "other",
                "location_label": "Primary Alias",
                "parent_location_id": "",
                "location_path": "",
                "identifier_kind": "address_alias",
                "normalized_identifier": "0xabc",
                "display_identifier": "0xabc",
                "network_scope": "ethereum",
                "controller": "Fixture",
                "parent_location_label": "",
                "evidence_kind": "statement_alias",
                "evidence_path": "b.csv",
                "confidence": "medium",
                "note": "",
            },
        ]
    )

    assert any(row["issue_kind"] == "identifier_kind_conflict" for row in issue_rows)
