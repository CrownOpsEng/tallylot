from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.reconciliation import (
    BalanceCheckRequest,
    BalanceCheckWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository


def test_balance_check_workflow_writes_single_source_outputs(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    evidence_repo.write_balance_snapshots(
        input_root / "balances.csv",
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
        input_root / "balance_evidence.csv",
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

    response = BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    issue_rows = artifacts.read_rows(output_root / "reconciliation_issues.csv")
    summary = json.loads(
        (output_root / "balance_assertion_summary.json").read_text(encoding="utf-8")
    )
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.issue_source_count == 1
    assert assertion_rows[0]["status"] == "drift"
    assert issue_rows[0]["kind"] == "balance_drift"
    assert summary["assertion_count"] == 1
    assert summary["issue_count"] == 1
    assert check_summary_rows[0]["check_status"] == "issues"
    assert check_summary_rows[0]["max_assertion_date"] == "2025-12-31"


def test_balance_check_workflow_uses_per_source_output_dirs_for_batch_runs(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    input_root.mkdir()
    for source_name in ("clean-source", "issue-source"):
        (input_root / source_name).mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    evidence_repo.write_balance_snapshots(
        input_root / "clean-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        input_root / "clean-source" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                evidence_ref="clean-source.csv",
            ),
        ),
    )
    evidence_repo.write_balance_snapshots(
        input_root / "issue-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("issue-source"),
                location_id=LocationId("issue-source"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        input_root / "issue-source" / "balance_evidence.csv",
        (),
    )

    response = BalanceCheckWorkflow(
        evidence_repo,
        FilesystemArtifactStore(),
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_check_summary.csv"
    )

    assert response.clean_source_count == 1
    assert response.issue_source_count == 1
    assert (output_root / "clean-source" / "balance_assertions.csv").exists()
    assert (output_root / "issue-source" / "reconciliation_issues.csv").exists()
    assert rows[0]["source"] == "clean-source"
    assert rows[1]["source"] == "issue-source"


def test_balance_check_workflow_rejects_output_inside_input_root(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    input_root.mkdir()
    (input_root / "balances.csv").write_text(
        "source,location_id,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,notes\n",
        encoding="utf-8",
    )
    (input_root / "balance_evidence.csv").write_text(
        "source,location_id,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,evidence_ref,notes\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="balance check output root must not be inside balance input root",
    ):
        BalanceCheckWorkflow(
            FilesystemEvidenceRepository(),
            FilesystemArtifactStore(),
        ).execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(input_root),
                output_root_ref=to_resource_ref(input_root / "analysis"),
            )
        )
