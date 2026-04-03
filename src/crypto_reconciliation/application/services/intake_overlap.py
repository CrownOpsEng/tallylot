"""Existing-capture overlap checks for intake planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.services.intake_file_facts import IntakeFileFacts, inspect_intake_file
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


@dataclass(frozen=True)
class IntakeOverlapDecision:
    review_required: str = "no"
    review_codes: str = ""
    review_reason: str = ""


@dataclass(frozen=True)
class IntakeOverlapRequest:
    workspace_root: Path
    source_folder: str
    capture_id: str
    relative_path: str
    sha256: str
    size_bytes: int
    facts: IntakeFileFacts


def resolve_overlap_review(
    *,
    artifacts: ArtifactStorePort,
    request: IntakeOverlapRequest,
) -> IntakeOverlapDecision:
    manifest_reason = _manifest_overlap_reason(
        artifacts,
        request.workspace_root,
        request.relative_path,
        request.sha256,
        request.size_bytes,
    )
    capture_reason = _capture_overlap_reason(
        request.workspace_root,
        request.source_folder,
        request.capture_id,
        request.facts,
    )
    review_codes: list[str] = []
    review_reasons: list[str] = []
    if manifest_reason:
        review_codes.append("repo_manifest_overlap")
        review_reasons.append(manifest_reason)
    if capture_reason:
        review_codes.append("raw_capture_overlap")
        review_reasons.append(capture_reason)
    if not review_codes:
        return IntakeOverlapDecision()
    return IntakeOverlapDecision(
        review_required="yes",
        review_codes=";".join(review_codes),
        review_reason="; ".join(review_reasons),
    )


def _manifest_overlap_reason(
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    relative_path: str,
    sha256: str,
    size_bytes: int,
) -> str:
    source_root = workspace_root / "evidence" / "raw" / "source"
    if not source_root.exists():
        return ""
    filename = Path(relative_path).name
    for manifest_path in sorted(source_root.rglob("manifest.csv")):
        for row in artifacts.read_rows(manifest_path):
            row_sha256 = (row.get("sha256") or "").strip()
            row_filename = Path(row.get("filename", "")).name
            row_size = (row.get("size_bytes") or "").strip()
            if row_sha256 == sha256:
                return f"Existing repo manifest already contains this file under {manifest_path.parent}"
            if row_filename == filename and row_size == str(size_bytes):
                return f"Existing repo manifest already contains a matching file under {manifest_path.parent}"
    return ""


def _capture_overlap_reason(
    workspace_root: Path,
    source_folder: str,
    capture_id: str,
    facts: IntakeFileFacts,
) -> str:
    if not capture_id or not facts.min_timestamp or not facts.max_timestamp:
        return ""
    capture_root = workspace_root / "evidence" / "raw" / "source" / source_folder / capture_id
    if not capture_root.exists():
        return ""
    for path in sorted(file for file in capture_root.rglob("*") if file.is_file() and file.name != "manifest.csv"):
        existing_facts = inspect_intake_file(path, relative_path=path.name)
        if _windows_overlap(facts, existing_facts):
            return f"Existing raw capture for {source_folder}/{capture_id} has overlapping activity in {path}"
    return ""


def _windows_overlap(left: IntakeFileFacts, right: IntakeFileFacts) -> bool:
    if not left.min_timestamp or not left.max_timestamp or not right.min_timestamp or not right.max_timestamp:
        return False
    return not (left.max_timestamp < right.min_timestamp or right.max_timestamp < left.min_timestamp)
