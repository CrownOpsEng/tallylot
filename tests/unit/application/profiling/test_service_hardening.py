from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.application.profiling import BuildProfileUseCase, ProfileRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import FakeSourceRegistry, MatchingSourceAdapter


def test_profile_service_rejects_ambiguous_adapter_matches(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(
        source_adapters=(
            MatchingSourceAdapter("alpha_adapter"),
            MatchingSourceAdapter("beta_adapter"),
        )
    )

    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(ValueError, match="ambiguous source adapter match"):
        service.create_profile("fixture", raw_dir)


def test_profile_service_rejects_missing_source_directories(tmp_path: Path) -> None:
    registry = FakeSourceRegistry(
        source_adapters=(MatchingSourceAdapter("alpha_adapter"),)
    )
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(FileNotFoundError, match="raw source directory does not exist"):
        service.create_profile("fixture", tmp_path / "missing")


def test_profile_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(
        ValueError,
        match="profile output directory must not be inside raw source directory",
    ):
        service.execute(
            ProfileRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                profile_output_ref=to_resource_ref(raw_dir / "profile"),
            )
        )


def test_profile_service_rejects_non_capture_roots(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = build_registry()
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(ValueError, match="must contain capture.json"):
        service.execute(
            ProfileRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                profile_output_ref=to_resource_ref(tmp_path / "profile"),
            )
        )


def test_profile_service_rejects_mismatched_capture_metadata(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "capture.json").write_text(
        (
            '{"capture_uid":"01HV4A5H7VJH7M3Y5A6B7C8D9E",'
            '"source":"other_source",'
            '"capture_label":"2026-03-23T14-15-16Z",'
            '"intake_started_at":"2026-03-23 14:15:16",'
            '"intake_completed_at":"2026-03-23 14:15:16",'
            '"intake_method":"source_intake_apply",'
            '"incoming_ref":"incoming/other_source",'
            '"manifest_fingerprint":"manifest:fixture",'
            '"status":"captured",'
            '"notes":""}'
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    service = BuildProfileUseCase(registry, FilesystemArtifactStore())

    with pytest.raises(ValueError, match="does not match requested source"):
        service.execute(
            ProfileRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                profile_output_ref=to_resource_ref(tmp_path / "profile"),
            )
        )


def test_profile_service_marks_capture_as_profiled(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
            "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,,,,,,,tx-1,BTC buy,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "fixture_source",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "captured",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/fixture_source",
                "capture_root_ref": "evidence/raw/source/fixture_source/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:fixture",
                "file_count": "1",
                "observed_period_start": "2023-08-06",
                "observed_period_end": "2023-08-06",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    service = BuildProfileUseCase(build_registry(), artifacts)

    service.execute(
        ProfileRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            profile_output_ref=to_resource_ref(tmp_path / "profile"),
        )
    )

    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    source_rows = artifacts.read_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )

    assert capture_rows[-1]["status"] == "profiled"
    assert source_rows == [
        {
            "source": "fixture_source",
            "activity_after_cutoff": "",
            "scope_status": "in_scope",
            "status": "profiled",
            "capture_count": "1",
            "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
            "latest_capture_label": "2026-03-23T14-15-16Z",
            "latest_capture_completed_at": "2026-03-23 14:15:16",
            "assembly_status": "pending",
            "assembled_root_ref": "",
            "adapter_hints": "",
            "notes": "",
        }
    ]


def test_profile_service_does_not_regress_existing_capture_status(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
            "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,,,,,,,tx-1,BTC buy,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "fixture_source",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "normalized",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/fixture_source",
                "capture_root_ref": "evidence/raw/source/fixture_source/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:fixture",
                "file_count": "1",
                "observed_period_start": "2023-08-06",
                "observed_period_end": "2023-08-06",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    service = BuildProfileUseCase(build_registry(), artifacts)

    service.execute(
        ProfileRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            profile_output_ref=to_resource_ref(tmp_path / "profile"),
        )
    )

    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert capture_rows[-1]["status"] == "normalized"
