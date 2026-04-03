"""Balance assertion workflow."""

from __future__ import annotations

from tallylot.application.reconciliation.contracts import (
    BalanceAssertionRequest,
    BalanceAssertionResponse,
)
from tallylot.application.resource_refs import path_from_ref
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
        snapshots = self._evidence.read_balance_snapshots(
            path_from_ref(request.snapshot_input_ref)
        )
        evidence = self._evidence.read_balance_evidence(
            path_from_ref(request.evidence_input_ref)
        )
        result = assert_balance_snapshots(snapshots, evidence)

        self._artifacts.write_rows(
            assertion_output_path,
            BALANCE_ASSERTION_HEADER,
            (assertion.to_row() for assertion in result.assertions),
        )
        self._evidence.write_issue_records(
            assertion_output_path.with_name("reconciliation_issues.csv"),
            result.issues,
        )
        self._artifacts.write_json(
            assertion_output_path.with_name("balance_assertion_summary.json"),
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
