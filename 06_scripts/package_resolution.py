#!/usr/bin/env python3

"""Shared bundle/package consolidation and merge rules for intake."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import PurePosixPath
import re
from typing import Sequence


PACKAGE_KEY = tuple[str, str, str, str]

COMPACT_TIMESTAMP_14 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
COMPACT_TIMESTAMP_12 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
DASHED_DATE = re.compile(r"(?<!\d)(20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)")


@dataclass(frozen=True)
class BundlePackage:
    group_key: tuple[str, str, str]
    bundle_id: str
    row_indexes: tuple[int, ...]
    material_indexes: tuple[int, ...]
    material_hashes: Counter[str]
    material_count: int
    logical_hashes: dict[str, Counter[str]]
    logical_indexes: dict[str, tuple[int, ...]]
    latest_marker: datetime | None
    cycle_day: date | None
    mixed_cycle: bool


@dataclass(frozen=True)
class PackageResolution:
    package_decisions: dict[PACKAGE_KEY, dict[str, str]]
    row_actions: dict[int, dict[str, str]]


def _material_indexes(rows: Sequence[dict[str, str]], indexes: Sequence[int]) -> tuple[int, ...]:
    content_indexes = [index for index in indexes if not rows[index]["bundle_relative_path"].startswith("archive/")]
    return tuple(content_indexes or indexes)


def _material_hashes(rows: Sequence[dict[str, str]], indexes: Sequence[int]) -> Counter[str]:
    return Counter(rows[index]["sha256"] for index in indexes)


def _merge_related_bundles(existing: str, bundle_id: str) -> str:
    values = {item.strip() for item in existing.split(";") if item.strip()}
    values.add(bundle_id)
    return "; ".join(sorted(values))


def _counter_subset(left: Counter[str], right: Counter[str]) -> bool:
    return all(count <= right.get(key, 0) for key, count in left.items())


def _logical_key(row: dict[str, str]) -> str:
    path = PurePosixPath(row["bundle_relative_path"])
    parts = list(path.parts)
    if parts and parts[0] in {"archive", "contents"}:
        parts = parts[1:]
    return "/".join(parts) if parts else path.name


def _extract_datetimes(text: str) -> list[datetime]:
    values: list[datetime] = []
    for match in COMPACT_TIMESTAMP_14.finditer(text):
        try:
            values.append(datetime.strptime(match.group(0), "%Y%m%d%H%M%S"))
        except ValueError:
            continue
    for match in COMPACT_TIMESTAMP_12.finditer(text):
        token = match.group(0)
        if any(existing.strftime("%Y%m%d%H%M") == token for existing in values):
            continue
        try:
            values.append(datetime.strptime(token, "%Y%m%d%H%M"))
        except ValueError:
            continue
    for match in DASHED_DATE.finditer(text):
        try:
            values.append(datetime.strptime(match.group(0).replace("_", "-"), "%Y-%m-%d"))
        except ValueError:
            continue
    return values


def _row_marker(row: dict[str, str]) -> datetime | None:
    markers: list[datetime] = []
    for field in ("source_path", "archive_source_path", "path", "bundle_id"):
        value = row.get(field, "")
        if value:
            markers.extend(_extract_datetimes(value))
    return max(markers) if markers else None


def _build_package(rows: Sequence[dict[str, str]], group_key: tuple[str, str, str], bundle_id: str, indexes: Sequence[int]) -> BundlePackage:
    material_indexes = _material_indexes(rows, indexes)
    logical_hashes: dict[str, Counter[str]] = defaultdict(Counter)
    logical_indexes: dict[str, list[int]] = defaultdict(list)
    markers: list[datetime] = []
    for index in indexes:
        marker = _row_marker(rows[index])
        if marker is not None:
            markers.append(marker)
    for index in material_indexes:
        key = _logical_key(rows[index])
        logical_hashes[key][rows[index]["sha256"]] += 1
        logical_indexes[key].append(index)
    marker_days = sorted({marker.date() for marker in markers})
    return BundlePackage(
        group_key=group_key,
        bundle_id=bundle_id,
        row_indexes=tuple(indexes),
        material_indexes=material_indexes,
        material_hashes=_material_hashes(rows, material_indexes),
        material_count=len(material_indexes),
        logical_hashes=dict(logical_hashes),
        logical_indexes={key: tuple(value) for key, value in logical_indexes.items()},
        latest_marker=max(markers) if markers else None,
        cycle_day=marker_days[0] if len(marker_days) == 1 else None,
        mixed_cycle=len(marker_days) > 1,
    )


def _package_sort_key(package: BundlePackage) -> tuple[int, str, int, str]:
    timestamp = int(package.latest_marker.strftime("%Y%m%d%H%M%S")) if package.latest_marker is not None else -1
    cycle_day = package.cycle_day.isoformat() if package.cycle_day is not None else ""
    return (timestamp, cycle_day, package.material_count, package.bundle_id)


def _same_export_cycle(primary: BundlePackage, candidate: BundlePackage) -> bool:
    if primary.mixed_cycle or candidate.mixed_cycle:
        return False
    if primary.cycle_day is not None and candidate.cycle_day is not None:
        return primary.cycle_day == candidate.cycle_day
    return True


def _can_supersede(primary: BundlePackage, candidate: BundlePackage) -> bool:
    if primary.latest_marker is None or candidate.latest_marker is None:
        return False
    if not _same_export_cycle(primary, candidate):
        return False
    return primary.latest_marker > candidate.latest_marker


def _evaluate_merge(primary: BundlePackage, candidate: BundlePackage, component_hashes: Counter[str], component_logical_hashes: dict[str, Counter[str]], rows: Sequence[dict[str, str]]) -> tuple[bool, set[int], Counter[str], dict[str, Counter[str]]]:
    if not _same_export_cycle(primary, candidate):
        return False, set(), Counter(), {}
    shared_hashes = candidate.material_hashes & component_hashes
    if not shared_hashes:
        return False, set(), Counter(), {}

    superseded_indexes: set[int] = set()
    kept_hashes: Counter[str] = Counter()
    kept_logical_hashes: dict[str, Counter[str]] = defaultdict(Counter)
    for logical_key, candidate_hashes in candidate.logical_hashes.items():
        existing_hashes = component_logical_hashes.get(logical_key, Counter())
        extra_hashes = Counter(
            {hash_value: count for hash_value, count in candidate_hashes.items() if hash_value not in existing_hashes}
        )
        if extra_hashes and existing_hashes and not _can_supersede(primary, candidate):
            return False, set(), Counter(), {}
        if extra_hashes and existing_hashes:
            for index in candidate.logical_indexes[logical_key]:
                if rows[index]["sha256"] in extra_hashes:
                    superseded_indexes.add(index)
            continue
        kept_logical_hashes[logical_key].update(candidate_hashes)
        kept_hashes.update(candidate_hashes)

    contributed = kept_hashes - component_hashes
    if not contributed:
        return False, set(), Counter(), {}
    return True, superseded_indexes, kept_hashes, dict(kept_logical_hashes)


def resolve_bundle_packages(rows: list[dict[str, str]]) -> PackageResolution:
    grouped_indexes: dict[PACKAGE_KEY, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped_indexes[(row["role"], row["source_folder"], row["capture_id"], row["bundle_id"])].append(index)

    packages_by_group: dict[tuple[str, str, str], list[BundlePackage]] = defaultdict(list)
    for (role, source_folder, capture_id, bundle_id), indexes in grouped_indexes.items():
        group_key = (role, source_folder, capture_id)
        package = _build_package(rows, group_key, bundle_id, indexes)
        packages_by_group[group_key].append(package)

    package_decisions: dict[PACKAGE_KEY, dict[str, str]] = {}
    row_actions = {
        index: {
            "package_row_status": "package_keep",
            "effective_bundle_id": rows[index]["bundle_id"],
        }
        for index in range(len(rows))
    }

    for group_key, packages in packages_by_group.items():
        ordered = sorted(packages, key=_package_sort_key, reverse=True)
        duplicate_keys: set[PACKAGE_KEY] = set()

        for package in ordered:
            package_key = group_key + (package.bundle_id,)
            supersets = [
                candidate
                for candidate in ordered
                if candidate.bundle_id != package.bundle_id and _counter_subset(package.material_hashes, candidate.material_hashes)
            ]
            if not supersets:
                continue
            primary = sorted(supersets, key=_package_sort_key, reverse=True)[0]
            package_decisions[package_key] = {
                "package_status": (
                    "duplicate_package_identical" if package.material_hashes == primary.material_hashes else "duplicate_package_subset"
                ),
                "package_primary_bundle_id": primary.bundle_id,
                "package_related_bundles": primary.bundle_id,
                "package_cycle_status": "mixed_cycle" if package.mixed_cycle else ("single_cycle" if package.cycle_day else "cycle_unknown"),
            }
            duplicate_keys.add(package_key)
            for index in package.row_indexes:
                row_actions[index]["package_row_status"] = "package_duplicate_skip"

        remaining = [package for package in ordered if group_key + (package.bundle_id,) not in duplicate_keys]
        consumed: set[PACKAGE_KEY] = set()
        for primary in remaining:
            primary_key = group_key + (primary.bundle_id,)
            if primary_key in consumed:
                continue
            component_hashes = Counter(primary.material_hashes)
            component_logical_hashes = {key: Counter(value) for key, value in primary.logical_hashes.items()}
            merged_members: list[BundlePackage] = []
            consumed.add(primary_key)
            for candidate in remaining:
                candidate_key = group_key + (candidate.bundle_id,)
                if candidate_key in consumed or candidate.bundle_id == primary.bundle_id:
                    continue
                mergeable, superseded_indexes, kept_hashes, kept_logical_hashes = _evaluate_merge(
                    primary,
                    candidate,
                    component_hashes,
                    component_logical_hashes,
                    rows,
                )
                if not mergeable:
                    continue
                merged_members.append(candidate)
                consumed.add(candidate_key)
                for index in candidate.row_indexes:
                    row_actions[index]["effective_bundle_id"] = primary.bundle_id
                    row_actions[index]["package_row_status"] = "package_merge_into_primary"
                for index in superseded_indexes:
                    row_actions[index]["package_row_status"] = "package_merge_superseded_skip"
                component_hashes.update(kept_hashes)
                for logical_key, counter in kept_logical_hashes.items():
                    component_logical_hashes.setdefault(logical_key, Counter()).update(counter)

            if merged_members:
                package_decisions[primary_key] = {
                    "package_status": "merge_primary",
                    "package_primary_bundle_id": primary.bundle_id,
                    "package_related_bundles": "; ".join(sorted(member.bundle_id for member in merged_members)),
                    "package_cycle_status": "single_cycle" if primary.cycle_day else "cycle_unknown",
                }
                for member in merged_members:
                    member_key = group_key + (member.bundle_id,)
                    package_decisions[member_key] = {
                        "package_status": "merge_member",
                        "package_primary_bundle_id": primary.bundle_id,
                        "package_related_bundles": primary.bundle_id,
                        "package_cycle_status": "single_cycle" if member.cycle_day else "cycle_unknown",
                    }

        for package in ordered:
            package_key = group_key + (package.bundle_id,)
            if package_key in package_decisions:
                continue
            if package.mixed_cycle:
                package_decisions[package_key] = {
                    "package_status": "mixed_cycle_review",
                    "package_primary_bundle_id": package.bundle_id,
                    "package_related_bundles": "",
                    "package_cycle_status": "mixed_cycle",
                }
            else:
                package_decisions[package_key] = {
                    "package_status": "primary",
                    "package_primary_bundle_id": package.bundle_id,
                    "package_related_bundles": "",
                    "package_cycle_status": "single_cycle" if package.cycle_day else "cycle_unknown",
                }

        unresolved = [package for package in ordered if package_decisions[group_key + (package.bundle_id,)]["package_status"] == "primary"]
        for index, left in enumerate(unresolved):
            left_key = group_key + (left.bundle_id,)
            if left.mixed_cycle:
                continue
            for right in unresolved[index + 1 :]:
                right_key = group_key + (right.bundle_id,)
                if not (left.material_hashes & right.material_hashes):
                    continue
                if package_decisions[left_key]["package_status"] == "primary":
                    package_decisions[left_key] = {
                        "package_status": "overlap_partial_review",
                        "package_primary_bundle_id": left.bundle_id,
                        "package_related_bundles": right.bundle_id,
                        "package_cycle_status": "single_cycle" if left.cycle_day else "cycle_unknown",
                    }
                else:
                    package_decisions[left_key]["package_related_bundles"] = _merge_related_bundles(
                        package_decisions[left_key]["package_related_bundles"],
                        right.bundle_id,
                    )
                if package_decisions[right_key]["package_status"] == "primary":
                    package_decisions[right_key] = {
                        "package_status": "overlap_partial_review",
                        "package_primary_bundle_id": right.bundle_id,
                        "package_related_bundles": left.bundle_id,
                        "package_cycle_status": "single_cycle" if right.cycle_day else "cycle_unknown",
                    }
                else:
                    package_decisions[right_key]["package_related_bundles"] = _merge_related_bundles(
                        package_decisions[right_key]["package_related_bundles"],
                        left.bundle_id,
                    )

    return PackageResolution(package_decisions=package_decisions, row_actions=row_actions)
