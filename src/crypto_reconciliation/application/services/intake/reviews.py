"""Review-field assembly helpers for intake planning."""

from __future__ import annotations

from .package_models import PlannedPackageItem
from .plan_models import PlannedItem


def merge_review_required(*values: str) -> str:
    return "yes" if any(value == "yes" for value in values) else "no"


def merge_review_values(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        for part in value.split(";"):
            stripped = part.strip()
            if stripped and stripped not in parts:
                parts.append(stripped)
    return "; ".join(parts) if any(" " in part for part in parts) else ";".join(parts)


def planned_review_required(item: PlannedItem, package_item: PlannedPackageItem) -> str:
    if package_item.package_status in {"overlap_partial_review", "mixed_cycle_review"}:
        return "yes"
    return item.review_required


def planned_review_codes(item: PlannedItem, package_item: PlannedPackageItem) -> str:
    extra_codes = ""
    if package_item.package_status == "overlap_partial_review":
        extra_codes = "package_overlap_review"
    elif package_item.package_status == "mixed_cycle_review":
        extra_codes = "package_cycle_mixed"
    return merge_review_values(item.review_codes, extra_codes)


def planned_review_reason(item: PlannedItem, package_item: PlannedPackageItem) -> str:
    extra_reason = ""
    if package_item.package_status == "overlap_partial_review":
        extra_reason = (
            f"Package overlap with {package_item.package_related_bundles}; {package_item.package_decision_reason}"
        )
    elif package_item.package_status == "mixed_cycle_review":
        extra_reason = package_item.package_decision_reason
    return merge_review_values(item.review_reason, extra_reason)
