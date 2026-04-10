from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.domain.captures import ProvenanceLocator
from tallylot.application.reconciliation import (
    BalanceCoverageRequest,
    BalanceCoverageWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
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
        "source-backed",
        "operator-confirmed",
        "mixed-reference",
        "missing-reference",
        "missing-snapshots",
        "empty-source",
    ):
        (input_root / source_name).mkdir()

    repository.write_balance_snapshots(
        input_root / "source-backed" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("source-backed"),
                location_id=LocationId("source-backed"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "source-backed" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("source-backed"),
                location_id=LocationId("source-backed"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                provenance=ProvenanceLocator.from_reference_ref("source-backed.csv"),
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "operator-confirmed" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("operator-confirmed"),
                location_id=LocationId("operator-confirmed"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_confirmations(
        input_root / "operator-confirmed" / "balance_confirmations.csv",
        (
            BalanceConfirmation(
                source=SourceId("operator-confirmed"),
                location_id=LocationId("operator-confirmed"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                confirmation_kind="manual_assertion",
                asserted_meaning="Operator asserted the runtime balance directly.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 3, 24, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "mixed-reference" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("mixed-reference"),
                location_id=LocationId("mixed-reference"),
                instrument_id=InstrumentId("SOL"),
                quantity=Decimal("3.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
            BalanceSnapshot(
                source=SourceId("mixed-reference"),
                location_id=LocationId("mixed-reference"),
                instrument_id=InstrumentId("USDC"),
                quantity=Decimal("4.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "mixed-reference" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("mixed-reference"),
                location_id=LocationId("mixed-reference"),
                instrument_id=InstrumentId("SOL"),
                quantity=Decimal("3.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                provenance=ProvenanceLocator.from_reference_ref("mixed-reference.csv"),
            ),
        ),
    )
    repository.write_balance_confirmations(
        input_root / "mixed-reference" / "balance_confirmations.csv",
        (
            BalanceConfirmation(
                source=SourceId("mixed-reference"),
                location_id=LocationId("mixed-reference"),
                instrument_id=InstrumentId("USDC"),
                quantity=Decimal("4.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                confirmation_kind="external_support",
                support_ref="wallet-note.txt",
                asserted_meaning="Closing balance from the cited note.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 3, 24, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "missing-reference" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("missing-reference"),
                location_id=LocationId("missing-reference"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("5.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
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
                provenance=ProvenanceLocator.from_reference_ref(
                    "missing-snapshots.csv"
                ),
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "empty-source" / "balances.csv",
        (),
    )
    repository.write_balance_confirmations(
        input_root / "empty-source" / "balance_confirmations.csv",
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

    assert response.source_count == 6
    assert response.comparable_source_count == 3
    assert {row["source"]: row["coverage_status"] for row in rows} == {
        "empty-source": "empty_source",
        "missing-reference": "missing_reference",
        "missing-snapshots": "missing_snapshots",
        "mixed-reference": "mixed_reference",
        "operator-confirmed": "operator_confirmed",
        "source-backed": "source_backed",
    }
    mixed_row = next(row for row in rows if row["source"] == "mixed-reference")
    assert mixed_row["source_backed_reference_count"] == "1"
    assert mixed_row["operator_confirmation_count"] == "1"
    assert mixed_row["missing_reference_count"] == "0"
    assert summary["source_backed_source_count"] == 1
    assert summary["operator_confirmed_source_count"] == 1
    assert summary["mixed_reference_source_count"] == 1
    assert summary["missing_reference_source_count"] == 1
    assert summary["empty_source_count"] == 1
