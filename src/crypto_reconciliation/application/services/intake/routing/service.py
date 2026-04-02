"""Typed intake routing rules."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.intake.archive import ScannedFile
from crypto_reconciliation.application.services.intake.file_facts import IntakeFileFacts, detect_capture_id

from .classification import detect_source_folder
from .models import IntakeRoute
from .portfolio import (
    cointracking_capture_id,
    cointracking_sidecar_capture_id,
    is_cointracking_portfolio_export,
    is_cointracking_sidecar,
)
from .targets import RAW_SOURCE_SUFFIXES, is_working_derivative, raw_source_target_path, relative_target_path


def route_intake_file(
    entry: ScannedFile,
    *,
    incoming_dir: Path,
    workspace_root: Path,
    facts: IntakeFileFacts,
) -> IntakeRoute:
    route_key = (
        f"{entry.archive_source_path}::{entry.archive_member_path}"
        if entry.archive_member_path
        else entry.relative_path
    )
    if is_cointracking_portfolio_export(route_key):
        capture_id = cointracking_capture_id(entry.file_path) or detect_capture_id(route_key, facts) or "unknown"
        target_path = (
            workspace_root / "evidence" / "raw" / "portfolio" / "cointracking" / capture_id / Path(route_key).name
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_export",
            source_folder="cointracking",
            capture_id=capture_id,
            action="copy",
            target_path=target_path,
        )

    if is_cointracking_sidecar(route_key):
        capture_id = cointracking_sidecar_capture_id(entry, incoming_dir) or "unknown"
        relative_target = relative_target_path(route_key)
        target_path = workspace_root / "evidence" / "raw" / "portfolio" / "cointracking" / capture_id / relative_target
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_sidecar",
            source_folder="cointracking",
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=target_path,
        )

    source_folder = detect_source_folder(route_key, facts)
    capture_id = detect_capture_id(route_key, facts) or incoming_dir.name
    relative_target = relative_target_path(route_key)
    if is_working_derivative(route_key):
        return IntakeRoute(
            category="supporting_artifact",
            role="working_derivative",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=(
                workspace_root
                / "working"
                / "supporting_artifacts"
                / source_folder
                / incoming_dir.name
                / relative_target
            ),
        )
    if Path(route_key).suffix.lower() in RAW_SOURCE_SUFFIXES:
        target_path = raw_source_target_path(
            entry,
            workspace_root=workspace_root,
            source_folder=source_folder,
            capture_id=capture_id,
            relative_target=relative_target,
        )
        return IntakeRoute(
            category="source_raw",
            role="source_export",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=target_path,
        )
    return IntakeRoute(
        category="supporting_artifact",
        role="supporting_artifact",
        source_folder=source_folder,
        capture_id=capture_id,
        action="extract_copy" if entry.archive_member_path else "copy",
        target_path=(
            workspace_root / "working" / "supporting_artifacts" / source_folder / incoming_dir.name / relative_target
        ),
    )
