from __future__ import annotations

from tallylot.application.checkpoints.location_inventory_summary import (
    summarize_location_inventory,
)


def _evidence_row(
    *,
    source: str,
    capture_uid: str,
    location_id: str,
    location_kind: str,
    location_label: str,
    identifier_kind: str,
    normalized_identifier: str,
    display_identifier: str,
    evidence_kind: str,
    evidence_relative_path: str,
    confidence: str,
    network_scope: str = "ethereum",
    controller: str = "Fixture",
    note: str = "",
) -> dict[str, str]:
    return {
        "source": source,
        "capture_uid": capture_uid,
        "location_id": location_id,
        "location_kind": location_kind,
        "location_label": location_label,
        "parent_location_id": "",
        "location_path": "",
        "identifier_kind": identifier_kind,
        "normalized_identifier": normalized_identifier,
        "display_identifier": display_identifier,
        "network_scope": network_scope,
        "controller": controller,
        "parent_location_label": "",
        "evidence_kind": evidence_kind,
        "evidence_capture_uid": capture_uid,
        "evidence_relative_path": evidence_relative_path,
        "evidence_archive_member_path": "",
        "evidence_locator_kind": "raw_file",
        "evidence_anchor": "",
        "confidence": confidence,
        "note": note,
    }


def test_location_inventory_summary_marks_alias_rows_for_linked_evidence() -> None:
    inventory_rows, issue_rows = summarize_location_inventory(
        [
            _evidence_row(
                source="gtrade",
                capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
                location_id="gtrade:alias:bb4d",
                location_kind="other",
                location_label="bb4d",
                identifier_kind="address_alias",
                normalized_identifier="0xbb4d",
                display_identifier="0xbb4d",
                evidence_kind="statement_alias",
                evidence_relative_path="normalized/gtrade.csv",
                confidence="medium",
                network_scope="arbitrum",
                controller="EVM Wallet",
                note="truncated alias only",
            )
        ]
    )

    assert inventory_rows[0]["status"] == "needs_linked_evidence"
    assert issue_rows == []


def test_location_inventory_summary_flags_missing_evidence_path() -> None:
    _, issue_rows = summarize_location_inventory(
        [
            {
                **_evidence_row(
                    source="fixture",
                    capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
                    location_id="fixture:wallet-1",
                    location_kind="address",
                    location_label="Primary",
                    identifier_kind="address",
                    normalized_identifier="0xabc",
                    display_identifier="0xabc",
                    evidence_kind="wallet_state",
                    evidence_relative_path="ignored.csv",
                    confidence="high",
                ),
                "evidence_capture_uid": "",
                "evidence_relative_path": "",
                "evidence_locator_kind": "",
            }
        ]
    )

    assert issue_rows[0]["issue_kind"] == "missing_evidence_path"


def test_location_inventory_summary_flags_identifier_kind_conflicts() -> None:
    _, issue_rows = summarize_location_inventory(
        [
            _evidence_row(
                source="fixture",
                capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
                location_id="fixture:wallet-1",
                location_kind="address",
                location_label="Primary",
                identifier_kind="address",
                normalized_identifier="0xabc",
                display_identifier="0xabc",
                evidence_kind="wallet_state",
                evidence_relative_path="a.csv",
                confidence="high",
            ),
            _evidence_row(
                source="fixture",
                capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9F",
                location_id="fixture:wallet-2",
                location_kind="other",
                location_label="Primary Alias",
                identifier_kind="address_alias",
                normalized_identifier="0xabc",
                display_identifier="0xabc",
                evidence_kind="statement_alias",
                evidence_relative_path="b.csv",
                confidence="medium",
            ),
        ]
    )

    assert any(row["issue_kind"] == "identifier_kind_conflict" for row in issue_rows)
