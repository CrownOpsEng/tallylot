"""Submit validated manual balance packages into balance outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.checkpoints.contracts import (
    SubmitBalancesRequest,
    SubmitBalancesResponse,
)
from tallylot.application.balances.merge import (
    merge_balance_references,
    merge_balance_snapshots,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort

from .materialize import materialize_balance_submission
from .schema import (
    BALANCE_REFERENCES_FILENAME,
    BALANCE_SNAPSHOTS_FILENAME,
    ISSUES_FILENAME,
    ISSUE_HEADER,
    LOCATION_INVENTORY_FILENAME,
    SUMMARY_FILENAME,
)
from .validation import validate_balance_submission


@dataclass(frozen=True)
class _SubmissionStatus:
    balance_snapshot_row_count: int
    balance_reference_row_count: int
    location_inventory_row_count: int
    issue_count: int
    blocked: bool
    wrote_balance_snapshots: bool
    wrote_balance_references: bool
    wrote_location_inventory: bool
    ready_for_balance_check: bool
    notes: tuple[str, ...]


class SubmitBalancesUseCase:
    def __init__(
        self,
        evidence: EvidenceRepositoryPort,
        artifacts: ArtifactStorePort,
    ) -> None:
        self._evidence = evidence
        self._artifacts = artifacts

    def execute(self, request: SubmitBalancesRequest) -> SubmitBalancesResponse:
        submission_root = path_from_ref(request.submission_root_ref)
        output_root = path_from_ref(request.output_root_ref)
        ensure_output_not_within_input_tree(
            submission_root,
            output_root,
            input_label="balance submission root",
            output_label="balance submission output root",
        )
        ensure_directory(output_root)
        _clear_generated_balance_outputs(output_root)
        if not submission_root.is_dir():
            status = _SubmissionStatus(
                balance_snapshot_row_count=0,
                balance_reference_row_count=0,
                location_inventory_row_count=0,
                issue_count=1,
                blocked=True,
                wrote_balance_snapshots=False,
                wrote_balance_references=False,
                wrote_location_inventory=False,
                ready_for_balance_check=False,
                notes=("Submission root is missing.",),
            )
            issues = [
                {
                    "file_name": "",
                    "row_number": "",
                    "column_name": "",
                    "issue_kind": "missing_submission_root",
                    "message": f"Submission root does not exist: {submission_root}",
                }
            ]
            self._write_status_artifacts(
                output_root=output_root,
                issues=issues,
                summary_payload=self._summary_payload(
                    submission_root=submission_root,
                    output_root=output_root,
                    status=status,
                ),
            )
            return SubmitBalancesResponse(
                submission_root_ref=request.submission_root_ref,
                output_root_ref=request.output_root_ref,
                balance_snapshot_row_count=status.balance_snapshot_row_count,
                balance_reference_row_count=status.balance_reference_row_count,
                location_inventory_row_count=status.location_inventory_row_count,
                issue_count=status.issue_count,
                blocked=status.blocked,
                wrote_balance_snapshots=status.wrote_balance_snapshots,
                wrote_balance_references=status.wrote_balance_references,
                wrote_location_inventory=status.wrote_location_inventory,
                ready_for_balance_check=status.ready_for_balance_check,
            )
        validation = validate_balance_submission(
            submission_root,
            expected_source=request.source,
        )
        blocked = bool(validation.issues)
        wrote_balance_snapshots = False
        wrote_balance_references = False
        wrote_location_inventory = False
        if not blocked:
            materialized = materialize_balance_submission(
                submission_root=str(submission_root),
                balance_snapshot_rows=validation.balance_snapshot_rows,
                balance_reference_rows=validation.balance_reference_rows,
                location_inventory_rows=validation.location_inventory_rows,
            )
            self._evidence.write_balance_snapshots(
                output_root / BALANCE_SNAPSHOTS_FILENAME,
                merge_balance_snapshots(
                    existing_snapshots=self._read_existing_snapshots(output_root),
                    submitted_snapshots=materialized.balance_snapshots,
                ),
            )
            wrote_balance_snapshots = True
            self._evidence.write_balance_references(
                output_root / BALANCE_REFERENCES_FILENAME,
                merge_balance_references(
                    existing_references=self._read_existing_references(output_root),
                    submitted_references=materialized.balance_references,
                ),
            )
            wrote_balance_references = True
            if materialized.location_inventory:
                self._evidence.write_location_inventory(
                    output_root / LOCATION_INVENTORY_FILENAME,
                    materialized.location_inventory,
                )
                wrote_location_inventory = True
        status = _SubmissionStatus(
            balance_snapshot_row_count=len(validation.balance_snapshot_rows),
            balance_reference_row_count=len(validation.balance_reference_rows),
            location_inventory_row_count=len(validation.location_inventory_rows),
            issue_count=len(validation.issues),
            blocked=blocked,
            wrote_balance_snapshots=wrote_balance_snapshots,
            wrote_balance_references=wrote_balance_references,
            wrote_location_inventory=wrote_location_inventory,
            ready_for_balance_check=not blocked,
            notes=(
                ("Balance snapshots and balance references were written.",)
                if not blocked
                else (
                    "Submission is blocked. Only the summary and issues were written.",
                )
            ),
        )
        self._write_status_artifacts(
            output_root=output_root,
            issues=[issue.to_row() for issue in validation.issues],
            summary_payload=self._summary_payload(
                submission_root=submission_root,
                output_root=output_root,
                status=status,
            ),
        )
        return SubmitBalancesResponse(
            submission_root_ref=request.submission_root_ref,
            output_root_ref=request.output_root_ref,
            balance_snapshot_row_count=status.balance_snapshot_row_count,
            balance_reference_row_count=status.balance_reference_row_count,
            location_inventory_row_count=status.location_inventory_row_count,
            issue_count=status.issue_count,
            blocked=status.blocked,
            wrote_balance_snapshots=status.wrote_balance_snapshots,
            wrote_balance_references=status.wrote_balance_references,
            wrote_location_inventory=status.wrote_location_inventory,
            ready_for_balance_check=status.ready_for_balance_check,
        )

    def _write_status_artifacts(
        self,
        *,
        output_root: Path,
        issues: list[dict[str, str]],
        summary_payload: dict[str, JsonValue],
    ) -> None:
        if issues:
            self._artifacts.write_rows(
                output_root / ISSUES_FILENAME, ISSUE_HEADER, issues
            )
        self._artifacts.write_json(output_root / SUMMARY_FILENAME, summary_payload)

    def _summary_payload(
        self,
        *,
        submission_root: Path,
        output_root: Path,
        status: _SubmissionStatus,
    ) -> dict[str, JsonValue]:
        notes_payload: list[JsonValue] = list(status.notes)
        if not status.issue_count:
            notes_payload.append(
                "No submission issues were found, so "
                "balance_submission_issues.csv was not written."
            )
        return {
            "submission_root": str(submission_root),
            "output_root": str(output_root),
            "balance_snapshot_row_count": status.balance_snapshot_row_count,
            "balance_reference_row_count": status.balance_reference_row_count,
            "location_inventory_row_count": status.location_inventory_row_count,
            "issue_count": status.issue_count,
            "blocked": status.blocked,
            "wrote_balance_snapshots": status.wrote_balance_snapshots,
            "wrote_balance_references": status.wrote_balance_references,
            "wrote_location_inventory": status.wrote_location_inventory,
            "ready_for_balance_check": status.ready_for_balance_check,
            "notes": notes_payload,
        }

    def _read_existing_snapshots(
        self,
        output_root: Path,
    ) -> tuple[BalanceSnapshot, ...]:
        path = output_root / BALANCE_SNAPSHOTS_FILENAME
        if not path.is_file():
            return ()
        return self._evidence.read_balance_snapshots(path)

    def _read_existing_references(
        self,
        output_root: Path,
    ) -> tuple[BalanceReference, ...]:
        path = output_root / BALANCE_REFERENCES_FILENAME
        if not path.is_file():
            return ()
        return self._evidence.read_balance_references(path)


_GENERATED_OUTPUT_FILENAMES = (
    BALANCE_SNAPSHOTS_FILENAME,
    BALANCE_REFERENCES_FILENAME,
    LOCATION_INVENTORY_FILENAME,
    SUMMARY_FILENAME,
    ISSUES_FILENAME,
    "balance_assertions.csv",
    "balance_check_summary.csv",
    "balance_reconciliation_summary.json",
    "cross_source_assertions.csv",
    "cross_source_issues.csv",
    "cross_source_summary.json",
    "reconciliation_issues.csv",
)


def _clear_generated_balance_outputs(output_root: Path) -> None:
    for filename in _GENERATED_OUTPUT_FILENAMES:
        path = output_root / filename
        if path.is_file() or path.is_symlink():
            path.unlink()
