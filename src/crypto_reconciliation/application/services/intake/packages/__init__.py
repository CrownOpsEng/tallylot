"""Package-level intake deduplication and merge rules."""

from __future__ import annotations

from .models import PackageRuleSummary, PlannedPackageItem
from .resolution import apply_package_rules

__all__ = [
    "PackageRuleSummary",
    "PlannedPackageItem",
    "apply_package_rules",
]
