"""Package-level intake deduplication rules."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PlannedPackageItem:
    path: str
    source_folder: str
    category: str
    action: str
    sha256: str
    package_key: str
    package_status: str = "primary"
    placement_status: str = "planned_copy"


def apply_package_rules(
    items: list[PlannedPackageItem],
) -> tuple[list[PlannedPackageItem], int]:
    package_hashes: dict[tuple[str, str], set[str]] = defaultdict(set)
    package_items: dict[tuple[str, str], list[PlannedPackageItem]] = defaultdict(list)
    for item in items:
        if item.category != "source_raw":
            continue
        key = (item.source_folder, item.package_key)
        package_hashes[key].add(item.sha256)
        package_items[key].append(item)

    duplicate_packages = 0
    updated_items = list(items)
    replacement_by_path: dict[str, PlannedPackageItem] = {}
    grouped_keys = sorted(package_hashes, key=lambda key: (key[0], key[1]))
    for candidate_key in grouped_keys:
        candidate_hashes = package_hashes[candidate_key]
        for primary_key in grouped_keys:
            if candidate_key == primary_key or candidate_key[0] != primary_key[0]:
                continue
            primary_hashes = package_hashes[primary_key]
            if not candidate_hashes or not candidate_hashes < primary_hashes:
                continue
            duplicate_packages += 1
            for item in package_items[candidate_key]:
                replacement_by_path[item.path] = replace(
                    item,
                    action="skip",
                    package_status="duplicate_package_subset",
                    placement_status="package_duplicate_skip",
                )
            break

    for index, item in enumerate(updated_items):
        replacement = replacement_by_path.get(item.path)
        if replacement is not None:
            updated_items[index] = replacement
    return updated_items, duplicate_packages
