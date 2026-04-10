from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.normalization import (
    AssembleSourceRequest,
    AssembleSourceUseCase,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER, SOURCE_INVENTORY_HEADER
from tallylot.ports.evidence import (
    BALANCE_EVIDENCE_HEADER,
    BALANCE_SNAPSHOT_HEADER,
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
    NORMALIZATION_REVIEW_HEADER,
)
from tallylot.ports.facts import FACT_HEADER


def test_source_assembly_merges_normalized_captures_and_excludes_overlap(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row("01HV4A5H7VJH7M3Y5A6B7C8D9E", status="normalized"),
            _capture_row(
                "01HV4A5H7VJH7M3Y5A6B7C8D9F", status="overlap_review_required"
            ),
        ),
    )
    included_root = (
        workspace_root
        / "working"
        / "normalized"
        / "captures"
        / "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    )
    excluded_root = (
        workspace_root
        / "working"
        / "normalized"
        / "captures"
        / "01HV4A5H7VJH7M3Y5A6B7C8D9F"
    )
    _write_capture_outputs(artifacts, included_root, quantity="1.0")
    _write_capture_outputs(artifacts, excluded_root, quantity="2.0")

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    summary = json.loads(
        (assembled_root / "assembly_summary.json").read_text(encoding="utf-8")
    )
    balance_rows = artifacts.read_rows(assembled_root / "balances.csv")
    evidence_rows = artifacts.read_rows(assembled_root / "balance_evidence.csv")
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 1
    assert response.excluded_capture_count == 1
    assert summary["included_capture_uids"] == ["01HV4A5H7VJH7M3Y5A6B7C8D9E"]
    assert summary["excluded_capture_uids"] == ["01HV4A5H7VJH7M3Y5A6B7C8D9F"]
    assert balance_rows[0]["quantity"] == "1.0"
    assert evidence_rows[0]["capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert evidence_rows[0]["relative_path"] == "statement-a.pdf"
    assert evidence_rows[0]["anchor"] == "page=1"
    assert source_rows[0]["assembly_status"] == "assembled"
    assert source_rows[0]["assembled_root_ref"] == "working/normalized/sources/coinbase"


def test_source_assembly_surfaces_semantic_balance_conflicts(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row("01HV4A5H7VJH7M3Y5A6B7C8D9E", status="normalized"),
            _capture_row("01HV4A5H7VJH7M3Y5A6B7C8D9F", status="normalized"),
        ),
    )
    capture_root_a = (
        workspace_root
        / "working"
        / "normalized"
        / "captures"
        / "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    )
    capture_root_b = (
        workspace_root
        / "working"
        / "normalized"
        / "captures"
        / "01HV4A5H7VJH7M3Y5A6B7C8D9F"
    )
    _write_capture_outputs(artifacts, capture_root_a, quantity="1.0")
    _write_capture_outputs(artifacts, capture_root_b, quantity="2.0")

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    issue_rows = artifacts.read_rows(assembled_root / "assembly_issues.csv")

    assert response.balance_count == 2
    assert issue_rows[0]["kind"] == "assembly_semantic_conflict"
    assert issue_rows[0]["raw_file"] == "balances.csv"


def _write_source_inventory(
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
) -> None:
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": "coinbase",
                "activity_after_cutoff": "unknown",
                "scope_status": "in_scope",
                "status": "normalized",
                "capture_count": "2",
                "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                "latest_capture_label": "2026-03-23T14-15-17Z",
                "latest_capture_completed_at": "2026-03-23 14:15:17",
                "assembly_status": "pending",
                "assembled_root_ref": "",
                "adapter_hints": "coinbase",
                "notes": "",
            },
        ),
    )


def _write_capture_registry(
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
    rows: tuple[dict[str, str], ...],
) -> None:
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        rows,
    )


def _capture_row(capture_uid: str, *, status: str) -> dict[str, str]:
    return {
        "capture_uid": capture_uid,
        "source": "coinbase",
        "capture_label": "2026-03-23T14-15-16Z",
        "status": status,
        "intake_started_at": "2026-03-23 14:15:16",
        "intake_completed_at": "2026-03-23 14:15:16",
        "intake_method": "source_intake_apply",
        "incoming_ref": "incoming/coinbase",
        "capture_root_ref": "evidence/raw/source/coinbase/2026-03-23T14-15-16Z",
        "manifest_fingerprint": f"manifest:{capture_uid}",
        "file_count": "1",
        "observed_period_start": "2026-03-23",
        "observed_period_end": "2026-03-23",
        "observed_group_count": "1",
        "supersedes_capture_uid": "",
        "notes": "",
    }


def _write_capture_outputs(
    artifacts: FilesystemArtifactStore,
    root: Path,
    *,
    quantity: str,
) -> None:
    artifacts.write_rows(root / "facts.csv", FACT_HEADER, ())
    artifacts.write_json(root / "fact_annotations.json", [])
    artifacts.write_rows(
        root / "balances.csv",
        BALANCE_SNAPSHOT_HEADER,
        (_balance_row(quantity=quantity),),
    )
    artifacts.write_rows(
        root / "balance_evidence.csv",
        BALANCE_EVIDENCE_HEADER,
        (
            {
                **_balance_row(quantity=quantity),
                "capture_uid": root.name,
                "relative_path": "statement-a.pdf",
                "archive_member_path": "",
                "locator_kind": "raw_file",
                "anchor": "page=1",
            },
        ),
    )
    artifacts.write_rows(root / "exceptions.csv", ISSUE_HEADER, ())
    artifacts.write_rows(
        root / "normalization_reviews.csv",
        NORMALIZATION_REVIEW_HEADER,
        (),
    )
    artifacts.write_rows(
        root / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "coinbase",
                "capture_uid": root.name,
                "capture_label": "2026-03-23T14-15-16Z",
                "capture_root_ref": f"evidence/raw/source/coinbase/{root.name}",
                "location_id": "coinbase:primary",
                "location_kind": "account",
                "location_label": "Primary",
                "parent_location_id": "",
                "location_path": "Primary",
                "identifier_kind": "account_wallet",
                "normalized_identifier": "coinbase:primary",
                "display_identifier": "coinbase:primary",
                "network_scope": "",
                "controller": "coinbase",
                "parent_location_label": "",
                "evidence_kind": "normalized_transactions",
                "evidence_capture_uid": root.name,
                "evidence_relative_path": "transactions.csv",
                "evidence_archive_member_path": "",
                "evidence_locator_kind": "raw_file",
                "evidence_anchor": "",
                "confidence": "high",
                "identifier_value": "coinbase:primary",
                "notes": "",
            },
        ),
    )


def _balance_row(*, quantity: str) -> dict[str, str]:
    return {
        "source": "coinbase",
        "location_id": "coinbase:primary",
        "instrument_id": "symbol:BTC@coinbase",
        "quantity": quantity,
        "as_of_at": "2026-03-23",
        "as_of_precision": "date",
        "balance_kind": "available",
        "notes": "",
    }
