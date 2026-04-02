"""Resolution engine for package-level intake deduplication and merge rules."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime

from .duplicates import apply_duplicate_decisions
from .markers import logical_key, material_indexes, package_sort_key, row_marker
from .merges import apply_merge_decisions
from .models import BundlePackage, PackageGroupKey, PackageRuleSummary, PlannedPackageItem, package_key
from .reviews import apply_default_decisions, apply_overlap_review_decisions


def apply_package_rules(
    items: list[PlannedPackageItem],
) -> tuple[list[PlannedPackageItem], PackageRuleSummary]:
    row_indexes: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        if item.category != "source_raw":
            continue
        row_indexes[(item.category, item.source_folder, item.capture_id, item.bundle_id)].append(index)

    packages_by_group: dict[PackageGroupKey, list[BundlePackage]] = defaultdict(list)
    for (category, source_folder, capture_id, bundle_id), indexes in row_indexes.items():
        group_key = (category, source_folder, capture_id)
        packages_by_group[group_key].append(build_package(items, group_key, bundle_id, indexes))

    summary = PackageRuleSummary()
    updates: dict[int, PlannedPackageItem] = {}
    for packages in packages_by_group.values():
        decisions, row_actions, package_summary = resolve_group(items, packages)
        summary = PackageRuleSummary(
            duplicate_packages=summary.duplicate_packages + package_summary.duplicate_packages,
            merge_primary_packages=summary.merge_primary_packages + package_summary.merge_primary_packages,
            merged_packages=summary.merged_packages + package_summary.merged_packages,
            overlap_packages=summary.overlap_packages + package_summary.overlap_packages,
            mixed_cycle_packages=summary.mixed_cycle_packages + package_summary.mixed_cycle_packages,
        )
        for index, item in enumerate(items):
            item_key = (item.category, item.source_folder, item.capture_id, item.bundle_id)
            decision = decisions.get(item_key)
            action = row_actions.get(index)
            if decision is None or action is None:
                continue
            replacement = replace(
                item,
                package_status=decision["package_status"],
                package_primary_bundle_id=decision["package_primary_bundle_id"],
                package_related_bundles=decision["package_related_bundles"],
                package_cycle_status=decision["package_cycle_status"],
                package_scope_status=decision["package_scope_status"],
                package_decision_reason=decision["package_decision_reason"],
                package_row_status=action["package_row_status"],
            )
            if decision["package_status"].startswith("duplicate_package"):
                replacement = replace(
                    replacement,
                    action="skip",
                    placement_status="package_duplicate_skip",
                )
            elif action["package_row_status"] == "package_merge_superseded_skip":
                replacement = replace(
                    replacement,
                    action="skip",
                    placement_status="package_merge_superseded_skip",
                )
            updates[index] = replacement

    updated_items = list(items)
    for index, replacement in updates.items():
        updated_items[index] = replacement
    return updated_items, summary


def build_package(
    items: list[PlannedPackageItem],
    group_key: PackageGroupKey,
    bundle_id: str,
    indexes: list[int],
) -> BundlePackage:
    resolved_material_indexes = material_indexes(items, indexes)
    logical_hashes: dict[str, Counter[str]] = defaultdict(Counter)
    logical_indexes: dict[str, list[int]] = defaultdict(list)
    markers: list[datetime] = []
    bundle_scope_tokens: set[str] = set()
    for index in indexes:
        marker = row_marker(items[index])
        if marker is not None:
            markers.append(marker)
        bundle_scope_tokens.update(items[index].scope_tokens)
    for index in resolved_material_indexes:
        bundle_logical_key = logical_key(items[index].bundle_relative_path)
        logical_hashes[bundle_logical_key][items[index].sha256] += 1
        logical_indexes[bundle_logical_key].append(index)
    marker_days = sorted({marker.date() for marker in markers})
    return BundlePackage(
        group_key=group_key,
        bundle_id=bundle_id,
        row_indexes=tuple(indexes),
        material_indexes=resolved_material_indexes,
        material_hashes=Counter(items[index].sha256 for index in resolved_material_indexes),
        material_count=len(resolved_material_indexes),
        logical_hashes=dict(logical_hashes),
        logical_indexes={key: tuple(value) for key, value in logical_indexes.items()},
        latest_marker=max(markers) if markers else None,
        cycle_day=marker_days[0] if len(marker_days) == 1 else None,
        mixed_cycle=len(marker_days) > 1,
        scope_tokens=frozenset(bundle_scope_tokens),
    )


def resolve_group(
    items: list[PlannedPackageItem],
    packages: list[BundlePackage],
) -> tuple[dict[tuple[str, str, str, str], dict[str, str]], dict[int, dict[str, str]], PackageRuleSummary]:
    decisions: dict[tuple[str, str, str, str], dict[str, str]] = {}
    row_actions = {
        index: {
            "package_row_status": "package_keep",
            "effective_bundle_id": items[index].bundle_id,
        }
        for package in packages
        for index in package.row_indexes
    }
    ordered = sorted(packages, key=package_sort_key, reverse=True)
    duplicate_keys, duplicate_packages = apply_duplicate_decisions(ordered, decisions, row_actions)
    remaining = [package for package in ordered if package_key(package) not in duplicate_keys]
    merge_primary_packages, merged_packages = apply_merge_decisions(items, remaining, decisions, row_actions)
    mixed_cycle_packages = apply_default_decisions(ordered, decisions)
    apply_overlap_review_decisions(ordered, decisions)
    return (
        decisions,
        row_actions,
        PackageRuleSummary(
            duplicate_packages=duplicate_packages,
            merge_primary_packages=merge_primary_packages,
            merged_packages=merged_packages,
            overlap_packages=sum(
                1 for decision in decisions.values() if decision["package_status"] == "overlap_partial_review"
            ),
            mixed_cycle_packages=mixed_cycle_packages,
        ),
    )
