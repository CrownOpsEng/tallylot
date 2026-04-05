"""Submit validated manual balance packages into canonical reconciliation artifacts."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.checkpoints.contracts import (
    SubmitBalancesRequest,
    SubmitBalancesResponse,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
)
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort

from .materialize import materialize_balance_submission
from .schema import (
    BALANCE_EVIDENCE_FILENAME,
    BALANCES_FILENAME,
    ISSUES_FILENAME,
    ISSUE_HEADER,
    LOCATION_INVENTORY_FILENAME,
    SUMMARY_FILENAME,
)
from .validation import validate_balance_submission


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
        if not submission_root.is_dir():
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
                    balance_row_count=0,
                    balance_evidence_row_count=0,
                    location_inventory_row_count=0,
                    issue_count=1,
                    blocked=True,
                    wrote_location_inventory=False,
                    ready_for_balance_check=False,
                    notes=["Submission root is missing."],
                ),
            )
            return SubmitBalancesResponse(
                submission_root_ref=request.submission_root_ref,
                output_root_ref=request.output_root_ref,
                balance_row_count=0,
                balance_evidence_row_count=0,
                location_inventory_row_count=0,
                issue_count=1,
                blocked=True,
                wrote_location_inventory=False,
                ready_for_balance_check=False,
            )
        validation = validate_balance_submission(
            submission_root,
            expected_source=request.source,
        )
        blocked = bool(validation.issues)
        wrote_location_inventory = False
        if not blocked:
            materialized = materialize_balance_submission(
                submission_root=str(submission_root),
                balance_rows=validation.balance_rows,
                balance_evidence_rows=validation.balance_evidence_rows,
                location_inventory_rows=validation.location_inventory_rows,
            )
            self._evidence.write_balance_snapshots(
                output_root / BALANCES_FILENAME,
                materialized.balances,
            )
            self._evidence.write_balance_evidence(
                output_root / BALANCE_EVIDENCE_FILENAME,
                materialized.balance_evidence,
            )
            if materialized.location_inventory:
                self._evidence.write_location_inventory(
                    output_root / LOCATION_INVENTORY_FILENAME,
                    materialized.location_inventory,
                )
                wrote_location_inventory = True
            else:
                _remove_file_if_present(output_root / LOCATION_INVENTORY_FILENAME)
        else:
            _clear_canonical_outputs(output_root)
        notes = (
            ["Canonical balance artifacts were written."]
            if not blocked
            else ["Submission is blocked. Canonical balance artifacts were cleared."]
        )
        self._write_status_artifacts(
            output_root=output_root,
            issues=[issue.to_row() for issue in validation.issues],
            summary_payload=self._summary_payload(
                submission_root=submission_root,
                output_root=output_root,
                balance_row_count=len(validation.balance_rows),
                balance_evidence_row_count=len(validation.balance_evidence_rows),
                location_inventory_row_count=len(validation.location_inventory_rows),
                issue_count=len(validation.issues),
                blocked=blocked,
                wrote_location_inventory=wrote_location_inventory,
                ready_for_balance_check=not blocked,
                notes=notes,
            ),
        )
        return SubmitBalancesResponse(
            submission_root_ref=request.submission_root_ref,
            output_root_ref=request.output_root_ref,
            balance_row_count=len(validation.balance_rows),
            balance_evidence_row_count=len(validation.balance_evidence_rows),
            location_inventory_row_count=len(validation.location_inventory_rows),
            issue_count=len(validation.issues),
            blocked=blocked,
            wrote_location_inventory=wrote_location_inventory,
            ready_for_balance_check=not blocked,
        )

    def _write_status_artifacts(
        self,
        *,
        output_root: Path,
        issues: list[dict[str, str]],
        summary_payload: dict[str, JsonValue],
    ) -> None:
        self._artifacts.write_rows(output_root / ISSUES_FILENAME, ISSUE_HEADER, issues)
        self._artifacts.write_json(output_root / SUMMARY_FILENAME, summary_payload)

    def _summary_payload(
        self,
        *,
        submission_root: Path,
        output_root: Path,
        balance_row_count: int,
        balance_evidence_row_count: int,
        location_inventory_row_count: int,
        issue_count: int,
        blocked: bool,
        wrote_location_inventory: bool,
        ready_for_balance_check: bool,
        notes: list[str],
    ) -> dict[str, JsonValue]:
        notes_payload: list[JsonValue] = [note for note in notes]
        return {
            "submission_root": str(submission_root),
            "output_root": str(output_root),
            "balance_row_count": balance_row_count,
            "balance_evidence_row_count": balance_evidence_row_count,
            "location_inventory_row_count": location_inventory_row_count,
            "issue_count": issue_count,
            "blocked": blocked,
            "wrote_location_inventory": wrote_location_inventory,
            "ready_for_balance_check": ready_for_balance_check,
            "notes": notes_payload,
        }


def _clear_canonical_outputs(output_root: Path) -> None:
    for filename in (
        BALANCES_FILENAME,
        BALANCE_EVIDENCE_FILENAME,
        LOCATION_INVENTORY_FILENAME,
    ):
        _remove_file_if_present(output_root / filename)


def _remove_file_if_present(path: Path) -> None:
    if path.is_file():
        path.unlink()
