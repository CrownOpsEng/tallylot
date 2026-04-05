"""Submit validated manual balance packages into canonical reconciliation artifacts."""

from __future__ import annotations

from dataclasses import dataclass
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
    BALANCE_CONFIRMATIONS_FILENAME,
    BALANCES_FILENAME,
    ISSUES_FILENAME,
    ISSUE_HEADER,
    LOCATION_INVENTORY_FILENAME,
    SUMMARY_FILENAME,
)
from .validation import validate_balance_submission


@dataclass(frozen=True)
class _SubmissionStatus:
    balance_row_count: int
    balance_confirmation_row_count: int
    location_inventory_row_count: int
    issue_count: int
    blocked: bool
    wrote_balance_confirmations: bool
    wrote_location_inventory: bool
    ready_for_balance_check: bool
    ready_for_source_backed_checkpoint: bool
    trust_tier: str
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
        if not submission_root.is_dir():
            _clear_canonical_outputs(output_root)
            status = _SubmissionStatus(
                balance_row_count=0,
                balance_confirmation_row_count=0,
                location_inventory_row_count=0,
                issue_count=1,
                blocked=True,
                wrote_balance_confirmations=False,
                wrote_location_inventory=False,
                ready_for_balance_check=False,
                ready_for_source_backed_checkpoint=False,
                trust_tier="operator_confirmed",
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
                balance_row_count=status.balance_row_count,
                balance_confirmation_row_count=status.balance_confirmation_row_count,
                location_inventory_row_count=status.location_inventory_row_count,
                issue_count=status.issue_count,
                blocked=status.blocked,
                wrote_balance_confirmations=status.wrote_balance_confirmations,
                wrote_location_inventory=status.wrote_location_inventory,
                ready_for_balance_check=status.ready_for_balance_check,
                ready_for_source_backed_checkpoint=status.ready_for_source_backed_checkpoint,
                trust_tier=status.trust_tier,
            )
        validation = validate_balance_submission(
            submission_root,
            expected_source=request.source,
        )
        blocked = bool(validation.issues)
        wrote_balance_confirmations = False
        wrote_location_inventory = False
        if not blocked:
            materialized = materialize_balance_submission(
                submission_root=str(submission_root),
                balance_rows=validation.balance_rows,
                balance_confirmation_rows=validation.balance_confirmation_rows,
                location_inventory_rows=validation.location_inventory_rows,
            )
            self._evidence.write_balance_snapshots(
                output_root / BALANCES_FILENAME,
                materialized.balances,
            )
            self._evidence.write_balance_confirmations(
                output_root / BALANCE_CONFIRMATIONS_FILENAME,
                materialized.balance_confirmations,
            )
            wrote_balance_confirmations = True
            _remove_file_if_present(output_root / "balance_evidence.csv")
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
        status = _SubmissionStatus(
            balance_row_count=len(validation.balance_rows),
            balance_confirmation_row_count=len(validation.balance_confirmation_rows),
            location_inventory_row_count=len(validation.location_inventory_rows),
            issue_count=len(validation.issues),
            blocked=blocked,
            wrote_balance_confirmations=wrote_balance_confirmations,
            wrote_location_inventory=wrote_location_inventory,
            ready_for_balance_check=not blocked,
            ready_for_source_backed_checkpoint=False,
            trust_tier="operator_confirmed",
            notes=(
                ("Canonical balances and balance confirmations were written.",)
                if not blocked
                else (
                    "Submission is blocked. Manual-submission-owned canonical artifacts were cleared.",
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
            balance_row_count=status.balance_row_count,
            balance_confirmation_row_count=status.balance_confirmation_row_count,
            location_inventory_row_count=status.location_inventory_row_count,
            issue_count=status.issue_count,
            blocked=status.blocked,
            wrote_balance_confirmations=status.wrote_balance_confirmations,
            wrote_location_inventory=status.wrote_location_inventory,
            ready_for_balance_check=status.ready_for_balance_check,
            ready_for_source_backed_checkpoint=status.ready_for_source_backed_checkpoint,
            trust_tier=status.trust_tier,
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
        status: _SubmissionStatus,
    ) -> dict[str, JsonValue]:
        notes_payload: list[JsonValue] = list(status.notes)
        return {
            "submission_root": str(submission_root),
            "output_root": str(output_root),
            "balance_row_count": status.balance_row_count,
            "balance_confirmation_row_count": status.balance_confirmation_row_count,
            "location_inventory_row_count": status.location_inventory_row_count,
            "issue_count": status.issue_count,
            "blocked": status.blocked,
            "wrote_balance_confirmations": status.wrote_balance_confirmations,
            "wrote_location_inventory": status.wrote_location_inventory,
            "ready_for_balance_check": status.ready_for_balance_check,
            "ready_for_source_backed_checkpoint": status.ready_for_source_backed_checkpoint,
            "trust_tier": status.trust_tier,
            "notes": notes_payload,
        }


def _clear_canonical_outputs(output_root: Path) -> None:
    for filename in (
        BALANCES_FILENAME,
        BALANCE_CONFIRMATIONS_FILENAME,
        LOCATION_INVENTORY_FILENAME,
        "balance_evidence.csv",
    ):
        _remove_file_if_present(output_root / filename)


def _remove_file_if_present(path: Path) -> None:
    if path.is_file():
        path.unlink()
