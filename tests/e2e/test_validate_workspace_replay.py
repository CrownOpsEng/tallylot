from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TypeGuard

import pytest

from tallylot.application.intake.contracts import IntakeApplyRequest
from tallylot.application.capture_paths import (
    default_capture_normalized_root,
)
from tallylot.application.normalization.contracts import (
    AssembleSourceRequest,
    NormalizeRequest,
)
from tallylot.application.profiling.contracts import ProfileRequest
from tallylot.application.resource_refs import to_resource_ref, to_workspace_path
from tallylot.application.workspace.contracts import WorkspaceInitRequest
from tallylot.infrastructure.composition.runtime import (
    apply_intake_use_case,
    assemble_source_use_case,
    build_profile_use_case,
    initialize_workspace_use_case,
    normalize_source_use_case,
)
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.ports.captures import CaptureMetadata, SOURCE_INVENTORY_HEADER
from tools.adapter_packs import AdapterPack, select_adapter_packs
from tools.validate_workspace_replay import main

REPLAY_PACKS = select_adapter_packs(
    selected_ids=(
        "binance/mixed_history",
        "shakepay/cash_crypto_mix",
        "evm_explorer/chain_scoped_deposit",
    )
)


def _pack_id(pack: AdapterPack) -> str:
    return pack.id


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _expected_row_count(path: Path) -> int:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not _is_object_list(payload):
        raise TypeError(f"expected JSON array at {path}")
    return len(payload)


