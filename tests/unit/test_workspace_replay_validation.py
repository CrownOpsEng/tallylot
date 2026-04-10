from __future__ import annotations

from pathlib import Path

from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER
from tools.workspace_replay_validation.comparison import _raw_capture_signature
from tools.workspace_replay_validation.workflow import _reference_captures


def test_reference_captures_ignore_non_materialized_registry_rows(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "coinbase",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "normalized",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/coinbase",
                "capture_root_ref": "evidence/raw/source/coinbase/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:present",
                "file_count": "1",
                "observed_period_start": "2026-03-23",
                "observed_period_end": "2026-03-23",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                "source": "coinbase",
                "capture_label": "2026-03-24T14-15-16Z",
                "status": "duplicate_blocked",
                "intake_started_at": "2026-03-24 14:15:16",
                "intake_completed_at": "2026-03-24 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/coinbase",
                "capture_root_ref": "evidence/raw/source/coinbase/2026-03-24T14-15-16Z",
                "manifest_fingerprint": "manifest:missing",
                "file_count": "1",
                "observed_period_start": "2026-03-24",
                "observed_period_end": "2026-03-24",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    present_root = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "coinbase"
        / "2026-03-23T14-15-16Z"
    )
    present_root.mkdir(parents=True)
    (present_root / "capture.json").write_text("{}", encoding="utf-8")
    (present_root / "manifest.csv").write_text(
        "relative_path,sha256,size_bytes\n", encoding="utf-8"
    )

    captures = _reference_captures(
        artifacts=artifacts,
        workspace_root=workspace_root,
        selected_sources=frozenset(),
    )

    assert len(captures) == 1
    assert captures[0].manifest_fingerprint == "manifest:present"


def test_raw_capture_signature_ignores_derived_capture_files(tmp_path: Path) -> None:
    raw_capture_root = tmp_path / "capture"
    raw_capture_root.mkdir()
    (raw_capture_root / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (raw_capture_root / "capture.json").write_text("{}", encoding="utf-8")
    (raw_capture_root / "manifest.csv").write_text("header\n", encoding="utf-8")
    (raw_capture_root / "manifest_issues.csv").write_text("header\n", encoding="utf-8")

    signature = _raw_capture_signature(FilesystemArtifactStore(), raw_capture_root)

    assert len(signature) == 1
    assert signature[0].startswith("transactions.csv|")
