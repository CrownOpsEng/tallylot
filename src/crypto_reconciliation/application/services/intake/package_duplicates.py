"""Duplicate-package rules for intake package resolution."""

from __future__ import annotations

from collections import Counter

from .package_markers import package_cycle_status, package_sort_key
from .package_models import BundlePackage, package_key
from .package_scope import scope_status


def apply_duplicate_decisions(
    ordered: list[BundlePackage],
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
    row_actions: dict[int, dict[str, str]],
) -> tuple[set[tuple[str, str, str, str]], int]:
    ordered_rank = {package.bundle_id: rank for rank, package in enumerate(ordered)}
    duplicate_keys: set[tuple[str, str, str, str]] = set()
    duplicate_packages = 0
    for package in ordered:
        package_key_value = package_key(package)
        supersets = [
            candidate
            for candidate in ordered
            if candidate.bundle_id != package.bundle_id
            and ordered_rank[candidate.bundle_id] < ordered_rank[package.bundle_id]
            and counter_subset(package.material_hashes, candidate.material_hashes)
        ]
        if not supersets:
            continue
        primary = sorted(supersets, key=package_sort_key, reverse=True)[0]
        decisions[package_key_value] = {
            "package_status": (
                "duplicate_package_identical"
                if package.material_hashes == primary.material_hashes
                else "duplicate_package_subset"
            ),
            "package_primary_bundle_id": primary.bundle_id,
            "package_related_bundles": primary.bundle_id,
            "package_cycle_status": package_cycle_status(package),
            "package_scope_status": scope_status(package, primary),
            "package_decision_reason": "deterministic superset duplicate",
        }
        duplicate_keys.add(package_key_value)
        duplicate_packages += 1
        for index in package.row_indexes:
            row_actions[index]["package_row_status"] = "package_duplicate_skip"
    return duplicate_keys, duplicate_packages


def counter_subset(left: Counter[str], right: Counter[str]) -> bool:
    return all(count <= right.get(key, 0) for key, count in left.items())