def _seed_reference_workspace(
    *,
    reference_workspace: Path,
    incoming_dir: Path,
    reference_report_dir: Path,
    pack: AdapterPack,
    artifacts: FilesystemArtifactStore,
) -> CaptureMetadata:
    initialize_workspace_use_case().execute(
        WorkspaceInitRequest(workspace_root_ref=to_workspace_path(reference_workspace))
    )
    artifacts.write_rows(
        reference_workspace / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": pack.source,
                "activity_after_cutoff": "",
                "scope_status": "in_scope",
                "status": "",
                "capture_count": "",
                "latest_capture_uid": "",
                "latest_capture_label": "",
                "latest_capture_completed_at": "",
                "assembly_status": "",
                "assembled_root_ref": "",
                "adapter_hints": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        reference_workspace / "analysis" / "issues" / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        ({"incoming_path_prefix": ".", "source": pack.source, "notes": ""},),
    )
    shutil.copytree(pack.raw_dir, incoming_dir)
    apply_intake_use_case().execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(reference_workspace),
            report_output_ref=to_resource_ref(reference_report_dir),
        )
    )
    intake_summary = json.loads(
        (reference_report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    raw_capture_root = (
        reference_workspace
        / "evidence"
        / "raw"
        / "source"
        / pack.source
        / str(intake_summary["planned_capture_label"])
    )
    metadata = CaptureMetadata.from_dict(
        json.loads((raw_capture_root / "capture.json").read_text(encoding="utf-8"))
    )
    normalized_root = default_capture_normalized_root(raw_capture_root)
    build_profile_use_case().execute(
        ProfileRequest(
            source=pack.source,
            raw_capture_ref=to_resource_ref(raw_capture_root),
            profile_output_ref=to_resource_ref(normalized_root),
        )
    )
    normalize_source_use_case().execute(
        NormalizeRequest(
            source=pack.source,
            raw_capture_ref=to_resource_ref(raw_capture_root),
            normalized_output_ref=to_resource_ref(normalized_root),
        )
    )
    assemble_source_use_case().execute(
        AssembleSourceRequest(
            source=pack.source,
            workspace_root_ref=to_resource_ref(reference_workspace),
        )
    )
    return metadata


@pytest.mark.parametrize("pack", REPLAY_PACKS, ids=_pack_id)
def test_validate_workspace_replay_matches_expected_source_metrics(
    pack: AdapterPack,
    tmp_path: Path,
) -> None:
    reference_workspace = tmp_path / "reference-workspace"
    candidate_workspace = tmp_path / "candidate-workspace"
    report_dir = tmp_path / "report"
    incoming_dir = tmp_path / "incoming"
    reference_report_dir = tmp_path / "reference-report"
    artifacts = FilesystemArtifactStore()
    metadata = _seed_reference_workspace(
        reference_workspace=reference_workspace,
        incoming_dir=incoming_dir,
        reference_report_dir=reference_report_dir,
        pack=pack,
        artifacts=artifacts,
    )

    exit_code = main(
        [
            "--reference-workspace",
            str(reference_workspace),
            "--candidate-workspace",
            str(candidate_workspace),
            "--report-dir",
            str(report_dir),
            "--source",
            pack.source,
        ]
    )

    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    source_metrics = next(
        row
        for row in artifacts.read_rows(report_dir / "source_metrics_parity.csv")
        if row["source"] == pack.source
    )

    assert exit_code == 0
    assert summary["passed"] is True
    assert summary["mismatch_count"] == 0
    assert source_metrics["status"] == "match"
    assert source_metrics["reference_fact_count"] == str(
        _expected_row_count(pack.expected_dir / "facts.json")
    )
    assert source_metrics["candidate_fact_count"] == str(
        _expected_row_count(pack.expected_dir / "facts.json")
    )
    assert source_metrics["reference_balance_count"] == str(
        _expected_row_count(pack.expected_dir / "balances.json")
    )
    assert source_metrics["candidate_balance_count"] == str(
        _expected_row_count(pack.expected_dir / "balances.json")
    )
    assert source_metrics["reference_balance_evidence_count"] == str(
        _expected_row_count(pack.expected_dir / "balance_evidence.json")
    )
    assert source_metrics["candidate_balance_evidence_count"] == str(
        _expected_row_count(pack.expected_dir / "balance_evidence.json")
    )
    assert (report_dir / "raw_capture_parity.csv").exists()
    assert (report_dir / "capture_registry_parity.csv").exists()
    assert (report_dir / "source_metrics_parity.csv").exists()
    assert (report_dir / "reconciliation_status_parity.csv").exists()
    assert (
        candidate_workspace
        / "working"
        / "normalized"
        / "sources"
        / pack.source
        / "assembly_summary.json"
    ).exists()
    candidate_capture_roots = tuple(
        path
        for path in (
            candidate_workspace / "working" / "normalized" / "captures"
        ).iterdir()
        if path.is_dir()
    )
    assert len(candidate_capture_roots) == 1
    assert candidate_capture_roots[0].name != str(metadata.capture_uid)


def test_validate_workspace_replay_emits_report_package(
    structured_source_dir: Path,
    tmp_path: Path,
) -> None:
    reference_workspace = tmp_path / "reference-workspace"
    candidate_workspace = tmp_path / "candidate-workspace"
    report_dir = tmp_path / "report"
    incoming_dir = tmp_path / "incoming"
    reference_report_dir = tmp_path / "reference-report"
    artifacts = FilesystemArtifactStore()

    initialize_workspace_use_case().execute(
        WorkspaceInitRequest(workspace_root_ref=to_workspace_path(reference_workspace))
    )
    artifacts.write_rows(
        reference_workspace / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": "fixture_source",
                "activity_after_cutoff": "",
                "scope_status": "in_scope",
                "status": "",
                "capture_count": "",
                "latest_capture_uid": "",
                "latest_capture_label": "",
                "latest_capture_completed_at": "",
                "assembly_status": "",
                "assembled_root_ref": "",
                "adapter_hints": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        reference_workspace / "analysis" / "issues" / "source_label_map.csv",
        ("incoming_path_prefix", "source", "notes"),
        ({"incoming_path_prefix": ".", "source": "fixture_source", "notes": ""},),
    )
    shutil.copytree(structured_source_dir, incoming_dir)
    apply_intake_use_case().execute(
        IntakeApplyRequest(
            incoming_capture_ref=to_resource_ref(incoming_dir),
            workspace_root_ref=to_workspace_path(reference_workspace),
            report_output_ref=to_resource_ref(reference_report_dir),
        )
    )
    intake_summary = json.loads(
        (reference_report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    raw_capture_root = (
        reference_workspace
        / "evidence"
        / "raw"
        / "source"
        / "fixture_source"
        / str(intake_summary["planned_capture_label"])
    )
    metadata = CaptureMetadata.from_dict(
        json.loads((raw_capture_root / "capture.json").read_text(encoding="utf-8"))
    )
    normalized_root = default_capture_normalized_root(raw_capture_root)
    build_profile_use_case().execute(
        ProfileRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_capture_root),
            profile_output_ref=to_resource_ref(normalized_root),
        )
    )
    normalize_source_use_case().execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_capture_root),
            normalized_output_ref=to_resource_ref(normalized_root),
        )
    )
    assemble_source_use_case().execute(
        AssembleSourceRequest(
            source="fixture_source",
            workspace_root_ref=to_resource_ref(reference_workspace),
        )
    )

    exit_code = main(
        [
            "--reference-workspace",
            str(reference_workspace),
            "--candidate-workspace",
            str(candidate_workspace),
            "--report-dir",
            str(report_dir),
            "--source",
            "fixture_source",
        ]
    )

    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert summary["passed"] is True
    assert summary["mismatch_count"] == 0
    assert (report_dir / "raw_capture_parity.csv").exists()
    assert (report_dir / "capture_registry_parity.csv").exists()
    assert (report_dir / "source_metrics_parity.csv").exists()
    assert (report_dir / "reconciliation_status_parity.csv").exists()
    assert (
        candidate_workspace
        / "working"
        / "normalized"
        / "sources"
        / "fixture_source"
        / "assembly_summary.json"
    ).exists()
    candidate_capture_roots = tuple(
        path
        for path in (
            candidate_workspace / "working" / "normalized" / "captures"
        ).iterdir()
        if path.is_dir()
    )
    assert len(candidate_capture_roots) == 1
    assert candidate_capture_roots[0].name != str(metadata.capture_uid)
