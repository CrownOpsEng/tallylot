from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_support.capture_roots import materialize_capture_root
from tallylot.application.capture_paths import (
    default_capture_normalized_root,
    require_capture_root,
)


def test_require_capture_root_returns_workspace_context(tmp_path: Path) -> None:
    capture_root = materialize_capture_root(tmp_path, source="fixture_source")

    context = require_capture_root(capture_root, expected_source="fixture_source")

    assert context.capture_root == capture_root
    assert str(context.metadata.capture_uid) == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert context.workspace_root == tmp_path / "workspace"
    assert (
        context.capture_root_ref
        == "evidence/raw/source/fixture_source/2026-03-23T14-15-16Z"
    )


def test_require_capture_root_rejects_paths_outside_capture_layout(
    tmp_path: Path,
) -> None:
    capture_root = tmp_path / "capture"
    capture_root.mkdir(parents=True)
    _write_capture_metadata(capture_root, source="fixture_source")

    with pytest.raises(
        ValueError,
        match="must be under evidence/raw/source/<source>/<capture_label>",
    ):
        require_capture_root(capture_root, expected_source="fixture_source")


def test_require_capture_root_rejects_capture_label_path_mismatch(
    tmp_path: Path,
) -> None:
    capture_root = materialize_capture_root(tmp_path, source="fixture_source")
    _write_capture_metadata(
        capture_root,
        source="fixture_source",
        capture_label="2026-03-24T14-15-16Z",
    )

    with pytest.raises(
        ValueError,
        match="path must match the capture.json source and capture_label",
    ):
        require_capture_root(capture_root, expected_source="fixture_source")


def test_default_capture_normalized_root_requires_valid_capture_root(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    with pytest.raises(ValueError, match="must contain capture.json"):
        default_capture_normalized_root(raw_dir)


def _write_capture_metadata(
    capture_root: Path,
    *,
    source: str,
    capture_label: str = "2026-03-23T14-15-16Z",
) -> None:
    (capture_root / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": source,
                "capture_label": capture_label,
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": f"incoming/{source}",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
