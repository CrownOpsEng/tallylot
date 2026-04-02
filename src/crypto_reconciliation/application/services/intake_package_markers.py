"""Date, cycle, and logical-key helpers for intake package rules."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import PurePosixPath

from .intake_package_models import BundlePackage, PlannedPackageItem

COMPACT_TIMESTAMP_14 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
COMPACT_TIMESTAMP_12 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
DASHED_DATE = re.compile(r"(?<!\d)(20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)")


def material_indexes(items: list[PlannedPackageItem], indexes: list[int]) -> tuple[int, ...]:
    content_indexes = [index for index in indexes if not items[index].bundle_relative_path.startswith("archive/")]
    return tuple(content_indexes or indexes)


def logical_key(bundle_relative_path: str) -> str:
    path = PurePosixPath(bundle_relative_path)
    parts = list(path.parts)
    if parts and parts[0] in {"archive", "contents"}:
        parts = parts[1:]
    return "/".join(parts) if parts else path.name


def extract_datetimes(text: str) -> list[datetime]:
    values: list[datetime] = []
    for match in COMPACT_TIMESTAMP_14.finditer(text):
        try:
            values.append(datetime.strptime(match.group(0), "%Y%m%d%H%M%S").replace(tzinfo=UTC))
        except ValueError:
            continue
    for match in COMPACT_TIMESTAMP_12.finditer(text):
        token = match.group(0)
        if any(existing.strftime("%Y%m%d%H%M") == token for existing in values):
            continue
        try:
            values.append(datetime.strptime(token, "%Y%m%d%H%M").replace(tzinfo=UTC))
        except ValueError:
            continue
    for match in DASHED_DATE.finditer(text):
        try:
            values.append(datetime.strptime(match.group(0).replace("_", "-"), "%Y-%m-%d").replace(tzinfo=UTC))
        except ValueError:
            continue
    return values


def row_marker(item: PlannedPackageItem) -> datetime | None:
    markers: list[datetime] = []
    for field in (item.relative_path, item.archive_source_path, item.path, item.bundle_id):
        if field:
            markers.extend(extract_datetimes(field))
    return max(markers) if markers else None


def package_sort_key(package: BundlePackage) -> tuple[int, str, int, str]:
    timestamp = int(package.latest_marker.strftime("%Y%m%d%H%M%S")) if package.latest_marker is not None else -1
    cycle_day = package.cycle_day.isoformat() if package.cycle_day is not None else ""
    return (timestamp, cycle_day, package.material_count, package.bundle_id)


def same_export_cycle(primary: BundlePackage, candidate: BundlePackage) -> bool:
    if primary.mixed_cycle or candidate.mixed_cycle:
        return False
    if primary.cycle_day is not None and candidate.cycle_day is not None:
        return primary.cycle_day == candidate.cycle_day
    return True


def package_cycle_status(package: BundlePackage) -> str:
    if package.mixed_cycle:
        return "mixed_cycle"
    return "single_cycle" if package.cycle_day else "cycle_unknown"
