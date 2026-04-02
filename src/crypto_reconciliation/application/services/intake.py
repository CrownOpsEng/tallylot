"""Archive-aware source intake planning and apply services."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.dtos import (
    IntakeApplyRequest,
    IntakeApplyResponse,
    IntakePlanRequest,
    IntakePlanResponse,
)
from crypto_reconciliation.application.services.archive_scan import ScannedFile, scanned_tree_files
from crypto_reconciliation.application.services.intake_file_facts import inspect_intake_file
from crypto_reconciliation.application.services.intake_inventory import resolve_inventory_route
from crypto_reconciliation.application.services.intake_overlap import (
    IntakeOverlapRequest,
    resolve_overlap_review,
)
from crypto_reconciliation.application.services.intake_packages import (
    PlannedPackageItem,
    apply_package_rules,
)
from crypto_reconciliation.application.services.intake_routing import route_intake_file
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

PLAN_HEADER = (
    "path",
    "relative_path",
    "archive_source_path",
    "archive_member_path",
    "category",
    "role",
    "source_folder",
    "capture_id",
    "bundle_id",
    "bundle_relative_path",
    "action",
    "package_key",
    "package_status",
    "package_primary_bundle_id",
    "package_related_bundles",
    "package_cycle_status",
    "package_scope_status",
    "package_decision_reason",
    "package_row_status",
    "placement_status",
    "review_required",
    "review_codes",
    "review_reason",
    "inventory_match_status",
    "target_path",
)
ISSUE_HEADER = ("relative_path", "severity", "kind", "message")


@dataclass(frozen=True)
class _PlannedItem:
    source_path: Path
    relative_path: str
    archive_source_path: str
    archive_member_path: str
    category: str
    role: str
    source_folder: str
    capture_id: str
    bundle_id: str
    bundle_relative_path: str
    action: str
    package_key: str
    package_status: str
    package_primary_bundle_id: str
    package_related_bundles: str
    package_cycle_status: str
    package_scope_status: str
    package_decision_reason: str
    package_row_status: str
    placement_status: str
    review_required: str
    review_codes: str
    review_reason: str
    inventory_match_status: str
    sha256: str
    scope_tokens: tuple[str, ...]
    target_path: Path

    def to_row(self) -> dict[str, str]:
        return {
            "path": str(self.source_path),
            "relative_path": self.relative_path,
            "archive_source_path": self.archive_source_path,
            "archive_member_path": self.archive_member_path,
            "category": self.category,
            "role": self.role,
            "source_folder": self.source_folder,
            "capture_id": self.capture_id,
            "bundle_id": self.bundle_id,
            "bundle_relative_path": self.bundle_relative_path,
            "action": self.action,
            "package_key": self.package_key,
            "package_status": self.package_status,
            "package_primary_bundle_id": self.package_primary_bundle_id,
            "package_related_bundles": self.package_related_bundles,
            "package_cycle_status": self.package_cycle_status,
            "package_scope_status": self.package_scope_status,
            "package_decision_reason": self.package_decision_reason,
            "package_row_status": self.package_row_status,
            "placement_status": self.placement_status,
            "review_required": self.review_required,
            "review_codes": self.review_codes,
            "review_reason": self.review_reason,
            "inventory_match_status": self.inventory_match_status,
            "target_path": str(self.target_path),
        }


class SourceIntakeService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def plan(self, request: IntakePlanRequest) -> IntakePlanResponse:
        planned_items, issue_rows = self._plan_rows(request)
        self._write_reports(request.report_dir, planned_items, issue_rows, copied_count=0)
        return IntakePlanResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            planned_copy_count=sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
        )

    def apply(self, request: IntakeApplyRequest) -> IntakeApplyResponse:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            planned_items = _build_planned_items(
                scanned_tree.files,
                self._artifacts,
                IntakePlanRequest(
                    incoming_dir=request.incoming_dir,
                    workspace_root=request.workspace_root,
                    report_dir=request.report_dir,
                    inspect_archives=request.inspect_archives,
                ),
            )
            issue_rows = [
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            ]
            for item in planned_items:
                if item.action not in {"copy", "extract_copy"}:
                    continue
                item.target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.source_path, item.target_path)
                copied_count += 1
            _write_capture_manifests(self._artifacts, request.workspace_root, planned_items)
        self._write_reports(request.report_dir, planned_items, issue_rows, copied_count=copied_count)
        return IntakeApplyResponse(
            report_dir=request.report_dir,
            file_count=len(planned_items),
            issue_count=len(issue_rows),
            copied_count=copied_count,
        )

    def _plan_rows(
        self,
        request: IntakePlanRequest,
    ) -> tuple[list[_PlannedItem], list[dict[str, str]]]:
        request.report_dir.mkdir(parents=True, exist_ok=True)
        source_root = (
            request.workspace_root / "evidence" / "raw" / "source" / "unclassified" / request.incoming_dir.name
        )
        planned_items: list[_PlannedItem] = []
        issue_rows: list[dict[str, str]] = []
        with scanned_tree_files(
            request.incoming_dir,
            inspect_archives=request.inspect_archives,
        ) as scanned_tree:
            del source_root
            planned_items.extend(_build_planned_items(scanned_tree.files, self._artifacts, request))
            issue_rows.extend(
                {
                    "relative_path": issue.relative_path,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in scanned_tree.issues
            )
        return planned_items, issue_rows

    def _write_reports(
        self,
        report_dir: Path,
        planned_items: list[_PlannedItem],
        issue_rows: list[dict[str, str]],
        *,
        copied_count: int,
    ) -> None:
        self._artifacts.write_rows(
            report_dir / "intake_plan.csv",
            PLAN_HEADER,
            (item.to_row() for item in planned_items),
        )
        self._artifacts.write_rows(report_dir / "intake_issues.csv", ISSUE_HEADER, issue_rows)
        self._artifacts.write_json(
            report_dir / "intake_summary.json",
            {
                "file_count": len(planned_items),
                "issue_count": len(issue_rows),
                "copied_count": copied_count,
                "planned_copy_count": sum(1 for item in planned_items if item.action in {"copy", "extract_copy"}),
                "duplicate_packages": len(
                    {
                        (item.source_folder, item.capture_id, item.bundle_id)
                        for item in planned_items
                        if item.package_status.startswith("duplicate_package")
                    }
                ),
                "merge_primary_packages": len(
                    {
                        (item.source_folder, item.capture_id, item.bundle_id)
                        for item in planned_items
                        if item.package_status == "merge_primary"
                    }
                ),
                "merged_packages": len(
                    {
                        (item.source_folder, item.capture_id, item.bundle_id)
                        for item in planned_items
                        if item.package_status == "merge_member"
                    }
                ),
                "overlap_packages": len(
                    {
                        (item.source_folder, item.capture_id, item.bundle_id)
                        for item in planned_items
                        if item.package_status == "overlap_partial_review"
                    }
                ),
                "mixed_cycle_packages": len(
                    {
                        (item.source_folder, item.capture_id, item.bundle_id)
                        for item in planned_items
                        if item.package_status == "mixed_cycle_review"
                    }
                ),
            },
        )


def _build_planned_items(
    files: tuple[ScannedFile, ...],
    artifacts: ArtifactStorePort,
    request: IntakePlanRequest,
) -> list[_PlannedItem]:
    planned_items: list[_PlannedItem] = []
    for entry in files:
        relative_path = entry.archive_member_path or entry.relative_path
        facts = inspect_intake_file(entry.file_path, relative_path=relative_path)
        route = route_intake_file(
            entry,
            incoming_dir=request.incoming_dir,
            workspace_root=request.workspace_root,
            facts=facts,
        )
        bundle_id = _bundle_id(entry, source_folder=route.source_folder)
        bundle_relative_path = _bundle_relative_path(entry)
        inventory_route = resolve_inventory_route(
            artifacts=artifacts,
            workspace_root=request.workspace_root,
            source_folder=route.source_folder,
            facts=facts,
        )
        overlap_review = resolve_overlap_review(
            artifacts=artifacts,
            request=IntakeOverlapRequest(
                workspace_root=request.workspace_root,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                relative_path=relative_path,
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
                facts=facts,
            ),
        )
        source_target_path = (
            _source_raw_target_path(
                request.workspace_root,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                bundle_id=bundle_id,
                bundle_relative_path=bundle_relative_path,
            )
            if route.category == "source_raw"
            else _override_target_source(route.target_path, route.source_folder, inventory_route.source_folder)
        )
        planned_items.append(
            _PlannedItem(
                source_path=entry.file_path,
                relative_path=relative_path,
                archive_source_path=entry.archive_source_path,
                archive_member_path=entry.archive_member_path,
                category=route.category,
                role=route.role,
                source_folder=inventory_route.source_folder,
                capture_id=route.capture_id,
                bundle_id=bundle_id,
                bundle_relative_path=bundle_relative_path,
                action=route.action,
                package_key=_package_key(entry),
                package_status="primary",
                package_primary_bundle_id=bundle_id,
                package_related_bundles="",
                package_cycle_status="",
                package_scope_status="",
                package_decision_reason="",
                package_row_status="package_keep",
                placement_status="planned_copy" if route.action in {"copy", "extract_copy"} else "inspect_only",
                review_required=_merge_review_required(
                    route.review_required,
                    inventory_route.review_required,
                    overlap_review.review_required,
                ),
                review_codes=_merge_review_values(
                    route.review_codes,
                    inventory_route.review_codes,
                    overlap_review.review_codes,
                ),
                review_reason=_merge_review_values(
                    route.review_reason,
                    inventory_route.review_reason,
                    overlap_review.review_reason,
                ),
                inventory_match_status=inventory_route.inventory_match_status,
                sha256=entry.sha256,
                scope_tokens=facts.scope_tokens,
                target_path=source_target_path,
            )
        )
    package_items = [
        PlannedPackageItem(
            path=str(item.source_path),
            relative_path=item.relative_path,
            archive_source_path=item.archive_source_path,
            source_folder=item.source_folder,
            capture_id=item.capture_id,
            category=item.category,
            action=item.action,
            sha256=item.sha256,
            bundle_id=item.bundle_id,
            bundle_relative_path=item.bundle_relative_path,
            scope_tokens=item.scope_tokens,
            package_status=item.package_status,
            package_primary_bundle_id=item.package_primary_bundle_id,
            package_related_bundles=item.package_related_bundles,
            package_cycle_status=item.package_cycle_status,
            package_scope_status=item.package_scope_status,
            package_decision_reason=item.package_decision_reason,
            package_row_status=item.package_row_status,
            placement_status=item.placement_status,
        )
        for item in planned_items
    ]
    updated_package_items, _ = apply_package_rules(package_items)
    package_map = {item.path: item for item in updated_package_items}
    return [
        _PlannedItem(
            source_path=item.source_path,
            relative_path=item.relative_path,
            archive_source_path=item.archive_source_path,
            archive_member_path=item.archive_member_path,
            category=item.category,
            role=item.role,
            source_folder=item.source_folder,
            capture_id=item.capture_id,
            bundle_id=_effective_bundle_id(item, package_map[str(item.source_path)]),
            bundle_relative_path=item.bundle_relative_path,
            action=package_map[str(item.source_path)].action,
            package_key=item.package_key,
            package_status=package_map[str(item.source_path)].package_status,
            package_primary_bundle_id=package_map[str(item.source_path)].package_primary_bundle_id,
            package_related_bundles=package_map[str(item.source_path)].package_related_bundles,
            package_cycle_status=package_map[str(item.source_path)].package_cycle_status,
            package_scope_status=package_map[str(item.source_path)].package_scope_status,
            package_decision_reason=package_map[str(item.source_path)].package_decision_reason,
            package_row_status=package_map[str(item.source_path)].package_row_status,
            placement_status=package_map[str(item.source_path)].placement_status,
            review_required=_planned_review_required(item, package_map[str(item.source_path)]),
            review_codes=_planned_review_codes(item, package_map[str(item.source_path)]),
            review_reason=_planned_review_reason(item, package_map[str(item.source_path)]),
            inventory_match_status=item.inventory_match_status,
            sha256=item.sha256,
            scope_tokens=item.scope_tokens,
            target_path=(
                _source_raw_target_path(
                    request.workspace_root,
                    source_folder=item.source_folder,
                    capture_id=item.capture_id,
                    bundle_id=_effective_bundle_id(item, package_map[str(item.source_path)]),
                    bundle_relative_path=item.bundle_relative_path,
                )
                if item.category == "source_raw"
                else item.target_path
            ),
        )
        for item in planned_items
    ]


def _package_key(entry: ScannedFile) -> str:
    if entry.archive_source_path:
        return entry.archive_source_path
    relative_path = Path(entry.relative_path)
    return str(relative_path.parent) if relative_path.parent != Path() else entry.relative_path


def _bundle_id(entry: ScannedFile, *, source_folder: str) -> str:
    if entry.archive_source_path:
        return Path(entry.archive_source_path).stem
    relative_path = Path(entry.relative_path)
    if relative_path.suffix.lower() == ".zip":
        return relative_path.stem
    if relative_path.parent == Path():
        return f"{source_folder}-loose"
    return relative_path.parent.name.replace(" ", "-").replace("_", "-").lower()


def _bundle_relative_path(entry: ScannedFile) -> str:
    if entry.archive_member_path:
        return str(Path("contents") / Path(entry.archive_member_path))
    if Path(entry.relative_path).suffix.lower() == ".zip":
        return str(Path("archive") / Path(entry.relative_path).name)
    return Path(entry.relative_path).name


def _effective_bundle_id(item: _PlannedItem, package_item: PlannedPackageItem) -> str:
    if package_item.package_row_status == "package_merge_into_primary":
        return package_item.package_primary_bundle_id
    return item.bundle_id


def _source_raw_target_path(
    workspace_root: Path,
    *,
    source_folder: str,
    capture_id: str,
    bundle_id: str,
    bundle_relative_path: str,
) -> Path:
    capture_root = workspace_root / "evidence" / "raw" / "source" / source_folder / capture_id
    if bundle_id.endswith("-loose"):
        return capture_root / bundle_relative_path
    return capture_root / bundle_id / bundle_relative_path


def _planned_review_required(item: _PlannedItem, package_item: PlannedPackageItem) -> str:
    if package_item.package_status in {"overlap_partial_review", "mixed_cycle_review"}:
        return "yes"
    return item.review_required


def _planned_review_codes(item: _PlannedItem, package_item: PlannedPackageItem) -> str:
    extra_codes = ""
    if package_item.package_status == "overlap_partial_review":
        extra_codes = "package_overlap_review"
    elif package_item.package_status == "mixed_cycle_review":
        extra_codes = "package_cycle_mixed"
    return _merge_review_values(item.review_codes, extra_codes)


def _planned_review_reason(item: _PlannedItem, package_item: PlannedPackageItem) -> str:
    extra_reason = ""
    if package_item.package_status == "overlap_partial_review":
        extra_reason = (
            f"Package overlap with {package_item.package_related_bundles}; {package_item.package_decision_reason}"
        )
    elif package_item.package_status == "mixed_cycle_review":
        extra_reason = package_item.package_decision_reason
    return _merge_review_values(item.review_reason, extra_reason)


def _merge_review_required(*values: str) -> str:
    return "yes" if any(value == "yes" for value in values) else "no"


def _merge_review_values(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        for part in value.split(";"):
            stripped = part.strip()
            if stripped and stripped not in parts:
                parts.append(stripped)
    return "; ".join(parts) if any(" " in part for part in parts) else ";".join(parts)


def _override_target_source(target_path: Path, previous_source: str, new_source: str) -> Path:
    if previous_source == new_source:
        return target_path
    parts = list(target_path.parts)
    for index, part in enumerate(parts):
        if part == previous_source:
            parts[index] = new_source
            break
    return Path(*parts)


def _write_capture_manifests(
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    planned_items: list[_PlannedItem],
) -> None:
    capture_rows: dict[Path, list[dict[str, str]]] = {}
    for item in planned_items:
        if item.category != "source_raw" or item.placement_status.startswith("package_") or item.action == "skip":
            continue
        capture_root = workspace_root / "evidence" / "raw" / "source" / item.source_folder / item.capture_id
        capture_rows.setdefault(capture_root, []).append(
            {
                "filename": str(item.target_path.relative_to(capture_root)),
                "sha256": item.sha256,
                "size_bytes": (
                    str(item.target_path.stat().st_size)
                    if item.target_path.exists()
                    else str(item.source_path.stat().st_size)
                ),
                "source_paths": str(item.source_path),
            }
        )
    for capture_root, rows in capture_rows.items():
        artifacts.write_rows(
            capture_root / "manifest.csv",
            ("filename", "sha256", "size_bytes", "source_paths"),
            rows,
        )
