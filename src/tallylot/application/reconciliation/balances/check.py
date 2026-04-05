"""Balance reconciliation checks over one or more source roots."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from tallylot.application.reconciliation.balances.contracts import (
    BalanceCheckRequest,
    BalanceCheckResponse,
)
from tallylot.application.reconciliation.balances.cross_source import (
    build_cross_source_corroboration,
)
from tallylot.application.reconciliation.balances.records import (
    BALANCE_ASSERTION_HEADER,
    BALANCE_CHECK_SUMMARY_HEADER,
    CROSS_SOURCE_ASSERTION_HEADER,
    BalanceCheckSummaryRecord,
)
from tallylot.application.reconciliation.balances.sources import (
    BalanceSourceDir,
    discover_balance_source_dirs,
    select_balance_source_dirs,
    source_dir_input,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
)
from tallylot.domain.reconciliation import assert_balance_snapshots
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort


class BalanceCheckWorkflow:
    def __init__(
        self,
        evidence: EvidenceRepositoryPort,
        artifacts: ArtifactStorePort,
    ) -> None:
        self._evidence = evidence
        self._artifacts = artifacts

    def execute(self, request: BalanceCheckRequest) -> BalanceCheckResponse:
        input_root = path_from_ref(request.input_root_ref)
        output_root = path_from_ref(request.output_root_ref)
        _ensure_output_root_is_safe(input_root, output_root)
        single_source = source_dir_input(input_root)
        source_dirs = select_balance_source_dirs(
            discover_balance_source_dirs(input_root),
            request.sources,
        )
        records = tuple(
            self._check_source_dir(
                source_dir,
                output_root=source_dir.output_root(
                    output_root, single_source=single_source
                ),
            )
            for source_dir in source_dirs
            if _is_runnable_source_dir(source_dir)
        )
        ensure_directory(output_root)
        check_summary_output_path = output_root / "balance_check_summary.csv"
        self._artifacts.write_rows(
            check_summary_output_path,
            BALANCE_CHECK_SUMMARY_HEADER,
            (record.to_row() for record in records),
        )
        cross_source_result = build_cross_source_corroboration(
            source_dirs,
            evidence=self._evidence,
            artifacts=self._artifacts,
        )
        self._artifacts.write_rows(
            output_root / "cross_source_assertions.csv",
            CROSS_SOURCE_ASSERTION_HEADER,
            (record.to_row() for record in cross_source_result.assertions),
        )
        self._evidence.write_issue_records(
            output_root / "cross_source_issues.csv",
            cross_source_result.issues,
        )
        self._artifacts.write_json(
            output_root / "cross_source_summary.json",
            cross_source_result.summary_payload(),
        )
        status_counts = Counter(record.check_status for record in records)
        return BalanceCheckResponse(
            output_root_ref=request.output_root_ref,
            check_summary_output_ref=to_resource_ref(check_summary_output_path),
            source_count=len(records),
            clean_source_count=status_counts.get("clean", 0),
            issue_source_count=status_counts.get("issues", 0),
            failed_source_count=status_counts.get("failed", 0),
            no_assertion_source_count=status_counts.get("no_assertions", 0),
        )

    def _check_source_dir(
        self,
        source_dir: BalanceSourceDir,
        *,
        output_root: Path,
    ) -> BalanceCheckSummaryRecord:
        assertion_output_path = output_root / "balance_assertions.csv"
        issue_output_path = output_root / "reconciliation_issues.csv"
        summary_output_path = output_root / "balance_assertion_summary.json"
        _ensure_output_paths_are_distinct(
            assertion_output_path,
            issue_output_path,
            summary_output_path,
        )
        _ensure_source_output_paths_are_safe(source_dir, output_root)
        ensure_directory(output_root)
        try:
            snapshots = self._evidence.read_balance_snapshots(source_dir.snapshot_path)
            evidence = self._evidence.read_balance_evidence(source_dir.evidence_path)
            result = assert_balance_snapshots(snapshots, evidence)
            self._artifacts.write_rows(
                assertion_output_path,
                BALANCE_ASSERTION_HEADER,
                (assertion.to_row() for assertion in result.assertions),
            )
            self._evidence.write_issue_records(issue_output_path, result.issues)
            self._artifacts.write_json(
                summary_output_path,
                {
                    "assertion_count": len(result.assertions),
                    "issue_count": len(result.issues),
                },
            )
        except ValueError as exc:
            return BalanceCheckSummaryRecord(
                source=source_dir.name,
                check_status="failed",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                assertion_status_counts=(),
                issue_kind_counts=(),
                error_message=str(exc),
            )
        assertion_rows = self._artifacts.read_rows(assertion_output_path)
        issue_rows = self._artifacts.read_rows(issue_output_path)
        all_dates = tuple(
            date_value
            for row in assertion_rows
            for date_value in _assertion_row_dates(row)
        )
        matched_dates = tuple(
            date_value
            for row in assertion_rows
            if row["status"] == "matched"
            for date_value in _assertion_row_dates(row)
        )
        check_status = _check_status(
            assertion_count=len(assertion_rows),
            issue_count=len(issue_rows),
        )
        return BalanceCheckSummaryRecord(
            source=source_dir.name,
            check_status=check_status,
            assertion_count=len(assertion_rows),
            issue_count=len(issue_rows),
            min_assertion_date=min(all_dates) if all_dates else "",
            max_assertion_date=max(all_dates) if all_dates else "",
            latest_clean_checked_date=(
                max(matched_dates) if check_status == "clean" and matched_dates else ""
            ),
            assertion_status_counts=tuple(
                sorted(Counter(row["status"] for row in assertion_rows).items())
            ),
            issue_kind_counts=tuple(
                sorted(Counter(row["kind"] for row in issue_rows).items())
            ),
        )


def _check_status(*, assertion_count: int, issue_count: int) -> str:
    if assertion_count == 0:
        return "no_assertions"
    if issue_count == 0:
        return "clean"
    return "issues"


def _is_runnable_source_dir(source_dir: BalanceSourceDir) -> bool:
    return source_dir.snapshot_path.is_file() and source_dir.evidence_path.is_file()


def _assertion_row_dates(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        value[:10]
        for value in (
            row.get("snapshot_as_of_at", "").strip(),
            row.get("evidence_as_of_at", "").strip(),
        )
        if value
    )


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
        ("balance snapshot input", source_dir.snapshot_path),
        ("balance evidence input", source_dir.evidence_path),
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
