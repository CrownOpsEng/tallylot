"""Balance assertion workflow."""

from __future__ import annotations

from pathlib import Path

from tallylot.application.reconciliation.contracts import (
    BalanceAssertionRequest,
    BalanceAssertionResponse,
)
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import (
    ensure_output_not_within_input_tree,
)
from tallylot.domain.reconciliation import assert_balance_snapshots
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort

BALANCE_ASSERTION_HEADER = (
    "source",
    "location_id",
    "instrument_id",
    "balance_kind",
    "snapshot_quantity",
    "evidence_quantity",
    "quantity_difference",
    "status",
    "snapshot_as_of_at",
    "snapshot_as_of_precision",
    "evidence_as_of_at",
    "evidence_as_of_precision",
    "evidence_ref",
    "notes",
)


class AssertBalancesUseCase:
    def __init__(
        self,
        evidence: EvidenceRepositoryPort,
        artifacts: ArtifactStorePort,
    ) -> None:
        self._evidence = evidence
        self._artifacts = artifacts

    def execute(self, request: BalanceAssertionRequest) -> BalanceAssertionResponse:
        assertion_output_path = path_from_ref(request.assertion_output_ref)
        snapshot_path = path_from_ref(request.snapshot_input_ref)
        evidence_path = path_from_ref(request.evidence_input_ref)
        issue_output_path = assertion_output_path.with_name("reconciliation_issues.csv")
        summary_output_path = assertion_output_path.with_name(
            "balance_assertion_summary.json"
        )
        _ensure_output_paths_are_safe(
            snapshot_path,
            input_label="balance snapshot input",
            output_paths={
                "balance assertion output": assertion_output_path,
                "balance assertion issue output": issue_output_path,
                "balance assertion summary output": summary_output_path,
            },
        )
        _ensure_output_paths_are_safe(
            evidence_path,
            input_label="balance evidence input",
            output_paths={
                "balance assertion output": assertion_output_path,
                "balance assertion issue output": issue_output_path,
                "balance assertion summary output": summary_output_path,
            },
        )
        snapshots = self._evidence.read_balance_snapshots(snapshot_path)
        evidence = self._evidence.read_balance_evidence(evidence_path)
        result = assert_balance_snapshots(snapshots, evidence)

        self._artifacts.write_rows(
            assertion_output_path,
            BALANCE_ASSERTION_HEADER,
            (assertion.to_row() for assertion in result.assertions),
        )
        self._evidence.write_issue_records(
            issue_output_path,
            result.issues,
        )
        self._artifacts.write_json(
            summary_output_path,
            {
                "assertion_count": len(result.assertions),
                "issue_count": len(result.issues),
            },
        )
        return BalanceAssertionResponse(
            assertion_output_ref=request.assertion_output_ref,
            assertion_count=len(result.assertions),
            issue_count=len(result.issues),
        )


def _ensure_output_paths_are_safe(
    input_path: Path,
    *,
    input_label: str,
    output_paths: dict[str, Path],
) -> None:
    for output_label, output_path in output_paths.items():
        ensure_output_not_within_input_tree(
            input_path,
            output_path,
            input_label=input_label,
            output_label=output_label,
        )
