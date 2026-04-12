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
    BALANCE_REFERENCE_HEADER,
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
    balance_rows = artifacts.read_rows(assembled_root / "balance_snapshots.csv")
    evidence_rows = artifacts.read_rows(assembled_root / "balance_references.csv")
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 1
    assert response.excluded_capture_count == 1
    assert summary["included_capture_uids"] == ["01HV4A5H7VJH7M3Y5A6B7C8D9E"]
    assert summary["excluded_capture_uids"] == ["01HV4A5H7VJH7M3Y5A6B7C8D9F"]
    assert balance_rows[0]["quantity"] == "1.0"
    assert evidence_rows[0]["reference_kind"] == "source_document"
    assert evidence_rows[0]["support_ref"] == "statement-a.pdf#page=1"
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

    assert response.balance_snapshot_count == 2
    assert issue_rows[0]["kind"] == "assembly_semantic_conflict"
    assert issue_rows[0]["raw_file"] == "balance_snapshots.csv"


def test_source_assembly_removes_stale_optional_generated_artifacts_on_rerun(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (_capture_row(capture_uid, status="normalized"),),
    )
    capture_root = workspace_root / "working" / "normalized" / "captures" / capture_uid
    _write_capture_outputs(
        artifacts,
        capture_root,
        quantity="1.0",
        write_reference=True,
    )
    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"

    AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )
    (assembled_root / "operator-notes.txt").write_text(
        "operator-owned", encoding="utf-8"
    )
    (capture_root / "balance_references.csv").unlink()

    AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assert artifacts.read_rows(assembled_root / "balance_references.csv") == []
    assert not (assembled_root / "balance_reference_issues.csv").exists()
    assert (assembled_root / "operator-notes.txt").read_text(
        encoding="utf-8"
    ) == "operator-owned"


def test_source_assembly_summary_excludes_all_policy_blocked_captures(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row(
                "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                status="overlap_review_required",
            ),
        ),
    )

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 0
    assert response.excluded_capture_count == 1
    assert source_rows[0]["status"] == "normalized"
    assert source_rows[0]["assembly_status"] == "excluded"
    assert source_rows[0]["assembled_root_ref"] == ""


def test_source_assembly_excludes_capture_blocked_rows_from_pending(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row(
                "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                status="capture_blocked",
            ),
        ),
    )

    AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    summary = json.loads(
        (
            workspace_root
            / "working"
            / "normalized"
            / "sources"
            / "coinbase"
            / "assembly_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert summary["excluded_capture_count"] == 1
    assert summary["pending_capture_count"] == 0


def test_source_assembly_excludes_normalized_rows_missing_output_root(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (_capture_row(capture_uid, status="normalized"),),
    )

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    issue_rows = artifacts.read_rows(assembled_root / "assembly_issues.csv")
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 0
    assert response.excluded_capture_count == 1
    assert issue_rows[0]["kind"] == "assembly_missing_normalized_capture"
    assert capture_rows[-1]["status"] == "assembly_excluded"
    assert source_rows[0]["status"] == "normalized"
    assert source_rows[0]["assembly_status"] == "excluded"
    assert source_rows[0]["assembled_root_ref"] == ""


def test_source_assembly_leaves_not_normalized_captures_pending(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root, status="profiled")
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (_capture_row(capture_uid, status="profiled"),),
    )

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    issue_rows = artifacts.read_rows(assembled_root / "assembly_issues.csv")
    summary = json.loads(
        (assembled_root / "assembly_summary.json").read_text(encoding="utf-8")
    )
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 0
    assert response.excluded_capture_count == 0
    assert response.issue_count == 1
    assert issue_rows[0]["kind"] == "assembly_capture_not_ready"
    assert summary["pending_capture_uids"] == [capture_uid]
    assert capture_rows == [_capture_row(capture_uid, status="profiled")]
    assert source_rows[0]["status"] == "profiled"
    assert source_rows[0]["assembly_status"] == "pending"
    assert source_rows[0]["assembled_root_ref"] == ""


def test_source_assembly_reincludes_restored_missing_capture_output(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row(capture_uid, status="normalized"),
            _capture_row(capture_uid, status="assembly_excluded"),
        ),
    )
    capture_root = workspace_root / "working" / "normalized" / "captures" / capture_uid
    _write_capture_outputs(artifacts, capture_root, quantity="1.0")

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert response.included_capture_count == 1
    assert response.excluded_capture_count == 0
    assert (
        artifacts.read_rows(assembled_root / "balance_snapshots.csv")[0]["quantity"]
        == "1.0"
    )
    assert capture_rows[-1]["status"] == "assembly_included"
    assert source_rows[0]["status"] == "assembled"
    assert source_rows[0]["assembly_status"] == "assembled"


