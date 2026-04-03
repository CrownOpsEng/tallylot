from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.reconciliation import (
    AssertBalancesUseCase,
    BalanceAssertionRequest,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository


def test_assert_balances_use_case_writes_assertions_and_issues(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "balances.csv"
    evidence_path = tmp_path / "balance_evidence.csv"
    assertion_path = tmp_path / "balance_assertions.csv"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    evidence_repo.write_balance_snapshots(
        snapshot_path,
        (
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        evidence_path,
        (
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.5"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                evidence_ref="statement.pdf#page=1",
            ),
        ),
    )

    response = AssertBalancesUseCase(evidence_repo, artifacts).execute(
        BalanceAssertionRequest(
            snapshot_input_ref=to_resource_ref(snapshot_path),
            evidence_input_ref=to_resource_ref(evidence_path),
            assertion_output_ref=to_resource_ref(assertion_path),
        )
    )

    assertion_rows = artifacts.read_rows(assertion_path)
    issue_rows = artifacts.read_rows(tmp_path / "reconciliation_issues.csv")
    summary = json.loads(
        (tmp_path / "balance_assertion_summary.json").read_text(encoding="utf-8")
    )

    assert response.assertion_count == 1
    assert response.issue_count == 1
    assert assertion_rows[0]["status"] == "drift"
    assert assertion_rows[0]["quantity_difference"] == "-0.5"
    assert assertion_rows[0]["evidence_ref"] == "statement.pdf#page=1"
    assert issue_rows[0]["kind"] == "balance_drift"
    assert summary["assertion_count"] == 1
    assert summary["issue_count"] == 1
