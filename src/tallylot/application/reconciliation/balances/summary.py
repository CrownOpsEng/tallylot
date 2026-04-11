"""Summary assembly for balance reconciliation artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from tallylot.application.reconciliation.balances.contracts import (
    BalanceSummaryRequest,
    BalanceSummaryResponse,
)
from tallylot.application.reconciliation.balances.records import (
    BALANCE_RECONCILIATION_BLOCKER_HEADER,
    BalanceCheckSummaryRecord,
    BalanceCoverageRecord,
    BalanceReconciliationBlockerRecord,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort


class BalanceSummaryWorkflow:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: BalanceSummaryRequest) -> BalanceSummaryResponse:
        coverage_input_path = path_from_ref(request.coverage_input_ref)
        check_summary_input_path = path_from_ref(request.check_summary_input_ref)
        summary_output_path = path_from_ref(request.summary_output_ref)
        blocker_output_path = summary_output_path.with_name(
            "balance_reconciliation_blockers.csv"
        )
        _clear_generated_balance_summary_outputs(summary_output_path)
        coverage_records = tuple(
            BalanceCoverageRecord.from_row(row)
            for row in _read_rows_if_present(self._artifacts, coverage_input_path)
        )
        check_records = tuple(
            BalanceCheckSummaryRecord.from_row(row)
            for row in _read_rows_if_present(self._artifacts, check_summary_input_path)
        )
        blockers = _build_blockers(coverage_records, check_records)
        summary_payload = _summary_payload(coverage_records, check_records, blockers)
        self._artifacts.write_json(summary_output_path, summary_payload)
        if blockers:
            self._artifacts.write_rows(
                blocker_output_path,
                BALANCE_RECONCILIATION_BLOCKER_HEADER,
                (blocker.to_row() for blocker in blockers),
            )
        return BalanceSummaryResponse(
            summary_output_ref=request.summary_output_ref,
            blocker_output_ref=to_resource_ref(blocker_output_path),
            source_count=len(coverage_records),
            latest_portfolio_clean_date=str(
                summary_payload["latest_portfolio_clean_date"]
            ),
            latest_portfolio_resolved_reference_date=str(
                summary_payload["latest_portfolio_resolved_reference_date"]
            ),
            latest_clean_source_date=str(summary_payload["latest_clean_source_date"]),
            latest_resolved_reference_date=str(
                summary_payload["latest_resolved_reference_date"]
            ),
            latest_observed_assertion_date=str(
                summary_payload["latest_observed_assertion_date"]
            ),
        )


def _build_blockers(
    coverage_records: tuple[BalanceCoverageRecord, ...],
    check_records: tuple[BalanceCheckSummaryRecord, ...],
) -> tuple[BalanceReconciliationBlockerRecord, ...]:
    blockers: list[BalanceReconciliationBlockerRecord] = []
    check_by_source = {record.source: record for record in check_records}
    for coverage_record in coverage_records:
        if coverage_record.coverage_status in {
            "missing_reference",
            "missing_snapshots",
            "empty_source",
        }:
            blockers.append(
                BalanceReconciliationBlockerRecord(
                    source=coverage_record.source,
                    blocker_kind=coverage_record.coverage_status,
                    blocker_count=1,
                )
            )
        check_record = check_by_source.get(coverage_record.source)
        if check_record is None:
            continue
        if check_record.check_status == "failed":
            blockers.append(
                BalanceReconciliationBlockerRecord(
                    source=check_record.source,
                    blocker_kind="failed",
                    blocker_count=1,
                    notes=check_record.error_message,
                )
            )
        if check_record.check_status == "no_assertions":
            blockers.append(
                BalanceReconciliationBlockerRecord(
                    source=check_record.source,
                    blocker_kind="no_assertions",
                    blocker_count=1,
                )
            )
        if check_record.check_status == "issues":
            blockers.extend(
                BalanceReconciliationBlockerRecord(
                    source=check_record.source,
                    blocker_kind=kind,
                    blocker_count=count,
                )
                for kind, count in check_record.issue_kind_counts
            )
    return tuple(blockers)


def _summary_payload(
    coverage_records: tuple[BalanceCoverageRecord, ...],
    check_records: tuple[BalanceCheckSummaryRecord, ...],
    blockers: tuple[BalanceReconciliationBlockerRecord, ...],
) -> dict[str, JsonValue]:
    check_by_source = {record.source: record for record in check_records}
    coverage_status_counts = Counter(
        record.coverage_status for record in coverage_records
    )
    check_status_counts = Counter(record.check_status for record in check_records)
    blocker_kind_counts = Counter(blocker.blocker_kind for blocker in blockers)
    clean_dates = tuple(
        record.latest_clean_checked_date
        for record in check_records
        if record.check_status == "clean" and record.latest_clean_checked_date
    )
    resolved_reference_dates = tuple(
        record.latest_resolved_reference_checked_date
        for record in check_records
        if record.latest_resolved_reference_checked_date
    )
    observed_dates = tuple(
        record.max_assertion_date
        for record in check_records
        if record.max_assertion_date
    )
    operational_sources = tuple(
        record.source
        for record in coverage_records
        if record.coverage_status in {"resolved_reference", "mixed_reference"}
    )
    all_sources_clean = (
        bool(coverage_records)
        and len(operational_sources) == len(coverage_records)
        and all(
            (
                source in check_by_source
                and check_by_source[source].check_status == "clean"
                and bool(check_by_source[source].latest_clean_checked_date)
            )
            for source in operational_sources
        )
    )
    all_sources_with_resolved_references = (
        bool(coverage_records)
        and len(operational_sources) == len(coverage_records)
        and all(
            (
                source in check_by_source
                and bool(check_by_source[source].latest_resolved_reference_checked_date)
            )
            for source in operational_sources
        )
    )
    latest_portfolio_clean_date = (
        min(
            check_by_source[source].latest_clean_checked_date
            for source in operational_sources
        )
        if all_sources_clean
        else ""
    )
    latest_portfolio_resolved_reference_date = (
        min(
            check_by_source[source].latest_resolved_reference_checked_date
            for source in operational_sources
        )
        if all_sources_with_resolved_references
        else ""
    )
    return {
        "source_count": len(coverage_records),
        "comparable_source_count": sum(
            coverage_status_counts.get(status, 0)
            for status in ("resolved_reference", "mixed_reference")
        ),
        "resolved_reference_source_count": coverage_status_counts.get(
            "resolved_reference", 0
        ),
        "mixed_reference_source_count": coverage_status_counts.get(
            "mixed_reference", 0
        ),
        "clean_source_count": check_status_counts.get("clean", 0),
        "issue_source_count": check_status_counts.get("issues", 0),
        "failed_source_count": check_status_counts.get("failed", 0),
        "no_assertion_source_count": check_status_counts.get("no_assertions", 0),
        "latest_portfolio_clean_date": latest_portfolio_clean_date,
        "latest_portfolio_resolved_reference_date": latest_portfolio_resolved_reference_date,
        "latest_clean_source_date": max(clean_dates) if clean_dates else "",
        "latest_resolved_reference_date": max(resolved_reference_dates)
        if resolved_reference_dates
        else "",
        "latest_observed_assertion_date": max(observed_dates) if observed_dates else "",
        "coverage_status_counts": dict(sorted(coverage_status_counts.items())),
        "check_status_counts": dict(sorted(check_status_counts.items())),
        "blocker_kind_counts": dict(sorted(blocker_kind_counts.items())),
    }


def _clear_generated_balance_summary_outputs(summary_output_path: Path) -> None:
    for path in (
        summary_output_path,
        summary_output_path.with_name("balance_reconciliation_blockers.csv"),
    ):
        if path.is_file() or path.is_symlink():
            path.unlink()


def _read_rows_if_present(
    artifacts: ArtifactStorePort,
    path: Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    return artifacts.read_rows(path)
