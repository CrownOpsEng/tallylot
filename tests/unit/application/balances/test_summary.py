from __future__ import annotations

import json
from pathlib import Path

import pytest

from tallylot.application.balances import (
    BALANCE_CHECK_SUMMARY_HEADER,
    BALANCE_INSPECT_HEADER,
    BalanceSummaryRequest,
    BalanceSummaryWorkflow,
)
from tallylot.application.balances.inputs import BalanceInputMode, BalanceSnapshotOrigin
from tallylot.application.balances.records import (
    BalanceCheckSummaryRecord,
    BalanceCheckStatus,
    BalanceCrossSourceReadyStatus,
    BalanceInspectRecord,
    BalanceOfflineReadyStatus,
    BalanceResolutionMode,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def _inspect_record(
    *,
    source: str,
    input_mode: BalanceInputMode = "manual_only",
    snapshot_origin: BalanceSnapshotOrigin = "explicit_rows",
    target_count: int = 1,
    snapshot_count: int = 1,
    reference_row_count: int = 1,
    matched_reference_count: int = 1,
    missing_reference_count: int = 0,
    source_document_count: int = 0,
    network_api_count: int = 0,
    operator_assertion_count: int = 0,
    cross_source_ready: BalanceCrossSourceReadyStatus = "ready",
    offline_ready: BalanceOfflineReadyStatus = "ready",
    unexpected_superseded_output_count: int = 0,
    min_target_date: str = "2026-03-23",
    max_target_date: str = "2026-03-23",
    min_reference_date: str = "2026-03-23",
    max_reference_date: str = "2026-03-23",
) -> BalanceInspectRecord:
    return BalanceInspectRecord(
        source=source,
        input_mode=input_mode,
        snapshot_origin=snapshot_origin,
        target_count=target_count,
        snapshot_count=snapshot_count,
        reference_row_count=reference_row_count,
        matched_reference_count=matched_reference_count,
        missing_reference_count=missing_reference_count,
        source_document_count=source_document_count,
        network_api_count=network_api_count,
        operator_assertion_count=operator_assertion_count,
        cross_source_ready=cross_source_ready,
        offline_ready=offline_ready,
        unexpected_superseded_output_count=unexpected_superseded_output_count,
        min_target_date=min_target_date,
        max_target_date=max_target_date,
        min_reference_date=min_reference_date,
        max_reference_date=max_reference_date,
    )


def _check_record(
    *,
    source: str,
    resolution_mode: BalanceResolutionMode = "offline",
    check_status: BalanceCheckStatus = "clean",
    not_runnable_reason: str = "",
    assertion_count: int = 1,
    issue_count: int = 0,
    min_assertion_date: str = "2026-03-23",
    max_assertion_date: str = "2026-03-23",
    latest_clean_checked_date: str = "2026-03-23",
    latest_resolved_reference_checked_date: str = "2026-03-23",
    assertion_status_counts: tuple[tuple[str, int], ...] = (("matched", 1),),
    selected_reference_kind_counts: tuple[tuple[str, int], ...] = (
        ("source_document", 1),
    ),
    issue_kind_counts: tuple[tuple[str, int], ...] = (),
    error_message: str = "",
) -> BalanceCheckSummaryRecord:
    return BalanceCheckSummaryRecord(
        source=source,
        resolution_mode=resolution_mode,
        check_status=check_status,
        assertion_count=assertion_count,
        issue_count=issue_count,
        min_assertion_date=min_assertion_date,
        max_assertion_date=max_assertion_date,
        latest_clean_checked_date=latest_clean_checked_date,
        latest_resolved_reference_checked_date=latest_resolved_reference_checked_date,
        assertion_status_counts=assertion_status_counts,
        selected_reference_kind_counts=selected_reference_kind_counts,
        issue_kind_counts=issue_kind_counts,
        not_runnable_reason=not_runnable_reason,
        error_message=error_message,
    )


def test_balance_summary_workflow_computes_latest_dates_for_ready_sources(
    tmp_path: Path,
) -> None:
    inspect_path = tmp_path / "balance_inspect.csv"
    check_summary_path = tmp_path / "balance_check_summary.csv"
    output_path = tmp_path / "balance_reconciliation_summary.json"

    write_rows(
        inspect_path,
        BALANCE_INSPECT_HEADER,
        (
            _inspect_record(
                source="source-backed",
                source_document_count=1,
                min_target_date="2026-03-23",
                max_target_date="2026-03-23",
                min_reference_date="2026-03-23",
                max_reference_date="2026-03-23",
            ).to_row(),
            _inspect_record(
                source="operator-confirmed",
                operator_assertion_count=1,
                min_target_date="2026-03-24",
                max_target_date="2026-03-24",
                min_reference_date="2026-03-24",
                max_reference_date="2026-03-24",
            ).to_row(),
        ),
    )
    write_rows(
        check_summary_path,
        BALANCE_CHECK_SUMMARY_HEADER,
        (
            _check_record(
                source="source-backed",
                latest_clean_checked_date="2026-03-23",
                latest_resolved_reference_checked_date="2026-03-23",
                assertion_status_counts=(("matched", 1),),
                selected_reference_kind_counts=(("source_document", 1),),
            ).to_row(),
            _check_record(
                source="operator-confirmed",
                latest_clean_checked_date="2026-03-24",
                latest_resolved_reference_checked_date="2026-03-24",
                min_assertion_date="2026-03-24",
                max_assertion_date="2026-03-24",
                assertion_status_counts=(("matched", 1),),
                selected_reference_kind_counts=(("operator_assertion", 1),),
            ).to_row(),
        ),
    )

    response = BalanceSummaryWorkflow(FilesystemArtifactStore()).execute(
        BalanceSummaryRequest(
            inspect_input_ref=to_resource_ref(inspect_path),
            check_summary_input_ref=to_resource_ref(check_summary_path),
            summary_output_ref=to_resource_ref(output_path),
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert response.source_count == 2
    assert response.latest_portfolio_clean_date == "2026-03-23"
    assert response.latest_portfolio_resolved_reference_date == "2026-03-23"
    assert response.latest_clean_source_date == "2026-03-24"
    assert response.latest_resolved_reference_date == "2026-03-24"
    assert response.latest_observed_assertion_date == "2026-03-24"
    assert payload["source_count"] == 2
    assert payload["clean_source_count"] == 2
    assert payload["issue_source_count"] == 0
    assert payload["failed_source_count"] == 0
    assert payload["inspect_status_counts"] == {"ready": 2}
    assert payload["check_status_counts"] == {"clean": 2}
    assert payload["blocker_kind_counts"] == {}
    assert not (tmp_path / "balance_reconciliation_blockers.csv").exists()


@pytest.mark.parametrize(
    (
        "inspect_record",
        "check_record",
        "expected_blocker_kind",
        "expected_notes",
        "expected_portfolio_clean_date",
        "expected_portfolio_resolved_reference_date",
        "expected_blocker_counts",
    ),
    (
        (
            _inspect_record(
                source="problem-source",
                offline_ready="missing_references",
                cross_source_ready="ready",
                target_count=1,
                snapshot_count=1,
                reference_row_count=0,
                matched_reference_count=0,
                missing_reference_count=1,
                source_document_count=0,
                min_target_date="2026-03-23",
                max_target_date="2026-03-23",
                min_reference_date="",
                max_reference_date="",
            ),
            _check_record(
                source="problem-source",
                check_status="clean",
                latest_clean_checked_date="2026-03-23",
                latest_resolved_reference_checked_date="2026-03-23",
            ),
            "missing_references",
            "",
            "",
            "",
            {"missing_references": 1},
        ),
        (
            _inspect_record(
                source="problem-source",
                offline_ready="no_balance_targets",
                cross_source_ready="not_comparable",
                target_count=0,
                snapshot_count=1,
                reference_row_count=0,
                matched_reference_count=0,
                missing_reference_count=0,
                min_target_date="",
                max_target_date="",
                min_reference_date="",
                max_reference_date="",
            ),
            _check_record(
                source="problem-source",
                check_status="no_balance_targets",
                resolution_mode="offline",
                not_runnable_reason="",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                latest_resolved_reference_checked_date="",
                assertion_status_counts=(),
                selected_reference_kind_counts=(),
                issue_kind_counts=(),
            ),
            "no_balance_targets",
            "",
            "",
            "",
            {"no_balance_targets": 1},
        ),
        (
            _inspect_record(
                source="problem-source",
                offline_ready="no_balance_inputs",
                cross_source_ready="not_applicable",
                target_count=0,
                snapshot_count=0,
                reference_row_count=0,
                matched_reference_count=0,
                missing_reference_count=0,
                unexpected_superseded_output_count=2,
            ),
            _check_record(
                source="problem-source",
                check_status="not_runnable",
                not_runnable_reason="no_balance_inputs",
                resolution_mode="offline",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                latest_resolved_reference_checked_date="",
                assertion_status_counts=(),
                selected_reference_kind_counts=(),
                issue_kind_counts=(),
            ),
            "no_balance_inputs",
            "unexpected superseded outputs present: 2",
            "",
            "",
            {"no_balance_inputs": 1},
        ),
        (
            _inspect_record(
                source="problem-source",
                offline_ready="ready",
                cross_source_ready="ready",
                source_document_count=1,
                min_target_date="2026-03-23",
                max_target_date="2026-03-23",
                min_reference_date="2026-03-23",
                max_reference_date="2026-03-23",
            ),
            _check_record(
                source="problem-source",
                check_status="issues",
                resolution_mode="hydrated",
                issue_kind_counts=(("unsupported_balance_provider", 1),),
                latest_resolved_reference_checked_date="2026-03-23",
            ),
            "unsupported_hydration",
            "",
            "",
            "",
            {"unsupported_hydration": 1},
        ),
        (
            _inspect_record(
                source="problem-source",
                offline_ready="ready",
                cross_source_ready="ready",
                source_document_count=1,
                min_target_date="2026-03-23",
                max_target_date="2026-03-23",
                min_reference_date="2026-03-23",
                max_reference_date="2026-03-23",
            ),
            _check_record(
                source="problem-source",
                check_status="failed",
                error_message="unsupported balance reference_policy: bogus",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                latest_resolved_reference_checked_date="",
                assertion_status_counts=(),
                selected_reference_kind_counts=(),
                issue_kind_counts=(),
            ),
            "failed",
            "unsupported balance reference_policy: bogus",
            "",
            "",
            {"failed": 1},
        ),
    ),
)
def test_balance_summary_workflow_emits_exact_blocker_kinds(
    tmp_path: Path,
    inspect_record: BalanceInspectRecord,
    check_record: BalanceCheckSummaryRecord,
    expected_blocker_kind: str,
    expected_notes: str,
    expected_portfolio_clean_date: str,
    expected_portfolio_resolved_reference_date: str,
    expected_blocker_counts: dict[str, int],
) -> None:
    inspect_path = tmp_path / "balance_inspect.csv"
    check_summary_path = tmp_path / "balance_check_summary.csv"
    output_path = tmp_path / "balance_reconciliation_summary.json"

    write_rows(
        inspect_path,
        BALANCE_INSPECT_HEADER,
        (inspect_record.to_row(),),
    )
    write_rows(
        check_summary_path,
        BALANCE_CHECK_SUMMARY_HEADER,
        (check_record.to_row(),),
    )

    response = BalanceSummaryWorkflow(FilesystemArtifactStore()).execute(
        BalanceSummaryRequest(
            inspect_input_ref=to_resource_ref(inspect_path),
            check_summary_input_ref=to_resource_ref(check_summary_path),
            summary_output_ref=to_resource_ref(output_path),
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    blocker_rows = FilesystemArtifactStore().read_rows(
        tmp_path / "balance_reconciliation_blockers.csv"
    )

    assert response.source_count == 1
    assert response.latest_portfolio_clean_date == expected_portfolio_clean_date
    assert (
        response.latest_portfolio_resolved_reference_date
        == expected_portfolio_resolved_reference_date
    )
    assert payload["source_count"] == 1
    assert payload["blocker_kind_counts"] == expected_blocker_counts
    assert blocker_rows[0]["blocker_kind"] == expected_blocker_kind
    assert blocker_rows[0]["notes"] == expected_notes
