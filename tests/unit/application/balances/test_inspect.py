from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.balances import (
    BALANCE_INSPECT_HEADER,
    BalanceInspectRequest,
    BalanceInspectWorkflow,
)
from tallylot.application.balances.inspect import (
    _cross_source_ready_status,
    _offline_ready_status,
)
from tallylot.application.balances.inputs import (
    BalanceInputMode,
    BalanceSnapshotOrigin,
    BalanceSourceInputs,
)
from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.locations import LocationKind
from tallylot.domain.location_identifiers import location_id_from_parts
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactSemantics,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, SourceId, TransactionId
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.ports.evidence import LOCATION_INVENTORY_HEADER, LocationInventoryRecord


def _source_input(
    *,
    source: str,
    input_mode: BalanceInputMode,
    snapshot_origin: BalanceSnapshotOrigin,
    targets: tuple[BalanceTarget, ...],
    snapshots: tuple[BalanceSnapshot, ...],
    references: tuple[BalanceReference, ...],
    location_inventory: tuple[LocationInventoryRecord, ...],
    has_facts: bool,
    has_snapshot_rows: bool,
    has_reference_rows: bool,
) -> BalanceSourceInputs:
    return BalanceSourceInputs(
        source=source,
        root=Path("/tmp"),
        input_mode=input_mode,
        snapshot_origin=snapshot_origin,
        timezone="UTC",
        targets=targets,
        snapshots=snapshots,
        references=references,
        reference_issues=(),
        location_inventory=location_inventory,
        unexpected_superseded_outputs=(),
        has_facts=has_facts,
        has_snapshot_rows=has_snapshot_rows,
        has_reference_rows=has_reference_rows,
    )


def _fact(
    *,
    fact_id: str,
    source: str,
    timestamp: datetime,
    location_id: str,
    instrument_id: str,
    quantity: str,
) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(fact_id),
        source=SourceId(source),
        adapter_id=AdapterId("structured_csv"),
        timestamp=timestamp,
        location_id=location_id_from_parts(location_id),
        semantics=FactSemantics(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        ),
        legs=(
            EconomicLeg(
                leg_id=f"{fact_id}_primary".replace("-", "_"),
                kind=LegKind.PRIMARY,
                instrument_id=InstrumentId(instrument_id),
                quantity=Decimal(quantity),
            ),
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )


def _target(
    source: str,
    instrument_id: str,
    as_of: datetime,
    *,
    precision: TemporalPrecision = TemporalPrecision.DATE,
) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=location_id_from_parts(source),
        instrument_id=InstrumentId(instrument_id),
        balance_kind="available",
        target_at=as_of,
        target_precision=precision,
    )


def _snapshot(source: str, instrument_id: str, as_of: datetime) -> BalanceSnapshot:
    return BalanceSnapshot(
        target=_target(source, instrument_id, as_of),
        quantity=Decimal("1.0"),
        snapshot_basis="fact_cutoff",
    )


def _reference(
    target: BalanceTarget,
    reference_kind: BalanceReferenceKind,
    *,
    support_ref: str = "statement.pdf#page=1",
    reviewed_by: str | None = None,
    reviewed_at: datetime | None = None,
) -> BalanceReference:
    if reference_kind is BalanceReferenceKind.OPERATOR_ASSERTION:
        return BalanceReference(
            target=target,
            quantity=Decimal("1.0"),
            reference_kind=reference_kind,
            observed_at=target.target_at,
            observed_precision=target.target_precision,
            reviewed_by=reviewed_by or "operator@example.com",
            reviewed_at=reviewed_at or datetime(2026, 1, 1, tzinfo=UTC),
        )
    return BalanceReference(
        target=target,
        quantity=Decimal("1.0"),
        reference_kind=reference_kind,
        observed_at=target.target_at,
        observed_precision=target.target_precision,
        support_ref=support_ref,
    )


def _inventory_row(source: str) -> LocationInventoryRecord:
    return build_location_inventory_record(
        LocationInventoryBuildSpec(
            source=source,
            location_id=location_id_from_parts(source),
            location_kind=LocationKind.ACCOUNT,
            location_label=source,
            identifier_kind="account",
            identifier_value=source,
            evidence_provenance=ProvenanceLocator.from_reference_ref(f"{source}.csv"),
            confidence="high",
        )
    )


