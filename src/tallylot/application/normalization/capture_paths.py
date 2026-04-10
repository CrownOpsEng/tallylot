"""Capture-aware normalized workspace paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tallylot.ports.captures import CaptureMetadata


def load_capture_metadata(capture_root: Path) -> CaptureMetadata | None:
    metadata_path = capture_root / "capture.json"
    if not metadata_path.is_file():
        return None
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"capture metadata must be a JSON object: {metadata_path}")
    return CaptureMetadata.from_dict(cast(dict[str, object], payload))


def workspace_root_from_capture_root(
    capture_root: Path,
    metadata: CaptureMetadata,
) -> Path | None:
    if capture_root.name != metadata.capture_label:
        return None
    source_dir = capture_root.parent
    if source_dir.name != str(metadata.source):
        return None
    if (
        source_dir.parent.name != "source"
        or source_dir.parent.parent.name != "raw"
        or source_dir.parent.parent.parent.name != "evidence"
    ):
        return None
    return source_dir.parent.parent.parent.parent


def capture_normalized_root(workspace_root: Path, capture_uid: str) -> Path:
    return workspace_root / "working" / "normalized" / "captures" / capture_uid


def source_assembled_root(workspace_root: Path, source: str) -> Path:
    return workspace_root / "working" / "normalized" / "sources" / source


def default_capture_normalized_root(capture_root: Path) -> Path:
    metadata = load_capture_metadata(capture_root)
    if metadata is None:
        raise ValueError(
            "raw capture directory must contain capture.json when --output-dir is omitted"
        )
    workspace_root = workspace_root_from_capture_root(capture_root, metadata)
    if workspace_root is None:
        raise ValueError(
            "raw capture directory must be under evidence/raw/source/<source>/<capture_label> "
            "when --output-dir is omitted"
        )
    return capture_normalized_root(workspace_root, str(metadata.capture_uid))
