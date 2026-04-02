"""Target-path helpers for intake routing."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.intake.archive import ScannedFile

RAW_SOURCE_SUFFIXES = frozenset({".csv", ".json", ".zip"})
WORKING_DERIVATIVE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".xlsx", ".xls"})


def is_working_derivative(relative_path: str) -> bool:
    path = Path(relative_path.replace("::", "__"))
    return path.suffix.lower() in WORKING_DERIVATIVE_SUFFIXES or path.name.lower() == "test.csv"


def relative_target_path(relative_path: str) -> Path:
    return Path(relative_path.replace("::", "/members/"))


def raw_source_target_path(
    entry: ScannedFile,
    *,
    workspace_root: Path,
    source_folder: str,
    capture_id: str,
    relative_target: Path,
) -> Path:
    base_path = workspace_root / "evidence" / "raw" / "source" / source_folder / capture_id
    if entry.archive_member_path:
        archive_stem = Path(entry.archive_source_path).stem
        return base_path / archive_stem / "contents" / Path(entry.archive_member_path)
    if Path(entry.relative_path).suffix.lower() == ".zip":
        archive_stem = Path(entry.relative_path).stem
        return base_path / archive_stem / "archive" / Path(entry.relative_path).name
    return base_path / relative_target