def test_balance_inspect_ready_status_helpers_cover_exact_states() -> None:
    target = _target("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC))
    snapshot = _snapshot("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC))
    source_input = _source_input(
        source="coinbase",
        input_mode="fact_backed",
        snapshot_origin="derived_from_facts",
        targets=(target,),
        snapshots=(snapshot,),
        references=(_reference(target, BalanceReferenceKind.SOURCE_DOCUMENT),),
        location_inventory=(_inventory_row("coinbase"),),
        has_facts=True,
        has_snapshot_rows=True,
        has_reference_rows=True,
    )

    assert (
        _offline_ready_status(
            source_input=source_input,
            target_count=1,
            matched_reference_count=1,
        )
        == "ready"
    )
    assert (
        _offline_ready_status(
            source_input=source_input,
            target_count=1,
            matched_reference_count=0,
        )
        == "missing_references"
    )
    assert (
        _offline_ready_status(
            source_input=source_input,
            target_count=0,
            matched_reference_count=0,
        )
        == "no_balance_targets"
    )
    assert (
        _offline_ready_status(
            source_input=_source_input(
                source="empty",
                input_mode="empty",
                snapshot_origin="none",
                targets=(),
                snapshots=(),
                references=(),
                location_inventory=(),
                has_facts=False,
                has_snapshot_rows=False,
                has_reference_rows=False,
            ),
            target_count=0,
            matched_reference_count=0,
        )
        == "no_balance_inputs"
    )


@pytest.mark.parametrize(
    ("source_input", "target_count", "snapshot_count", "expected"),
    (
        (
            _source_input(
                source="coinbase",
                input_mode="manual_only",
                snapshot_origin="explicit_rows",
                targets=(
                    _target("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC)),
                ),
                snapshots=(
                    _snapshot("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC)),
                ),
                references=(),
                location_inventory=(_inventory_row("coinbase"),),
                has_facts=False,
                has_snapshot_rows=True,
                has_reference_rows=False,
            ),
            1,
            1,
            "ready",
        ),
        (
            _source_input(
                source="coinbase",
                input_mode="manual_only",
                snapshot_origin="explicit_rows",
                targets=(
                    _target("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC)),
                ),
                snapshots=(
                    _snapshot("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC)),
                ),
                references=(),
                location_inventory=(),
                has_facts=False,
                has_snapshot_rows=True,
                has_reference_rows=False,
            ),
            1,
            1,
            "missing_location_inventory",
        ),
        (
            _source_input(
                source="coinbase",
                input_mode="manual_only",
                snapshot_origin="explicit_rows",
                targets=(),
                snapshots=(),
                references=(),
                location_inventory=(),
                has_facts=False,
                has_snapshot_rows=True,
                has_reference_rows=False,
            ),
            0,
            0,
            "not_comparable",
        ),
        (
            _source_input(
                source="coinbase",
                input_mode="manual_only",
                snapshot_origin="explicit_rows",
                targets=(),
                snapshots=(
                    _snapshot("coinbase", "BTC", datetime(2026, 3, 23, tzinfo=UTC)),
                ),
                references=(),
                location_inventory=(_inventory_row("coinbase"),),
                has_facts=False,
                has_snapshot_rows=True,
                has_reference_rows=False,
            ),
            0,
            1,
            "not_comparable",
        ),
        (
            _source_input(
                source="empty",
                input_mode="empty",
                snapshot_origin="none",
                targets=(),
                snapshots=(),
                references=(),
                location_inventory=(),
                has_facts=False,
                has_snapshot_rows=False,
                has_reference_rows=False,
            ),
            0,
            0,
            "not_applicable",
        ),
    ),
)
def test_balance_inspect_cross_source_ready_status_helpers_cover_exact_states(
    source_input: BalanceSourceInputs,
    target_count: int,
    snapshot_count: int,
    expected: str,
) -> None:
    assert (
        _cross_source_ready_status(
            source_input=source_input,
            target_count=target_count,
            snapshot_count=snapshot_count,
        )
        == expected
    )


def test_balance_inspect_workflow_writes_exact_rows_and_summary_counts(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_path = tmp_path / "balance_inspect.csv"
    facts = FilesystemFactRepository()
    repository = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    for source_name in (
        "source-backed",
        "manual-ready",
        "missing-reference",
        "empty-source",
    ):
        (input_root / source_name).mkdir()

    facts.write_facts(
        input_root / "source-backed" / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="source-backed",
                timestamp=as_of,
                location_id="source-backed",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    repository.write_balance_references(
        input_root / "source-backed" / "balance_references.csv",
        (
            _reference(
                _target(
                    "source-backed",
                    "BTC",
                    as_of,
                    precision=TemporalPrecision.TIMESTAMP,
                ),
                BalanceReferenceKind.SOURCE_DOCUMENT,
                support_ref="source-backed.csv",
            ),
        ),
    )
    write_rows(
        input_root / "source-backed" / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (_inventory_row("source-backed").to_row(),),
    )

    repository.write_balance_snapshots(
        input_root / "manual-ready" / "balance_snapshots.csv",
        (_snapshot("manual-ready", "ETH", as_of),),
    )
    repository.write_balance_references(
        input_root / "manual-ready" / "balance_references.csv",
        (
            _reference(
                _target("manual-ready", "ETH", as_of),
                BalanceReferenceKind.OPERATOR_ASSERTION,
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 3, 24, tzinfo=UTC),
            ),
        ),
    )
    write_rows(
        input_root / "manual-ready" / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (_inventory_row("manual-ready").to_row(),),
    )
    (input_root / "manual-ready" / "balances.csv").write_text(
        "stale,legacy,contents\n",
        encoding="utf-8",
    )
    (input_root / "manual-ready" / "balance_evidence.csv").write_text(
        "stale,legacy,contents\n",
        encoding="utf-8",
    )

    repository.write_balance_snapshots(
        input_root / "missing-reference" / "balance_snapshots.csv",
        (_snapshot("missing-reference", "BTC", as_of),),
    )
    write_rows(
        input_root / "missing-reference" / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (_inventory_row("missing-reference").to_row(),),
    )

    repository.write_balance_references(
        input_root / "empty-source" / "balance_references.csv",
        (),
    )

    response = BalanceInspectWorkflow(
        facts=facts,
        evidence=repository,
        artifacts=artifacts,
    ).execute(
        BalanceInspectRequest(
            input_root_ref=to_resource_ref(input_root),
            inspect_output_ref=to_resource_ref(output_path),
        )
    )

    rows = artifacts.read_rows(output_path)
    summary = json.loads(
        (tmp_path / "balance_inspect_summary.json").read_text(encoding="utf-8")
    )
    rows_by_source = {row["source"]: row for row in rows}

    assert response.source_count == 4
    assert response.comparable_source_count == 3
    assert tuple(rows[0].keys()) == BALANCE_INSPECT_HEADER
    assert rows_by_source["source-backed"]["input_mode"] == "fact_backed"
    assert rows_by_source["source-backed"]["snapshot_origin"] == "derived_from_facts"
    assert rows_by_source["source-backed"]["offline_ready"] == "ready"
    assert rows_by_source["source-backed"]["cross_source_ready"] == "ready"
    assert rows_by_source["source-backed"]["source_document_count"] == "1"
    assert rows_by_source["source-backed"]["unexpected_superseded_output_count"] == "0"
    assert rows_by_source["manual-ready"]["input_mode"] == "manual_only"
    assert rows_by_source["manual-ready"]["snapshot_origin"] == "explicit_rows"
    assert rows_by_source["manual-ready"]["offline_ready"] == "ready"
    assert rows_by_source["manual-ready"]["cross_source_ready"] == "ready"
    assert rows_by_source["manual-ready"]["operator_assertion_count"] == "1"
    assert rows_by_source["manual-ready"]["unexpected_superseded_output_count"] == "2"
    assert rows_by_source["missing-reference"]["offline_ready"] == "missing_references"
    assert rows_by_source["missing-reference"]["cross_source_ready"] == "ready"
    assert rows_by_source["missing-reference"]["missing_reference_count"] == "1"
    assert rows_by_source["empty-source"]["input_mode"] == "empty"
    assert rows_by_source["empty-source"]["snapshot_origin"] == "none"
    assert rows_by_source["empty-source"]["offline_ready"] == "no_balance_inputs"
    assert rows_by_source["empty-source"]["cross_source_ready"] == "not_applicable"
    assert summary["source_count"] == 4
    assert summary["inspect_status_counts"] == {
        "missing_references": 1,
        "no_balance_inputs": 1,
        "ready": 2,
    }
    assert summary["cross_source_ready_counts"] == {
        "not_applicable": 1,
        "ready": 3,
    }
    assert summary["offline_ready_source_count"] == 2
    assert summary["cross_source_ready_source_count"] == 3
    assert summary["missing_reference_source_count"] == 1
    assert summary["no_balance_target_source_count"] == 0
    assert summary["no_balance_input_source_count"] == 1
    assert summary["missing_location_inventory_source_count"] == 0
    assert summary["not_comparable_source_count"] == 0
    assert summary["not_applicable_source_count"] == 1
