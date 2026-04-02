"""Default and overlap-review rules for intake package resolution."""

from __future__ import annotations

from .package_models import BundlePackage, package_key
from .package_scope import overlap_reason, scope_status


def apply_default_decisions(
    ordered: list[BundlePackage],
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


def apply_overlap_review_decisions(
    ordered: list[BundlePackage],
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
) -> None:
    unresolved = [package for package in ordered if decisions[package_key(package)]["package_status"] == "primary"]
    for index, left in enumerate(unresolved):
        if left.mixed_cycle:
            continue
        for right in unresolved[index + 1 :]:
            if not left.material_hashes & right.material_hashes:
                continue
            set_overlap_decision(decisions, left, right)
            set_overlap_decision(decisions, right, left)


def set_overlap_decision(
    decisions: dict[tuple[str, str, str, str], dict[str, str]],
    package: BundlePackage,
    related: BundlePackage,
) -> None:
    current = decisions[package_key(package)]
    if current["package_status"] == "primary":
        resolved_scope_status = scope_status(package, related)
        decisions[package_key(package)] = {
            "package_status": "overlap_partial_review",
            "package_primary_bundle_id": package.bundle_id,
            "package_related_bundles": related.bundle_id,
            "package_cycle_status": "single_cycle" if package.cycle_day else "cycle_unknown",
            "package_scope_status": resolved_scope_status,
            "package_decision_reason": overlap_reason(resolved_scope_status),
        }
        return
    current["package_related_bundles"] = merge_related_bundles(current["package_related_bundles"], related.bundle_id)


def merge_related_bundles(existing: str, bundle_id: str) -> str:
    values = {item.strip() for item in existing.split(";") if item.strip()}
    values.add(bundle_id)
    return "; ".join(sorted(values))
