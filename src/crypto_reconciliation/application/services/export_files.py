"""CSV export discovery helpers for service workflows."""

from __future__ import annotations

from pathlib import Path


def find_matching_csv_files(directory: Path, stem: str) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv" and stem.lower() in path.name.lower()
    )


def find_required_csv_export(directory: Path, stem: str) -> Path:
    matches = find_matching_csv_files(directory, stem)
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one export containing {stem!r} in {directory}")
    return matches[0]


def find_required_csv_exports(directory: Path, stems: tuple[str, ...]) -> dict[str, Path]:
    return {stem: find_required_csv_export(directory, stem) for stem in stems}
