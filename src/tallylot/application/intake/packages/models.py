"""Typed models for package-level intake rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

type PackageGroupKey = tuple[str, str, str]


@dataclass(frozen=True)
class PlannedPackageItem:
    path: str
    relative_path: str
    archive_source_path: str
    source_folder: str
    capture_label: str
    category: str
    action: str
    sha256: str
    bundle_id: str
    bundle_relative_path: str
    scope_tokens: tuple[str, ...] = ()
    package_status: str = "primary"
    package_primary_bundle_id: str = ""
    package_related_bundles: str = ""
    package_cycle_status: str = ""
    package_scope_status: str = ""
    package_decision_reason: str = ""
    package_row_status: str = "package_keep"
    placement_status: str = "planned_copy"


@dataclass(frozen=True)
class PackageRuleSummary:
    duplicate_packages: int = 0
    merge_primary_packages: int = 0
    merged_packages: int = 0
    overlap_packages: int = 0
    mixed_cycle_packages: int = 0


@dataclass(frozen=True)
class BundlePackage:
    group_key: PackageGroupKey
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
    scope_tokens: frozenset[str]


def package_key(package: BundlePackage) -> tuple[str, str, str, str]:
    return (*package.group_key, package.bundle_id)
