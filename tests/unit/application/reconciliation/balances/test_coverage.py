from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import location_id_from_parts
from tallylot.application.reconciliation import (
    BalanceCoverageRequest,
    BalanceCoverageWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository


def _target(source: str, instrument_id: str, as_of: datetime) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=location_id_from_parts(source),
        instrument_id=InstrumentId(instrument_id),
        balance_kind="available",
        target_at=as_of,
        target_precision=TemporalPrecision.DATE,
    )


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
        input_root / "source-backed" / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("source-backed", "BTC", as_of),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    repository.write_balance_references(
        input_root / "source-backed" / "balance_references.csv",
        (
            BalanceReference(
                target=_target("source-backed", "BTC", as_of),
                quantity=Decimal("1.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                support_ref="source-backed.csv",
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "operator-confirmed" / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("operator-confirmed", "ETH", as_of),
                quantity=Decimal("2.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    repository.write_balance_references(
        input_root / "operator-confirmed" / "balance_references.csv",
        (
            BalanceReference(
                target=_target("operator-confirmed", "ETH", as_of),
                quantity=Decimal("2.0"),
                reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 3, 24, tzinfo=UTC),
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "mixed-reference" / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("mixed-reference", "SOL", as_of),
                quantity=Decimal("3.0"),
                snapshot_basis="fact_cutoff",
            ),
            BalanceSnapshot(
                target=_target("mixed-reference", "USDC", as_of),
                quantity=Decimal("4.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    repository.write_balance_references(
        input_root / "mixed-reference" / "balance_references.csv",
        (
            BalanceReference(
                target=_target("mixed-reference", "SOL", as_of),
                quantity=Decimal("3.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                support_ref="mixed-reference.csv",
            ),
            BalanceReference(
                target=_target("mixed-reference", "USDC", as_of),
                quantity=Decimal("4.0"),
                reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                support_ref="wallet-note.txt",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 3, 24, tzinfo=UTC),
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "missing-reference" / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("missing-reference", "BTC", as_of),
                quantity=Decimal("5.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "missing-snapshots" / "balance_snapshots.csv",
        (),
    )
    repository.write_balance_references(
        input_root / "missing-snapshots" / "balance_references.csv",
        (
            BalanceReference(
                target=_target("missing-snapshots", "SOL", as_of),
                quantity=Decimal("3.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                support_ref="missing-snapshots.csv",
            ),
        ),
    )

    repository.write_balance_snapshots(
        input_root / "empty-source" / "balance_snapshots.csv",
        (),
    )
    repository.write_balance_references(
        input_root / "empty-source" / "balance_references.csv",
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
        "operator-confirmed": "resolved_reference",
        "source-backed": "resolved_reference",
    }
    mixed_row = next(row for row in rows if row["source"] == "mixed-reference")
    assert mixed_row["source_document_count"] == "1"
    assert mixed_row["operator_assertion_count"] == "1"
    assert mixed_row["missing_reference_count"] == "0"
    assert summary["resolved_reference_source_count"] == 2
    assert summary["mixed_reference_source_count"] == 1
    assert summary["missing_reference_source_count"] == 1
    assert summary["empty_source_count"] == 1
