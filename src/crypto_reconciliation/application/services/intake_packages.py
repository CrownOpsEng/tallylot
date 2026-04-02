"""Package-level intake deduplication and merge rules."""

from __future__ import annotations

from .intake_package_models import PackageRuleSummary, PlannedPackageItem
from .intake_package_resolution import apply_package_rules

__all__ = [
    "PackageRuleSummary",
    "PlannedPackageItem",
    "apply_package_rules",
]
