"""Target-path and bundle-shape helpers for intake planning."""

from __future__ import annotations

from pathlib import Path

from .archive import ScannedFile
from .packages import PlannedPackageItem
from .plan_models import PlannedItem


def package_key(entry: ScannedFile) -> str:
    if entry.archive_source_path:
        return entry.archive_source_path
    relative_path = Path(entry.relative_path)
    return str(relative_path.parent) if relative_path.parent != Path() else entry.relative_path


def bundle_id(entry: ScannedFile, *, source_folder: str) -> str:
    if entry.archive_source_path:
        return Path(entry.archive_source_path).stem
    relative_path = Path(entry.relative_path)
    if relative_path.suffix.lower() == ".zip":
        return relative_path.stem
    if relative_path.parent == Path():
        return f"{source_folder}-loose"
    return relative_path.parent.name.replace(" ", "-").replace("_", "-").lower()


def bundle_relative_path(entry: ScannedFile) -> str:
    if entry.archive_member_path:
        return str(Path("contents") / Path(entry.archive_member_path))
    if Path(entry.relative_path).suffix.lower() == ".zip":
        return str(Path("archive") / Path(entry.relative_path).name)
    return Path(entry.relative_path).name


def effective_bundle_id(item: PlannedItem, package_item: PlannedPackageItem) -> str:
    if package_item.package_row_status == "package_merge_into_primary":
        return package_item.package_primary_bundle_id
    return item.bundle_id


def source_raw_target_path(
    workspace_root: Path,
    *,
    source_folder: str,
    capture_id: str,
    bundle_id_value: str,
    bundle_relative_path_value: str,
) -> Path:
    capture_root = workspace_root / "evidence" / "raw" / "source" / source_folder / capture_id
    if bundle_id_value.endswith("-loose"):
        return capture_root / bundle_relative_path_value
    return capture_root / bundle_id_value / bundle_relative_path_value


def override_target_source(target_path: Path, previous_source: str, new_source: str) -> Path:
    if previous_source == new_source:
        return target_path
    parts = list(target_path.parts)
    for index, part in enumerate(parts):
        if part == previous_source:
            parts[index] = new_source
            break
    return Path(*parts)
