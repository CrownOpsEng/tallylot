"""CoinTracking baseline export discovery helpers."""

from __future__ import annotations

from pathlib import Path

from .schema import REQUIRED_BASELINE_EXPORTS


def match_baseline_exports(export_dir: Path) -> int:
    present = sum(1 for stem in REQUIRED_BASELINE_EXPORTS if _find_matching_csv_files(export_dir, stem))
    return 0 if present == 0 else int(100 * present / len(REQUIRED_BASELINE_EXPORTS))


def find_required_baseline_exports(export_dir: Path) -> dict[str, Path]:
    return {stem: _find_required_csv_export(export_dir, stem) for stem in REQUIRED_BASELINE_EXPORTS}


def _find_matching_csv_files(directory: Path, stem: str) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv" and stem.lower() in path.name.lower()
    )


def _find_required_csv_export(directory: Path, stem: str) -> Path:
    matches = _find_matching_csv_files(directory, stem)
    if not matches:
        raise FileNotFoundError(f"expected exactly one export containing {stem!r} in {directory}")
    if len(matches) > 1:
        candidates = ", ".join(path.name for path in matches)
        raise ValueError(f"Ambiguous export containing {stem!r} in {directory}: {candidates}")
    return matches[0]
