"""Package-level intake deduplication and merge rules."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import PurePosixPath

type PackageGroupKey = tuple[str, str, str]
COMPACT_TIMESTAMP_14 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
COMPACT_TIMESTAMP_12 = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
DASHED_DATE = re.compile(r"(?<!\d)(20\d{2})[-_](\d{2})[-_](\d{2})(?!\d)")


@dataclass(frozen=True)
class PlannedPackageItem:
    path: str
    relative_path: str
    archive_source_path: str
    source_folder: str
    capture_id: str
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
class _BundlePackage:
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


def apply_package_rules(
    items: list[PlannedPackageItem],
) -> tuple[list[PlannedPackageItem], PackageRuleSummary]:
    row_indexes: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        if item.category != "source_raw":
            continue
        row_indexes[(item.category, item.source_folder, item.capture_id, item.bundle_id)].append(index)

    packages_by_group: dict[PackageGroupKey, list[_BundlePackage]] = defaultdict(list)
    for (category, source_folder, capture_id, bundle_id), indexes in row_indexes.items():
        group_key = (category, source_folder, capture_id)
        packages_by_group[group_key].append(_build_package(items, group_key, bundle_id, indexes))

    summary = PackageRuleSummary()
    updates: dict[int, PlannedPackageItem] = {}
    for group_key, packages in packages_by_group.items():
        del group_key
        decisions, row_actions, package_summary = _resolve_group(items, packages)
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


def _build_package(
    items: list[PlannedPackageItem],
    group_key: PackageGroupKey,
    bundle_id: str,
    indexes: list[int],
) -> _BundlePackage:
    material_indexes = _material_indexes(items, indexes)
    logical_hashes: dict[str, Counter[str]] = defaultdict(Counter)
    logical_indexes: dict[str, list[int]] = defaultdict(list)
    markers: list[datetime] = []
    scope_tokens: set[str] = set()
    for index in indexes:
        marker = _row_marker(items[index])
        if marker is not None:
            markers.append(marker)
        scope_tokens.update(items[index].scope_tokens)
    for index in material_indexes:
        logical_key = _logical_key(items[index].bundle_relative_path)
        logical_hashes[logical_key][items[index].sha256] += 1
        logical_indexes[logical_key].append(index)
    marker_days = sorted({marker.date() for marker in markers})
    return _BundlePackage(
        group_key=group_key,
        bundle_id=bundle_id,
        row_indexes=tuple(indexes),
        material_indexes=material_indexes,
        material_hashes=Counter(items[index].sha256 for index in material_indexes),
        material_count=len(material_indexes),
        logical_hashes=dict(logical_hashes),
        logical_indexes={key: tuple(value) for key, value in logical_indexes.items()},
        latest_marker=max(markers) if markers else None,
        cycle_day=marker_days[0] if len(marker_days) == 1 else None,
        mixed_cycle=len(marker_days) > 1,
        scope_tokens=frozenset(scope_tokens),
    )


def _resolve_group(
    items: list[PlannedPackageItem],
    packages: list[_BundlePackage],
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
    ordered = sorted(packages, key=_package_sort_key, reverse=True)
    duplicate_keys, duplicate_packages = _apply_duplicate_decisions(ordered, decisions, row_actions)
    remaining = [package for package in ordered if package_key(package) not in duplicate_keys]
    merge_primary_packages, merged_packages = _apply_merge_decisions(items, remaining, decisions, row_actions)
    mixed_cycle_packages = _apply_default_decisions(ordered, decisions)
    _apply_overlap_review_decisions(ordered, decisions)
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


def _material_indexes(items: list[PlannedPackageItem], indexes: list[int]) -> tuple[int, ...]:
    content_indexes = [index for index in indexes if not items[index].bundle_relative_path.startswith("archive/")]
    return tuple(content_indexes or indexes)


def _logical_key(bundle_relative_path: str) -> str:
    path = PurePosixPath(bundle_relative_path)
    parts = list(path.parts)
    if parts and parts[0] in {"archive", "contents"}:
        parts = parts[1:]
    return "/".join(parts) if parts else path.name


def _merge_related_bundles(existing: str, bundle_id: str) -> str:
    values = {item.strip() for item in existing.split(";") if item.strip()}
    values.add(bundle_id)
    return "; ".join(sorted(values))


def _counter_subset(left: Counter[str], right: Counter[str]) -> bool:
    return all(count <= right.get(key, 0) for key, count in left.items())


def _extract_datetimes(text: str) -> list[datetime]:
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


def _row_marker(item: PlannedPackageItem) -> datetime | None:
    markers: list[datetime] = []
    for field in (item.relative_path, item.archive_source_path, item.path, item.bundle_id):
        if field:
            markers.extend(_extract_datetimes(field))
    return max(markers) if markers else None


def _package_sort_key(package: _BundlePackage) -> tuple[int, str, int, str]:
    timestamp = int(package.latest_marker.strftime("%Y%m%d%H%M%S")) if package.latest_marker is not None else -1
    cycle_day = package.cycle_day.isoformat() if package.cycle_day is not None else ""
    return (timestamp, cycle_day, package.material_count, package.bundle_id)


def _same_export_cycle(primary: _BundlePackage, candidate: _BundlePackage) -> bool:
    if primary.mixed_cycle or candidate.mixed_cycle:
        return False
    if primary.cycle_day is not None and candidate.cycle_day is not None:
        return primary.cycle_day == candidate.cycle_day
    return True


def _compatible_scope(primary: _BundlePackage, candidate: _BundlePackage) -> bool:
    primary_material_scope = _material_scope_tokens(primary.scope_tokens)
    candidate_material_scope = _material_scope_tokens(candidate.scope_tokens)
    if primary_material_scope and candidate_material_scope:
        return bool(primary_material_scope & candidate_material_scope)
    if primary.scope_tokens and candidate.scope_tokens:
        return bool(primary.scope_tokens & candidate.scope_tokens)
    return True


def _can_supersede(primary: _BundlePackage, candidate: _BundlePackage) -> bool:
    if primary.latest_marker is None or candidate.latest_marker is None:
        return False
    if not _same_export_cycle(primary, candidate):
        return False
    return primary.latest_marker > candidate.latest_marker


def _evaluate_merge(
    primary: _BundlePackage,
    candidate: _BundlePackage,
    component_hashes: Counter[str],
    component_logical_hashes: dict[str, Counter[str]],
    items: list[PlannedPackageItem],
) -> tuple[bool, set[int], Counter[str], dict[str, Counter[str]]]:
    if not _same_export_cycle(primary, candidate):
        return False, set(), Counter(), {}
    if not _compatible_scope(primary, candidate):
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
                if items[index].sha256 in extra_hashes:
                    superseded_indexes.add(index)
            continue
        kept_logical_hashes[logical_key].update(candidate_hashes)
        kept_hashes.update(candidate_hashes)

    if not kept_hashes - component_hashes:
        return False, set(), Counter(), {}
    return True, superseded_indexes, kept_hashes, dict(kept_logical_hashes)


def _apply_duplicate_decisions(
    ordered: list[_BundlePackage],
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
            and _counter_subset(package.material_hashes, candidate.material_hashes)
        ]
        if not supersets:
            continue
        primary = sorted(supersets, key=_package_sort_key, reverse=True)[0]
        decisions[package_key_value] = {
            "package_status": (
                "duplicate_package_identical"
                if package.material_hashes == primary.material_hashes
                else "duplicate_package_subset"
            ),
            "package_primary_bundle_id": primary.bundle_id,
            "package_related_bundles": primary.bundle_id,
            "package_cycle_status": _package_cycle_status(package),
            "package_scope_status": _scope_status(package, primary),
            "package_decision_reason": "deterministic superset duplicate",
        }
        duplicate_keys.add(package_key_value)
        duplicate_packages += 1
        for index in package.row_indexes:
            row_actions[index]["package_row_status"] = "package_duplicate_skip"
    return duplicate_keys, duplicate_packages


def _apply_merge_decisions(
    items: list[PlannedPackageItem],
    remaining: list[_BundlePackage],
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
        merged_members: list[_BundlePackage] = []
        consumed.add(primary_key)
        for candidate in remaining:
            candidate_key = package_key(candidate)
            if candidate_key in consumed or candidate.bundle_id == primary.bundle_id:
                continue
            mergeable, superseded_indexes, kept_hashes, kept_logical_hashes = _evaluate_merge(
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
            _apply_merge_member_row_actions(row_actions, candidate, superseded_indexes, primary.bundle_id)
            component_hashes.update(kept_hashes)
            for logical_key, counter in kept_logical_hashes.items():
                component_logical_hashes.setdefault(logical_key, Counter()).update(counter)

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
                "package_scope_status": _scope_status(member, primary),
                "package_decision_reason": "same-cycle additive package merge member",
            }
    return merge_primary_packages, merged_packages


def _apply_default_decisions(
    ordered: list[_BundlePackage],
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
) -> int:
    mixed_cycle_packages = 0
    for package in ordered:
        package_key_value = package_key(package)
        if package_key_value in decisions:
            continue
        if package.mixed_cycle:
            mixed_cycle_packages += 1
            decisions[package_key_value] = {
                "package_status": "mixed_cycle_review",
                "package_primary_bundle_id": package.bundle_id,
                "package_related_bundles": "",
                "package_cycle_status": "mixed_cycle",
                "package_scope_status": "scope_unknown" if not package.scope_tokens else "single_scope_present",
                "package_decision_reason": "bundle contains files from multiple export-cycle days",
            }
            continue
        decisions[package_key_value] = {
            "package_status": "primary",
            "package_primary_bundle_id": package.bundle_id,
            "package_related_bundles": "",
            "package_cycle_status": "single_cycle" if package.cycle_day else "cycle_unknown",
            "package_scope_status": "scope_unknown" if not package.scope_tokens else "single_scope_present",
            "package_decision_reason": "kept primary package",
        }
    return mixed_cycle_packages


def _apply_overlap_review_decisions(
    ordered: list[_BundlePackage],
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
) -> None:
    unresolved = [package for package in ordered if decisions[package_key(package)]["package_status"] == "primary"]
    for index, left in enumerate(unresolved):
        if left.mixed_cycle:
            continue
        for right in unresolved[index + 1 :]:
            if not left.material_hashes & right.material_hashes:
                continue
            _set_overlap_decision(decisions, left, right)
            _set_overlap_decision(decisions, right, left)


def _apply_merge_member_row_actions(
    row_actions: dict[int, dict[str, str]],
    candidate: _BundlePackage,
    superseded_indexes: set[int],
    primary_bundle_id: str,
) -> None:
    for index in candidate.row_indexes:
        row_actions[index]["effective_bundle_id"] = primary_bundle_id
        row_actions[index]["package_row_status"] = "package_merge_into_primary"
    for index in superseded_indexes:
        row_actions[index]["package_row_status"] = "package_merge_superseded_skip"


def _set_overlap_decision(
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
    package: _BundlePackage,
    related: _BundlePackage,
) -> None:
    current = decisions[package_key(package)]
    if current["package_status"] == "primary":
        scope_status = _scope_status(package, related)
        decisions[package_key(package)] = {
            "package_status": "overlap_partial_review",
            "package_primary_bundle_id": package.bundle_id,
            "package_related_bundles": related.bundle_id,
            "package_cycle_status": "single_cycle" if package.cycle_day else "cycle_unknown",
            "package_scope_status": scope_status,
            "package_decision_reason": _overlap_reason(scope_status),
        }
        return
    current["package_related_bundles"] = _merge_related_bundles(current["package_related_bundles"], related.bundle_id)


def package_key(package: _BundlePackage) -> tuple[str, str, str, str]:
    return (*package.group_key, package.bundle_id)


def _package_cycle_status(package: _BundlePackage) -> str:
    if package.mixed_cycle:
        return "mixed_cycle"
    return "single_cycle" if package.cycle_day else "cycle_unknown"


def _scope_status(primary: _BundlePackage, candidate: _BundlePackage) -> str:
    primary_material_scope = _material_scope_tokens(primary.scope_tokens)
    candidate_material_scope = _material_scope_tokens(candidate.scope_tokens)
    if primary_material_scope and candidate_material_scope:
        return "matched_scope" if primary_material_scope & candidate_material_scope else "incompatible_scope"
    if primary.scope_tokens and candidate.scope_tokens:
        return "matched_scope" if primary.scope_tokens & candidate.scope_tokens else "incompatible_scope"
    if primary.scope_tokens or candidate.scope_tokens:
        return "partial_scope"
    return "scope_unknown"


def _material_scope_tokens(tokens: frozenset[str]) -> frozenset[str]:
    return frozenset(token for token in tokens if not token.startswith("label:"))


def _overlap_reason(scope_status: str) -> str:
    if scope_status == "incompatible_scope":
        return "shared material but explicit scope identifiers differ"
    return "shared material but export-cycle markers or contents do not justify merge"
