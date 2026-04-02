"""Intake capability."""

from .apply_intake import ApplyIntakeUseCase
from .archive import ScanIssue, ScannedFile, ScannedTree, scanned_tree_files
from .build_manifest import BuildManifestUseCase
from .contracts import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
    IntakePlanResponse,
    ManifestRequest,
    ManifestResponse,
)
from .file_facts import IntakeFileFacts, detect_capture_id, inspect_intake_file
from .inventory import resolve_inventory_route
from .packages import PackageRuleSummary, PlannedPackageItem, apply_package_rules
from .plan_intake import PlanIntakeUseCase
from .routing import detect_source_folder, route_intake_file

__all__ = [
    "ApplyIntakeUseCase",
    "BuildManifestUseCase",
    "IntakeApplyRequest",
    "IntakeApplyResponse",
    "IntakeFileFacts",
    "IntakePlanRequest",
    "IntakePlanResponse",
    "ManifestRequest",
    "ManifestResponse",
    "PackageRuleSummary",
    "PlanIntakeUseCase",
    "PlannedPackageItem",
    "ScanIssue",
    "ScannedFile",
    "ScannedTree",
    "apply_package_rules",
    "detect_capture_id",
    "detect_source_folder",
    "inspect_intake_file",
    "resolve_inventory_route",
    "route_intake_file",
    "scanned_tree_files",
]
