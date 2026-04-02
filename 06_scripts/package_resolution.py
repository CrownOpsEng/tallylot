#!/usr/bin/env python3

"""Shared bundle/package consolidation for intake."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BundlePackage:
    group_key: tuple[str, str, str]
    bundle_id: str
    row_indexes: tuple[int, ...]
    material_hashes: Counter[str]
    material_count: int


def _material_hashes(rows: Sequence[dict[str, str]], indexes: Sequence[int]) -> Counter[str]:
    content_indexes = [index for index in indexes if not rows[index]["bundle_relative_path"].startswith("archive/")]
    selected_indexes = content_indexes or list(indexes)
    return Counter(rows[index]["sha256"] for index in selected_indexes)


def _counter_subset(left: Counter[str], right: Counter[str]) -> bool:
    return all(count <= right.get(key, 0) for key, count in left.items())


def reconcile_bundle_packages(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    grouped_indexes: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = (row["role"], row["source_folder"], row["capture_id"], row["bundle_id"])
        grouped_indexes[key].append(index)

    packages_by_group: dict[tuple[str, str, str], list[BundlePackage]] = defaultdict(list)
    for (role, source_folder, capture_id, bundle_id), indexes in grouped_indexes.items():
        material_hashes = _material_hashes(rows, indexes)
        packages_by_group[(role, source_folder, capture_id)].append(
            BundlePackage(
                group_key=(role, source_folder, capture_id),
                bundle_id=bundle_id,
                row_indexes=tuple(indexes),
                material_hashes=material_hashes,
                material_count=sum(material_hashes.values()),
            )
        )

    decisions: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for group_key, packages in packages_by_group.items():
        ordered = sorted(packages, key=lambda item: (-item.material_count, item.bundle_id))
        for package in ordered:
            decisions[group_key + (package.bundle_id,)] = {
                "package_status": "primary",
                "package_primary_bundle_id": package.bundle_id,
                "package_related_bundles": "",
            }

        for package in ordered:
            supersets = [
                candidate
                for candidate in ordered
                if candidate.bundle_id != package.bundle_id and _counter_subset(package.material_hashes, candidate.material_hashes)
            ]
            if supersets:
                primary = sorted(supersets, key=lambda item: (-item.material_count, item.bundle_id))[0]
                status = "duplicate_package_identical" if package.material_hashes == primary.material_hashes else "duplicate_package_subset"
                decisions[group_key + (package.bundle_id,)] = {
                    "package_status": status,
                    "package_primary_bundle_id": primary.bundle_id,
                    "package_related_bundles": primary.bundle_id,
                }
                continue

            overlaps = [
                candidate.bundle_id
                for candidate in ordered
                if candidate.bundle_id != package.bundle_id
                and (package.material_hashes & candidate.material_hashes)
                and not _counter_subset(candidate.material_hashes, package.material_hashes)
                and not _counter_subset(package.material_hashes, candidate.material_hashes)
            ]
            if overlaps:
                decisions[group_key + (package.bundle_id,)] = {
                    "package_status": "overlap_partial_review",
                    "package_primary_bundle_id": package.bundle_id,
                    "package_related_bundles": "; ".join(sorted(overlaps)),
                }
    return decisions
