"""Balance reconciliation checks over one or more source roots."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import assert_never

from tallylot.application.balances.filenames import (
    BALANCE_ASSERTION_FILENAME,
    BALANCE_CHECK_SUMMARY_FILENAME,
    BALANCE_RECONCILIATION_SUMMARY_FILENAME,
)
from tallylot.application.balances.contracts import (
    BalanceCheckRequest,
    BalanceCheckResponse,
)
from tallylot.application.balances.corroboration import (
    build_cross_source_corroboration,
)
from tallylot.application.balances.inputs import (
    BalanceSourceDir,
    BalanceSourceInputs,
    build_balance_source_inputs,
    discover_balance_source_dirs,
    select_balance_source_dirs,
    source_dir_input,
)
from tallylot.application.balances.references import BalanceReferenceResolver
from tallylot.application.balances.snapshots import derive_balance_snapshots
from tallylot.application.balances.records import (
    BALANCE_ASSERTION_HEADER,
    BALANCE_CHECK_SUMMARY_HEADER,
    CROSS_SOURCE_ASSERTION_HEADER,
    BalanceCheckStatus,
    BalanceCheckSummaryRecord,
    BalanceResolutionMode,
)
from tallylot.application.balances.targets import (
    parse_target_time_values,
    targets_for_as_of_values,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
)
from tallylot.domain.balances import (
    BalanceReference,
    BalanceSnapshot,
    BalanceTarget,
    assert_balance_targets,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.balance_providers import BalanceProviderRegistryPort
from tallylot.ports.evidence import EvidenceRepositoryPort, ISSUE_HEADER
from tallylot.ports.facts import FactRepositoryPort


@dataclass(frozen=True)
class _ReferenceCacheUpdate:
    existing_references: tuple[BalanceReference, ...]
    resolved_references: tuple[BalanceReference, ...]
    reference_issues: tuple[IssueRecord, ...]


@dataclass(frozen=True)
class _CheckPlan:
    resolution_mode: BalanceResolutionMode
    targets: tuple[BalanceTarget, ...]
    snapshots: tuple[BalanceSnapshot, ...]
    snapshot_issues: tuple[IssueRecord, ...]
    status: BalanceCheckStatus = "clean"
    not_runnable_reason: str = ""


class BalanceCheckWorkflow:
    def __init__(
        self,
        *,
        facts: FactRepositoryPort,
        evidence: EvidenceRepositoryPort,
        artifacts: ArtifactStorePort,
        providers: BalanceProviderRegistryPort | None = None,
    ) -> None:
        self._facts = facts
        self._evidence = evidence
        self._artifacts = artifacts
        self._resolver = BalanceReferenceResolver(
            evidence=evidence,
            providers=providers,
        )

    def execute(self, request: BalanceCheckRequest) -> BalanceCheckResponse:
        input_root = path_from_ref(request.input_root_ref)
        output_root = path_from_ref(request.output_root_ref)
        _ensure_output_root_is_safe(input_root, output_root)
        _clear_generated_balance_check_outputs(output_root)
        single_source = source_dir_input(input_root)
        source_dirs = select_balance_source_dirs(
            discover_balance_source_dirs(input_root),
            request.sources,
        )
        source_inputs = tuple(
            build_balance_source_inputs(
                source_dir,
                facts=self._facts,
                evidence=self._evidence,
                artifacts=self._artifacts,
            )
            for source_dir in source_dirs
        )
        records: list[BalanceCheckSummaryRecord] = []
        for source_dir, source_input in zip(source_dirs, source_inputs):
            source_output_root = source_dir.output_root(
                output_root,
                single_source=single_source,
            )
            _clear_generated_balance_check_outputs(source_output_root)
            _clear_generated_balance_reference_issue_output(
                source_dir.reference_issue_path
            )
            records.append(
                self._check_source_input(
                    source_dir,
                    source_input,
                    output_root=source_output_root,
                    request=request,
                )
            )
        ensure_directory(output_root)
        check_summary_output_path = output_root / BALANCE_CHECK_SUMMARY_FILENAME
        if records:
            self._artifacts.write_rows(
                check_summary_output_path,
                BALANCE_CHECK_SUMMARY_HEADER,
                (record.to_row() for record in records),
            )
        cross_source_result = build_cross_source_corroboration(source_inputs)
        if cross_source_result.assertions:
            self._artifacts.write_rows(
                output_root / "cross_source_assertions.csv",
                CROSS_SOURCE_ASSERTION_HEADER,
                (record.to_row() for record in cross_source_result.assertions),
            )
        if cross_source_result.issues:
            self._evidence.write_issue_records(
                output_root / "cross_source_issues.csv",
                cross_source_result.issues,
            )
        self._artifacts.write_json(
            output_root / "cross_source_summary.json",
            cross_source_result.summary_payload(),
        )
        status_counts = Counter(record.check_status for record in records)
        resolution_mode: BalanceResolutionMode = (
            "hydrated" if request.hydrate_missing_references else "offline"
        )
        return BalanceCheckResponse(
            output_root_ref=request.output_root_ref,
            check_summary_output_ref=to_resource_ref(check_summary_output_path),
            source_count=len(records),
            clean_source_count=status_counts.get("clean", 0),
            issue_source_count=status_counts.get("issues", 0),
            failed_source_count=status_counts.get("failed", 0),
            no_balance_target_source_count=status_counts.get("no_balance_targets", 0),
            not_runnable_source_count=status_counts.get("not_runnable", 0),
            resolution_mode=resolution_mode,
        )

    def _check_source_input(
        self,
        source_dir: BalanceSourceDir,
        source_input: BalanceSourceInputs,
        *,
        output_root: Path,
        request: BalanceCheckRequest,
    ) -> BalanceCheckSummaryRecord:
        _clear_generated_balance_check_outputs(output_root)
        assertion_output_path = output_root / BALANCE_ASSERTION_FILENAME
        issue_output_path = output_root / "reconciliation_issues.csv"
        summary_output_path = output_root / BALANCE_RECONCILIATION_SUMMARY_FILENAME
        _ensure_output_paths_are_distinct(
            assertion_output_path,
            issue_output_path,
            summary_output_path,
        )
        _ensure_source_output_paths_are_safe(source_dir, output_root)
        ensure_directory(output_root)
        resolution_mode: BalanceResolutionMode = (
            "hydrated" if request.hydrate_missing_references else "offline"
        )
        try:
            plan = _build_check_plan(
                source_dir=source_dir,
                source_input=source_input,
                request=request,
                facts=self._facts,
                resolution_mode=resolution_mode,
            )
        except ValueError as exc:
            return BalanceCheckSummaryRecord(
                source=source_dir.name,
                resolution_mode=resolution_mode,
                check_status="failed",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                latest_resolved_reference_checked_date="",
                assertion_status_counts=(),
                selected_reference_kind_counts=(),
                issue_kind_counts=(),
                not_runnable_reason="",
                error_message=str(exc),
            )
        if plan.status in {"not_runnable", "no_balance_targets"}:
            self._artifacts.write_json(
                summary_output_path,
                {
                    "assertion_count": 0,
                    "issue_count": 0,
                    "reference_kind_counts": {},
                },
            )
            return BalanceCheckSummaryRecord(
                source=source_dir.name,
                resolution_mode=resolution_mode,
                check_status=plan.status,
                not_runnable_reason=plan.not_runnable_reason,
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                latest_resolved_reference_checked_date="",
                assertion_status_counts=(),
                selected_reference_kind_counts=(),
                issue_kind_counts=(),
            )

        existing_references = source_input.references
        resolved_references, reference_issues = self._resolver.resolve(
            existing_references=existing_references,
            targets=plan.targets,
            hydrate_missing=request.hydrate_missing_references,
        )
        _persist_reference_cache(
            source_dir=source_dir,
            artifacts=self._artifacts,
            evidence=self._evidence,
            update=_ReferenceCacheUpdate(
                existing_references=existing_references,
                resolved_references=resolved_references,
                reference_issues=reference_issues,
            ),
        )
        result = assert_balance_targets(plan.snapshots, resolved_references)
        all_issues = (*plan.snapshot_issues, *reference_issues, *result.issues)
        if result.assertions:
            self._artifacts.write_rows(
                assertion_output_path,
                BALANCE_ASSERTION_HEADER,
                (assertion.to_row() for assertion in result.assertions),
            )
        if all_issues:
            self._evidence.write_issue_records(issue_output_path, all_issues)
        self._artifacts.write_json(
            summary_output_path,
            {
                "assertion_count": len(result.assertions),
                "issue_count": len(all_issues),
                "reference_kind_counts": dict(
                    sorted(
                        Counter(
                            assertion.selected_reference_kind.value
                            for assertion in result.assertions
                            if assertion.selected_reference_kind is not None
                        ).items()
                    )
                ),
            },
        )
        assertion_rows = _read_rows_if_present(self._artifacts, assertion_output_path)
        issue_rows = _read_rows_if_present(self._artifacts, issue_output_path)
        all_dates = tuple(
            date_value
            for row in assertion_rows
            for date_value in _assertion_row_dates(row)
        )
        matched_dates = tuple(
            row["target_at"][:10]
            for row in assertion_rows
            if row["status"] == "matched" and row.get("target_at", "").strip()
        )
        check_status = _check_status(issue_count=len(issue_rows))
        selected_reference_kind_counts = tuple(
            sorted(
                Counter(
                    row["selected_reference_kind"]
                    for row in assertion_rows
                    if row.get("selected_reference_kind", "").strip()
                ).items()
            )
        )
        return BalanceCheckSummaryRecord(
            source=source_dir.name,
            resolution_mode=resolution_mode,
            check_status=check_status,
            not_runnable_reason="",
            assertion_count=len(assertion_rows),
            issue_count=len(issue_rows),
            min_assertion_date=min(all_dates) if all_dates else "",
            max_assertion_date=max(all_dates) if all_dates else "",
            latest_clean_checked_date=(
                max(matched_dates) if check_status == "clean" and matched_dates else ""
            ),
            latest_resolved_reference_checked_date=(
                max(matched_dates) if matched_dates else ""
            ),
            assertion_status_counts=tuple(
                sorted(Counter(row["status"] for row in assertion_rows).items())
            ),
            selected_reference_kind_counts=selected_reference_kind_counts,
            issue_kind_counts=tuple(
                sorted(Counter(row["kind"] for row in issue_rows).items())
            ),
        )


def _check_status(*, issue_count: int) -> BalanceCheckStatus:
    return "clean" if issue_count == 0 else "issues"


def _assertion_row_dates(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        value[:10]
        for value in (
            row.get("target_at", "").strip(),
            row.get("observed_at", "").strip(),
        )
        if value
    )


def _normalize_reference_policy(reference_policy: str) -> str:
    normalized = reference_policy.strip().lower()
    if normalized != "default":
        raise ValueError(f"unsupported balance reference_policy: {reference_policy}")
    return normalized


def _build_check_plan(
    *,
    source_dir: BalanceSourceDir,
    source_input: BalanceSourceInputs,
    request: BalanceCheckRequest,
    facts: FactRepositoryPort,
    resolution_mode: BalanceResolutionMode,
) -> _CheckPlan:
    parsed_times = parse_target_time_values(request.as_of_values)
    _normalize_reference_policy(request.reference_policy)
    if source_input.input_mode == "empty":
        return _CheckPlan(
            resolution_mode=resolution_mode,
            targets=(),
            snapshots=(),
            snapshot_issues=(),
            status="not_runnable",
            not_runnable_reason="no_balance_inputs",
        )

    if not parsed_times:
        return _CheckPlan(
            resolution_mode=resolution_mode,
            targets=source_input.targets,
            snapshots=source_input.snapshots,
            snapshot_issues=(),
        )

    if source_input.input_mode == "fact_backed":
        fact_rows = facts.read_facts(source_dir.facts_path)
        targets = targets_for_as_of_values(fact_rows, parsed_times)
        if not targets:
            return _CheckPlan(
                resolution_mode=resolution_mode,
                targets=(),
                snapshots=(),
                snapshot_issues=(),
                status="no_balance_targets",
            )
        snapshots, snapshot_issues = derive_balance_snapshots(fact_rows, targets)
        return _CheckPlan(
            resolution_mode=resolution_mode,
            targets=targets,
            snapshots=snapshots,
            snapshot_issues=snapshot_issues,
        )

    if source_input.input_mode == "manual_only":
        targets = _select_targets_for_requested_times(
            source_input.targets, parsed_times
        )
        if not targets:
            return _CheckPlan(
                resolution_mode=resolution_mode,
                targets=(),
                snapshots=(),
                snapshot_issues=(),
                status="no_balance_targets",
            )
        return _CheckPlan(
            resolution_mode=resolution_mode,
            targets=targets,
            snapshots=tuple(
                snapshot
                for snapshot in source_input.snapshots
                if snapshot.target in targets
            ),
            snapshot_issues=(),
        )

    assert_never(source_input.input_mode)


def _select_targets_for_requested_times(
    targets: tuple[BalanceTarget, ...],
    requested_times: tuple[tuple[datetime, TemporalPrecision], ...],
) -> tuple[BalanceTarget, ...]:
    selected: list[BalanceTarget] = []
    for target in targets:
        if any(
            target.target_at == target_at and target.target_precision == precision
            for target_at, precision in requested_times
        ):
            selected.append(target)
    return tuple(selected)


def _persist_reference_cache(
    *,
    source_dir: BalanceSourceDir,
    artifacts: ArtifactStorePort,
    evidence: EvidenceRepositoryPort,
    update: _ReferenceCacheUpdate,
) -> None:
    merged_references = {
        (
            reference.target,
            reference.reference_kind.value,
            reference.observed_at,
            reference.observed_precision.value,
            reference.support_ref,
        ): reference
        for reference in (*update.existing_references, *update.resolved_references)
    }
    evidence.write_balance_references(
        source_dir.reference_path,
        tuple(
            merged_references[key]
            for key in sorted(
                merged_references,
                key=lambda item: (
                    str(item[0].source),
                    str(item[0].location_id),
                    str(item[0].instrument_id),
                    item[0].balance_kind,
                    item[0].target_at,
                    item[1],
                    item[2],
                ),
            )
        ),
    )
    if update.reference_issues:
        artifacts.write_rows(
            source_dir.reference_issue_path,
            ISSUE_HEADER,
            tuple(issue.to_row() for issue in update.reference_issues),
        )
    else:
        _clear_generated_balance_reference_issue_output(source_dir.reference_issue_path)


def _ensure_output_root_is_safe(input_root: Path, output_root: Path) -> None:
    ensure_output_not_within_input_tree(
        input_root,
        output_root,
        input_label="balance input root",
        output_label="balance check output root",
    )


def _ensure_source_output_paths_are_safe(
    source_dir: BalanceSourceDir, output_root: Path
) -> None:
    for input_label, input_path in (
        ("balance facts input", source_dir.facts_path),
        ("balance snapshot input", source_dir.snapshot_path),
        ("balance reference input", source_dir.reference_path),
    ):
        ensure_output_not_within_input_tree(
            input_path,
            output_root,
            input_label=input_label,
            output_label="balance check output root",
        )


def _ensure_output_paths_are_distinct(*paths: Path) -> None:
    seen_paths: set[Path] = set()
    for path in paths:
        if path in seen_paths:
            raise ValueError(f"balance check outputs must be distinct: {path}")
        seen_paths.add(path)


def _read_rows_if_present(
    artifacts: ArtifactStorePort,
    path: Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    return artifacts.read_rows(path)


_GENERATED_OUTPUT_FILENAMES = (
    BALANCE_ASSERTION_FILENAME,
    BALANCE_CHECK_SUMMARY_FILENAME,
    BALANCE_RECONCILIATION_SUMMARY_FILENAME,
    "cross_source_assertions.csv",
    "cross_source_issues.csv",
    "cross_source_summary.json",
    "reconciliation_issues.csv",
)


def _clear_generated_balance_check_outputs(output_root: Path) -> None:
    for filename in _GENERATED_OUTPUT_FILENAMES:
        path = output_root / filename
        if path.is_file() or path.is_symlink():
            path.unlink()


def _clear_generated_balance_reference_issue_output(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink()
