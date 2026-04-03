from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.reconciliation import (
    BalanceCoverageRequest,
    BalanceCoverageWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository


def test_balance_coverage_workflow_classifies_source_coverage_states(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_path = tmp_path / "balance_coverage.csv"
    repository = FilesystemEvidenceRepository()
    input_root.mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    for source_name in (
        "comparable",
        "missing-evidence",
        "missing-snapshots",
        "empty-source",
    ):
        (input_root / source_name).mkdir()

    repository.write_balance_snapshots(
        input_root / "comparable" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("comparable"),
                location_id=LocationId("comparable"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "comparable" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("comparable"),
                location_id=LocationId("comparable"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                evidence_ref="comparable.csv",
            ),
        ),
    )
    repository.write_balance_snapshots(
        input_root / "missing-evidence" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("missing-evidence"),
                location_id=LocationId("missing-evidence"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "missing-evidence" / "balance_evidence.csv",
        (),
    )
    repository.write_balance_snapshots(
        input_root / "missing-snapshots" / "balances.csv",
        (),
    )
    repository.write_balance_evidence(
        input_root / "missing-snapshots" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("missing-snapshots"),
                location_id=LocationId("missing-snapshots"),
                instrument_id=InstrumentId("SOL"),
                quantity=Decimal("3.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                evidence_ref="missing-snapshots.csv",
            ),
        ),
    )
    repository.write_balance_snapshots(
        input_root / "empty-source" / "balances.csv",
        (),
    )
    repository.write_balance_evidence(
        input_root / "empty-source" / "balance_evidence.csv",
        (),
    )

    response = BalanceCoverageWorkflow(FilesystemArtifactStore()).execute(
        BalanceCoverageRequest(
            input_root_ref=to_resource_ref(input_root),
            coverage_output_ref=to_resource_ref(output_path),
        )
    )

    rows = FilesystemArtifactStore().read_rows(output_path)
    summary = json.loads(
        (tmp_path / "balance_coverage_summary.json").read_text(encoding="utf-8")
    )

    assert response.source_count == 4
    assert response.comparable_source_count == 1
    assert [row["coverage_status"] for row in rows] == [
        "comparable",
        "empty_source",
        "missing_evidence",
        "missing_snapshots",
    ]
    assert summary["missing_evidence_source_count"] == 1
    assert summary["empty_source_count"] == 1
