"""Capture-aware workspace path and validation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from tallylot.ports.captures import CaptureMetadata


@dataclass(frozen=True)
class CaptureRootContext:
    capture_root: Path
    metadata: CaptureMetadata
    workspace_root: Path
    capture_root_ref: str


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
    layout = _capture_root_layout(capture_root)
    if layout is None:
        return None
    workspace_root, path_source, path_capture_label = layout
    if (
        path_source != str(metadata.source)
        or path_capture_label != metadata.capture_label
    ):
        return None
    return workspace_root


def require_capture_root(
    capture_root: Path,
    *,
    expected_source: str | None = None,
) -> CaptureRootContext:
    metadata = load_capture_metadata(capture_root)
    if metadata is None:
        raise ValueError(
            "raw capture root must contain capture.json and point to one "
            "materialized capture root"
        )
    layout = _capture_root_layout(capture_root)
    if layout is None:
        raise ValueError(
            "raw capture root must be under evidence/raw/source/<source>/<capture_label>"
        )
    workspace_root, path_source, path_capture_label = layout
    if expected_source is not None and str(metadata.source) != expected_source:
        raise ValueError(
            f"raw capture root source {metadata.source!s} does not match "
            f"requested source {expected_source}"
        )
    if (
        metadata.capture_label != path_capture_label
        or str(metadata.source) != path_source
    ):
        raise ValueError(
            "raw capture root path must match the capture.json source and capture_label"
        )
    return CaptureRootContext(
        capture_root=capture_root,
        metadata=metadata,
        workspace_root=workspace_root,
        capture_root_ref=capture_root.relative_to(workspace_root).as_posix(),
    )


def capture_normalized_root(workspace_root: Path, capture_uid: str) -> Path:
    return workspace_root / "working" / "normalized" / "captures" / capture_uid


def source_assembled_root(workspace_root: Path, source: str) -> Path:
    return workspace_root / "working" / "normalized" / "sources" / source


def evidence_set_product_root(workspace_root: Path, evidence_set_id: str) -> Path:
    return workspace_root / "working" / "products" / "evidence_sets" / evidence_set_id


def evidence_set_product_file(workspace_root: Path, evidence_set_id: str) -> Path:
    return (
        evidence_set_product_root(workspace_root, evidence_set_id) / "evidence_set.json"
    )


def evidence_set_compatibility_plan_file(
    workspace_root: Path, evidence_set_id: str
) -> Path:
    return (
        evidence_set_product_root(workspace_root, evidence_set_id)
        / "compatibility"
        / "translation_input_plan.json"
    )


def evidence_set_ref(workspace_root: Path, evidence_set_id: str) -> str:
    return (
        evidence_set_product_file(workspace_root, evidence_set_id)
        .relative_to(workspace_root)
        .as_posix()
    )


def default_capture_normalized_root(capture_root: Path) -> Path:
    context = require_capture_root(capture_root)
    return capture_normalized_root(
        context.workspace_root, str(context.metadata.capture_uid)
    )


def _capture_root_layout(capture_root: Path) -> tuple[Path, str, str] | None:
    path_capture_label = capture_root.name
    source_dir = capture_root.parent
    path_source = source_dir.name
    if (
        source_dir.parent.name != "source"
        or source_dir.parent.parent.name != "raw"
        or source_dir.parent.parent.parent.name != "evidence"
    ):
        return None
    return (
        source_dir.parent.parent.parent.parent,
        path_source,
        path_capture_label,
    )
