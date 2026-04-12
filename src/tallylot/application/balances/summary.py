"""Summary assembly for balance reconciliation artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from tallylot.application.balances.contracts import (
    BalanceSummaryRequest,
    BalanceSummaryResponse,
)
from tallylot.application.balances.records import (
    BALANCE_RECONCILIATION_BLOCKER_HEADER,
    BalanceCheckSummaryRecord,
    BalanceInspectRecord,
    BalanceReconciliationBlockerRecord,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort


class BalanceSummaryWorkflow:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: BalanceSummaryRequest) -> BalanceSummaryResponse:
        inspect_input_path = path_from_ref(request.inspect_input_ref)
        check_summary_input_path = path_from_ref(request.check_summary_input_ref)
        summary_output_path = path_from_ref(request.summary_output_ref)
        blocker_output_path = summary_output_path.with_name(
            "balance_reconciliation_blockers.csv"
        )
        _clear_generated_balance_summary_outputs(summary_output_path)
        inspect_records = tuple(
            BalanceInspectRecord.from_row(row)
            for row in _read_rows_if_present(self._artifacts, inspect_input_path)
        )
        check_records = tuple(
            BalanceCheckSummaryRecord.from_row(row)
            for row in _read_rows_if_present(self._artifacts, check_summary_input_path)
        )
        blockers = _build_blockers(inspect_records, check_records)
        summary_payload = _summary_payload(inspect_records, check_records, blockers)
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
            source_count=len(inspect_records),
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
    inspect_records: tuple[BalanceInspectRecord, ...],
    check_records: tuple[BalanceCheckSummaryRecord, ...],
) -> tuple[BalanceReconciliationBlockerRecord, ...]:
    blockers_by_key: dict[tuple[str, str], BalanceReconciliationBlockerRecord] = {}
    for inspect_record in inspect_records:
        blocker_kind = _inspect_blocker_kind(inspect_record)
        if blocker_kind is None:
            continue
        _merge_blocker(
            blockers_by_key,
            source=inspect_record.source,
            blocker_kind=blocker_kind,
            notes=_inspect_blocker_notes(inspect_record, blocker_kind),
        )

    for check_record in check_records:
        blocker_kind = _check_blocker_kind(check_record)
        if blocker_kind is None:
            continue
        _merge_blocker(
            blockers_by_key,
            source=check_record.source,
            blocker_kind=blocker_kind,
            notes=_check_blocker_notes(check_record, blocker_kind),
        )

    return tuple(
        blockers_by_key[key]
        for key in sorted(
            blockers_by_key,
            key=lambda item: (item[0], item[1]),
        )
    )


def _merge_blocker(
    blockers_by_key: dict[tuple[str, str], BalanceReconciliationBlockerRecord],
    *,
    source: str,
    blocker_kind: str,
    notes: str = "",
) -> None:
    key = (source, blocker_kind)
    existing = blockers_by_key.get(key)
    if existing is None:
        blockers_by_key[key] = BalanceReconciliationBlockerRecord(
            source=source,
            blocker_kind=blocker_kind,
            blocker_count=1,
            notes=notes,
        )
        return
    if notes and not existing.notes:
        blockers_by_key[key] = BalanceReconciliationBlockerRecord(
            source=existing.source,
            blocker_kind=existing.blocker_kind,
            blocker_count=existing.blocker_count,
            notes=notes,
        )


def _inspect_blocker_kind(
    inspect_record: BalanceInspectRecord,
) -> str | None:
    if inspect_record.offline_ready == "missing_references":
        return "missing_references"
    if inspect_record.offline_ready == "no_balance_targets":
        return "no_balance_targets"
    if inspect_record.offline_ready == "no_balance_inputs":
        return "no_balance_inputs"
    return None


def _inspect_blocker_notes(
    inspect_record: BalanceInspectRecord,
    blocker_kind: str,
) -> str:
    del blocker_kind
    if (
        inspect_record.offline_ready == "no_balance_inputs"
        and inspect_record.unexpected_superseded_output_count > 0
    ):
        return (
            "unexpected superseded outputs present: "
            f"{inspect_record.unexpected_superseded_output_count}"
        )
    return ""


def _check_blocker_kind(
    check_record: BalanceCheckSummaryRecord,
) -> str | None:
    if check_record.check_status == "failed":
        return "failed"
    if check_record.check_status == "not_runnable":
        return "no_balance_inputs"
    if check_record.check_status == "no_balance_targets":
        return "no_balance_targets"
    if (
        check_record.check_status == "issues"
        and check_record.resolution_mode == "hydrated"
        and _count_issue_kind(
            check_record.issue_kind_counts, "unsupported_balance_provider"
        )
    ):
        return "unsupported_hydration"
    return None


def _check_blocker_notes(
    check_record: BalanceCheckSummaryRecord,
    blocker_kind: str,
) -> str:
    if blocker_kind == "failed":
        return check_record.error_message
    return ""


def _summary_payload(
    inspect_records: tuple[BalanceInspectRecord, ...],
    check_records: tuple[BalanceCheckSummaryRecord, ...],
    blockers: tuple[BalanceReconciliationBlockerRecord, ...],
) -> dict[str, JsonValue]:
    check_by_source = {record.source: record for record in check_records}
    inspect_status_counts = Counter(record.offline_ready for record in inspect_records)
    check_status_counts = Counter(record.check_status for record in check_records)
    blocker_kind_counts = Counter(blocker.blocker_kind for blocker in blockers)
    clean_check_records = tuple(
        record for record in check_records if record.check_status == "clean"
    )
    clean_dates = tuple(
        record.latest_clean_checked_date
        for record in clean_check_records
        if record.latest_clean_checked_date
    )
    resolved_reference_dates = tuple(
        record.latest_resolved_reference_checked_date
        for record in clean_check_records
        if record.latest_resolved_reference_checked_date
    )
    observed_dates = tuple(
        record.max_assertion_date
        for record in check_records
        if record.max_assertion_date
    )
    operational_sources = tuple(
        record.source for record in inspect_records if record.offline_ready == "ready"
    )
    all_sources_clean = (
        bool(inspect_records)
        and len(operational_sources) == len(inspect_records)
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
        bool(inspect_records)
        and len(operational_sources) == len(inspect_records)
        and all(
            (
                source in check_by_source
                and check_by_source[source].check_status == "clean"
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
        "source_count": len(inspect_records),
        "clean_source_count": check_status_counts.get("clean", 0),
        "issue_source_count": check_status_counts.get("issues", 0),
        "failed_source_count": check_status_counts.get("failed", 0),
        "latest_portfolio_clean_date": latest_portfolio_clean_date,
        "latest_portfolio_resolved_reference_date": latest_portfolio_resolved_reference_date,
        "latest_clean_source_date": max(clean_dates) if clean_dates else "",
        "latest_resolved_reference_date": max(resolved_reference_dates)
        if resolved_reference_dates
        else "",
        "latest_observed_assertion_date": max(observed_dates) if observed_dates else "",
        "inspect_status_counts": dict(sorted(inspect_status_counts.items())),
        "check_status_counts": dict(sorted(check_status_counts.items())),
        "blocker_kind_counts": dict(sorted(blocker_kind_counts.items())),
    }


def _count_issue_kind(
    issue_kind_counts: tuple[tuple[str, int], ...],
    kind: str,
) -> int:
    for issue_kind, count in issue_kind_counts:
        if issue_kind == kind:
            return count
    return 0


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
