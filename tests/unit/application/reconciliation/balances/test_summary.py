from __future__ import annotations

import json
from pathlib import Path

from tallylot.application.reconciliation import (
    BALANCE_CHECK_SUMMARY_HEADER,
    BALANCE_COVERAGE_HEADER,
    BalanceSummaryRequest,
    BalanceSummaryWorkflow,
)
from tallylot.application.reconciliation.balances.records import (
    BalanceCheckSummaryRecord,
    BalanceCoverageRecord,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_balance_summary_workflow_keeps_no_assertion_sources_out_of_clean_dates(
    tmp_path: Path,
) -> None:
    coverage_path = tmp_path / "balance_coverage.csv"
    check_summary_path = tmp_path / "balance_check_summary.csv"
    output_path = tmp_path / "balance_reconciliation_summary.json"

    write_rows(
        coverage_path,
        BALANCE_COVERAGE_HEADER,
        (
            BalanceCoverageRecord(
                source="clean-source",
                coverage_status="comparable",
                snapshot_count=1,
                evidence_count=1,
                min_snapshot_date="2026-03-23",
                max_snapshot_date="2026-03-23",
                min_evidence_date="2026-03-23",
                max_evidence_date="2026-03-23",
            ).to_row(),
            BalanceCoverageRecord(
                source="empty-source",
                coverage_status="empty_source",
                snapshot_count=0,
                evidence_count=0,
            ).to_row(),
        ),
    )
    write_rows(
        check_summary_path,
        BALANCE_CHECK_SUMMARY_HEADER,
        (
            BalanceCheckSummaryRecord(
                source="clean-source",
                check_status="clean",
                assertion_count=1,
                issue_count=0,
                min_assertion_date="2026-03-23",
                max_assertion_date="2026-03-23",
                latest_clean_checked_date="2026-03-23",
                assertion_status_counts=(("matched", 1),),
                issue_kind_counts=(),
            ).to_row(),
            BalanceCheckSummaryRecord(
                source="empty-source",
                check_status="no_assertions",
                assertion_count=0,
                issue_count=0,
                min_assertion_date="",
                max_assertion_date="",
                latest_clean_checked_date="",
                assertion_status_counts=(),
                issue_kind_counts=(),
            ).to_row(),
        ),
    )

    response = BalanceSummaryWorkflow(FilesystemArtifactStore()).execute(
        BalanceSummaryRequest(
            coverage_input_ref=to_resource_ref(coverage_path),
            check_summary_input_ref=to_resource_ref(check_summary_path),
            summary_output_ref=to_resource_ref(output_path),
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    blocker_rows = FilesystemArtifactStore().read_rows(
        tmp_path / "balance_reconciliation_blockers.csv"
    )

    assert response.latest_portfolio_clean_date == ""
    assert response.latest_clean_source_date == "2026-03-23"
    assert response.latest_observed_assertion_date == "2026-03-23"
    assert payload["blocker_kind_counts"]["empty_source"] == 1
    assert payload["blocker_kind_counts"]["no_assertions"] == 1
    assert blocker_rows[0]["blocker_kind"] == "empty_source"
    assert blocker_rows[1]["blocker_kind"] == "no_assertions"