def test_source_assembly_preserves_policy_exclusion_after_rerun(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9F"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row(capture_uid, status="overlap_review_required"),
            _capture_row(capture_uid, status="assembly_excluded"),
        ),
    )
    capture_root = workspace_root / "working" / "normalized" / "captures" / capture_uid
    _write_capture_outputs(artifacts, capture_root, quantity="2.0")

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert response.included_capture_count == 0
    assert response.excluded_capture_count == 1
    assert not artifacts.read_rows(assembled_root / "balance_snapshots.csv")
    assert capture_rows[-1]["status"] == "assembly_excluded"


def test_source_assembly_honors_policy_resolution_before_missing_output_rerun(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    _write_source_inventory(artifacts, workspace_root)
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9F"
    _write_capture_registry(
        artifacts,
        workspace_root,
        (
            _capture_row(capture_uid, status="overlap_review_required"),
            _capture_row(capture_uid, status="normalized"),
            _capture_row(capture_uid, status="assembly_excluded"),
        ),
    )
    capture_root = workspace_root / "working" / "normalized" / "captures" / capture_uid
    _write_capture_outputs(artifacts, capture_root, quantity="2.0")

    response = AssembleSourceUseCase(artifacts).execute(
        AssembleSourceRequest(
            source="coinbase",
            workspace_root_ref=to_resource_ref(workspace_root),
        )
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert response.included_capture_count == 1
    assert response.excluded_capture_count == 0
    assert (
        artifacts.read_rows(assembled_root / "balance_snapshots.csv")[0]["quantity"]
        == "2.0"
    )
    assert capture_rows[-1]["status"] == "assembly_included"


def _write_source_inventory(
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
    *,
    status: str = "normalized",
) -> None:
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": "coinbase",
                "activity_after_cutoff": "unknown",
                "scope_status": "in_scope",
                "status": status,
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
    write_reference: bool = False,
) -> None:
    artifacts.write_rows(root / "facts.csv", FACT_HEADER, ())
    artifacts.write_json(root / "fact_annotations.json", [])
    artifacts.write_rows(
        root / "balance_snapshots.csv",
        BALANCE_SNAPSHOT_HEADER,
        (_balance_row(quantity=quantity),),
    )
    artifacts.write_rows(
        root / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        (
            {
                **_reference_row(quantity=quantity),
                "reference_kind": "source_document",
                "observed_at": "2026-03-23",
                "observed_precision": "date",
                "support_ref": "statement-a.pdf#page=1",
                "provider_family": "",
                "provider_locator": "",
                "provider_block_ref": "",
                "reviewed_by": "",
                "reviewed_at": "",
                "notes": "",
            },
        ),
    )
    if write_reference:
        artifacts.write_rows(
            root / "balance_references.csv",
            BALANCE_REFERENCE_HEADER,
            (
                {
                    **_reference_row(quantity=quantity),
                    "reference_kind": "operator_assertion",
                    "observed_at": "2026-03-23",
                    "observed_precision": "date",
                    "support_ref": "operator",
                    "provider_family": "",
                    "provider_locator": "",
                    "provider_block_ref": "",
                    "reviewed_by": "operator",
                    "reviewed_at": "2026-03-24 00:00:00",
                    "notes": "test fixture",
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
        "target_at": "2026-03-23",
        "target_precision": "date",
        "balance_kind": "available",
        "snapshot_basis": "fact_cutoff",
        "notes": "",
    }


def _reference_row(*, quantity: str) -> dict[str, str]:
    return {
        "source": "coinbase",
        "location_id": "coinbase:primary",
        "instrument_id": "symbol:BTC@coinbase",
        "quantity": quantity,
        "target_at": "2026-03-23",
        "target_precision": "date",
        "balance_kind": "available",
    }
