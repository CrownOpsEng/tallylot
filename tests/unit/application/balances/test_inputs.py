from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable

import pytest

from tallylot.application.balances import (
    BalanceSourceDir,
    build_balance_source_inputs,
)
from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.locations import LocationKind
from tallylot.domain.location_identifiers import location_id_from_parts
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import SourceId
from tallylot.domain.transactions import TransactionFact
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.ports.evidence import ISSUE_HEADER, LOCATION_INVENTORY_HEADER


def _write_fact_rows(
    root: Path,
    *,
    facts: FilesystemFactRepository,
    evidence: FilesystemEvidenceRepository,
    artifacts: FilesystemArtifactStore,
) -> None:
    facts.write_facts(
        root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=datetime(2026, 3, 23, tzinfo=UTC),
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )


def _write_snapshot_rows(
    root: Path,
    *,
    facts: FilesystemFactRepository,
    evidence: FilesystemEvidenceRepository,
    artifacts: FilesystemArtifactStore,
) -> None:
    evidence.write_balance_snapshots(
        root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target(
                    "coinbase",
                    "BTC",
                    datetime(2026, 3, 23, tzinfo=UTC),
                ),
                quantity=Decimal("1.0"),
                snapshot_basis="manual_override",
            ),
        ),
    )


def _write_empty_rows(
    root: Path,
    *,
    facts: FilesystemFactRepository,
    evidence: FilesystemEvidenceRepository,
    artifacts: FilesystemArtifactStore,
) -> None:
    del root, facts, evidence, artifacts


@pytest.mark.parametrize(
    ("mode", "snapshot_origin", "has_facts", "has_snapshot_rows", "writer"),
    (
        (
            "fact_backed",
            "derived_from_facts",
            True,
            False,
            _write_fact_rows,
        ),
        (
            "manual_only",
            "explicit_rows",
            False,
            True,
            _write_snapshot_rows,
        ),
        ("empty", "none", False, False, _write_empty_rows),
    ),
)
def test_build_balance_source_inputs_classifies_input_modes(
    tmp_path: Path,
    mode: str,
    snapshot_origin: str,
    has_facts: bool,
    has_snapshot_rows: bool,
    writer: Callable[..., None],
) -> None:
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    root = tmp_path / mode
    root.mkdir()

    writer(root, facts=facts, evidence=evidence, artifacts=artifacts)

    inputs = build_balance_source_inputs(
        BalanceSourceDir(name=mode, root=root),
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )

    assert inputs.input_mode == mode
    assert inputs.snapshot_origin == snapshot_origin
    assert inputs.has_facts is has_facts
    assert inputs.has_snapshot_rows is has_snapshot_rows
    assert inputs.has_reference_rows is False
    assert len(inputs.targets) == (1 if mode != "empty" else 0)
    assert len(inputs.snapshots) == (1 if mode != "empty" else 0)
    assert len(inputs.references) == 0
    assert len(inputs.reference_issues) == 0
    assert len(inputs.location_inventory) == 0
    assert len(inputs.unexpected_superseded_outputs) == 0


def test_build_balance_source_inputs_prefers_derived_snapshots_over_persisted_rows(
    tmp_path: Path,
) -> None:
    root = tmp_path / "coinbase"
    root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    facts.write_facts(
        root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_snapshots(
        root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("coinbase", "BTC", as_of),
                quantity=Decimal("99.0"),
                snapshot_basis="manual_override",
            ),
        ),
    )
    evidence.write_balance_references(
        root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )
    artifacts.write_rows(
        root / "balance_reference_issues.csv",
        ISSUE_HEADER,
        (
            IssueRecord(
                issue_id="coinbase:balance_reference_issues:1",
                source="coinbase",
                adapter_id="balances",
                severity="high",
                kind="balance_reference_issue",
                message="reference issue",
            ).to_row(),
        ),
    )
    artifacts.write_rows(
        root / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            build_location_inventory_record(
                LocationInventoryBuildSpec(
                    source="coinbase",
                    location_id=location_id_from_parts("coinbase"),
                    location_kind=LocationKind.ACCOUNT,
                    location_label="coinbase",
                    identifier_kind="account",
                    identifier_value="coinbase",
                    evidence_provenance=ProvenanceLocator.from_reference_ref(
                        "wallet.csv"
                    ),
                    confidence="high",
                )
            ).to_row(),
        ),
    )

    inputs = build_balance_source_inputs(
        BalanceSourceDir(name="coinbase", root=root),
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )

    assert inputs.input_mode == "fact_backed"
    assert inputs.snapshot_origin == "derived_from_facts"
    assert inputs.has_snapshot_rows is True
    assert inputs.has_reference_rows is True
    assert inputs.snapshots[0].quantity == Decimal("1.0")
    assert inputs.targets[0].target_at == as_of
    assert inputs.references[0].quantity == Decimal("1.0")
    assert inputs.reference_issues[0].kind == "balance_reference_issue"
    assert inputs.location_inventory[0].location_label == "coinbase"


def test_build_balance_source_inputs_records_superseded_outputs_without_reading_them(
    tmp_path: Path,
) -> None:
    root = tmp_path / "coinbase"
    root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()

    (root / "balances.csv").write_text("stale,legacy,contents\n", encoding="utf-8")
    (root / "balance_evidence.csv").write_text(
        "stale,legacy,contents\n", encoding="utf-8"
    )

    inputs = build_balance_source_inputs(
        BalanceSourceDir(name="coinbase", root=root),
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )

    assert inputs.input_mode == "empty"
    assert inputs.snapshot_origin == "none"
    assert tuple(path.name for path in inputs.unexpected_superseded_outputs) == (
        "balances.csv",
        "balance_evidence.csv",
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
    from tallylot.domain.transactions import (
        SINGLE_PRIMARY_ACTIVITY_POLICY,
        AccountingIntentHint,
        EconomicKind,
        EconomicLeg,
        FactSemantics,
        LegKind,
        ProjectionHint,
        TaxTreatmentHint,
    )
    from tallylot.domain.types import AdapterId, TransactionId

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


def _target(source: str, instrument_id: str, as_of: datetime) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=location_id_from_parts(source),
        instrument_id=InstrumentId(instrument_id),
        balance_kind="available",
        target_at=as_of,
        target_precision=TemporalPrecision.DATE,
    )


def _reference(
    *,
    source: str,
    instrument_id: str,
    quantity: str,
    target_at: datetime,
    reference_kind: BalanceReferenceKind,
) -> BalanceReference:
    return BalanceReference(
        target=_target(source, instrument_id, target_at),
        quantity=Decimal(quantity),
        reference_kind=reference_kind,
        observed_at=target_at,
        observed_precision=TemporalPrecision.DATE,
        support_ref="statement.pdf#page=1",
    )
