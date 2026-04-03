"""Merge rules for intake package resolution."""

from __future__ import annotations

from collections import Counter, defaultdict

from .markers import same_export_cycle
from .models import BundlePackage, PlannedPackageItem, package_key
from .scope import compatible_scope, scope_status


def apply_merge_decisions(
    items: list[PlannedPackageItem],
    remaining: list[BundlePackage],
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
    row_actions: dict[int, dict[str, str]],
) -> tuple[int, int]:
    merge_primary_packages = 0
    merged_packages = 0
    consumed: set[tuple[str, str, str, str]] = set()
    for primary in remaining:
        primary_key = package_key(primary)
        if primary_key in consumed:
            continue
        component_hashes = Counter(primary.material_hashes)
        component_logical_hashes = {key: Counter(value) for key, value in primary.logical_hashes.items()}
        merged_members: list[BundlePackage] = []
        consumed.add(primary_key)
        for candidate in remaining:
            candidate_key = package_key(candidate)
            if candidate_key in consumed or candidate.bundle_id == primary.bundle_id:
                continue
            mergeable, superseded_indexes, kept_hashes, kept_logical_hashes = evaluate_merge(
                primary,
                candidate,
                component_hashes,
                component_logical_hashes,
                items,
            )
            if not mergeable:
                continue
            merged_members.append(candidate)
            consumed.add(candidate_key)
            apply_merge_member_row_actions(row_actions, candidate, superseded_indexes, primary.bundle_id)
            component_hashes.update(kept_hashes)
            for candidate_logical_key, counter in kept_logical_hashes.items():
                component_logical_hashes.setdefault(candidate_logical_key, Counter()).update(counter)

        if not merged_members:
            continue
        merge_primary_packages += 1
        decisions[primary_key] = {
            "package_status": "merge_primary",
            "package_primary_bundle_id": primary.bundle_id,
            "package_related_bundles": "; ".join(sorted(member.bundle_id for member in merged_members)),
            "package_cycle_status": "single_cycle" if primary.cycle_day else "cycle_unknown",
            "package_scope_status": "matched_scope" if primary.scope_tokens else "scope_unknown",
            "package_decision_reason": "same-cycle additive package merge",
        }
        for member in merged_members:
            merged_packages += 1
            decisions[package_key(member)] = {
                "package_status": "merge_member",
                "package_primary_bundle_id": primary.bundle_id,
                "package_related_bundles": primary.bundle_id,
                "package_cycle_status": "single_cycle" if member.cycle_day else "cycle_unknown",
                "package_scope_status": scope_status(member, primary),
                "package_decision_reason": "same-cycle additive package merge member",
            }
    return merge_primary_packages, merged_packages


def evaluate_merge(
    primary: BundlePackage,
    candidate: BundlePackage,
    component_hashes: Counter[str],
    component_logical_hashes: dict[str, Counter[str]],
    items: list[PlannedPackageItem],
) -> tuple[bool, set[int], Counter[str], dict[str, Counter[str]]]:
    if not same_export_cycle(primary, candidate):
        return False, set(), Counter(), {}
    if not compatible_scope(primary, candidate):
        return False, set(), Counter(), {}
    shared_hashes = candidate.material_hashes & component_hashes
    if not shared_hashes:
        return False, set(), Counter(), {}

    superseded_indexes: set[int] = set()
    kept_hashes: Counter[str] = Counter()
    kept_logical_hashes: dict[str, Counter[str]] = defaultdict(Counter)
    for candidate_logical_key, candidate_hashes in candidate.logical_hashes.items():
        existing_hashes = component_logical_hashes.get(candidate_logical_key, Counter())
        extra_hashes = Counter(
            {hash_value: count for hash_value, count in candidate_hashes.items() if hash_value not in existing_hashes}
        )
        if extra_hashes and existing_hashes and not can_supersede(primary, candidate):
            return False, set(), Counter(), {}
        if extra_hashes and existing_hashes:
            for index in candidate.logical_indexes[candidate_logical_key]:
                if items[index].sha256 in extra_hashes:
                    superseded_indexes.add(index)
            continue
        kept_logical_hashes[candidate_logical_key].update(candidate_hashes)
        kept_hashes.update(candidate_hashes)

    if not kept_hashes - component_hashes:
        return False, set(), Counter(), {}
    return True, superseded_indexes, kept_hashes, dict(kept_logical_hashes)


def can_supersede(primary: BundlePackage, candidate: BundlePackage) -> bool:
    if primary.latest_marker is None or candidate.latest_marker is None:
        return False
    if not same_export_cycle(primary, candidate):
        return False
    return primary.latest_marker > candidate.latest_marker


def apply_merge_member_row_actions(
    row_actions: dict[int, dict[str, str]],
    candidate: BundlePackage,
    superseded_indexes: set[int],
    primary_bundle_id: str,
) -> None:
    for index in candidate.row_indexes:
        row_actions[index]["effective_bundle_id"] = primary_bundle_id
        row_actions[index]["package_row_status"] = "package_merge_into_primary"
    for index in superseded_indexes:
        row_actions[index]["package_row_status"] = "package_merge_superseded_skip"
