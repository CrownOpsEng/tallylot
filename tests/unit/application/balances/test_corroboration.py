from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.balances import (
    BalanceInputMode,
    BalanceSnapshotOrigin,
    BalanceSourceInputs,
    build_balance_source_inputs,
    build_cross_source_corroboration,
    discover_balance_source_dirs,
)
from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.domain.balances import BalanceSnapshot, BalanceTarget
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
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.ports.evidence import LOCATION_INVENTORY_HEADER, LocationInventoryRecord


def test_cross_source_corroboration_reports_exact_statuses() -> None:
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    matched_result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                ),
                inventory_records=(
                    _inventory_record("alpha", "alpha:wallet_1", "shared-one"),
                ),
            ),
            _source_input(
                source="beta",
                snapshots=(_snapshot("beta", "beta:wallet_1", native_asset_id, as_of),),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-one"),
                ),
            ),
        )
    )
    assert [assertion.status for assertion in matched_result.assertions] == ["matched"]
    assert matched_result.issues == ()
    assert matched_result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 0,
        "matched_count": 1,
        "drift_count": 0,
        "missing_left_count": 0,
        "missing_right_count": 0,
        "ambiguous_count": 0,
        "skipped_count": 0,
    }

    drift_result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                ),
                inventory_records=(
                    _inventory_record("alpha", "alpha:wallet_1", "shared-one"),
                ),
            ),
            _source_input(
                source="beta",
                snapshots=(
                    _snapshot(
                        "beta",
                        "beta:wallet_1",
                        native_asset_id,
                        as_of,
                        quantity="2",
                    ),
                ),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-one"),
                ),
            ),
        )
    )
    assert [assertion.status for assertion in drift_result.assertions] == ["drift"]
    assert drift_result.issues == ()
    assert drift_result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 0,
        "matched_count": 0,
        "drift_count": 1,
        "missing_left_count": 0,
        "missing_right_count": 0,
        "ambiguous_count": 0,
        "skipped_count": 0,
    }

    missing_left_result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(),
                inventory_records=(
                    _inventory_record("alpha", "alpha:wallet_1", "shared-one"),
                ),
                input_mode="empty",
                snapshot_origin="none",
                has_snapshot_rows=False,
            ),
            _source_input(
                source="beta",
                snapshots=(_snapshot("beta", "beta:wallet_1", native_asset_id, as_of),),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-one"),
                ),
            ),
        )
    )
    assert [assertion.status for assertion in missing_left_result.assertions] == [
        "missing_left"
    ]
    assert missing_left_result.issues == ()
    assert missing_left_result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 0,
        "matched_count": 0,
        "drift_count": 0,
        "missing_left_count": 1,
        "missing_right_count": 0,
        "ambiguous_count": 0,
        "skipped_count": 0,
    }

    missing_right_result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                ),
                inventory_records=(
                    _inventory_record("alpha", "alpha:wallet_1", "shared-one"),
                ),
            ),
            _source_input(
                source="beta",
                snapshots=(),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-one"),
                ),
                input_mode="empty",
                snapshot_origin="none",
                has_snapshot_rows=False,
            ),
        )
    )
    assert [assertion.status for assertion in missing_right_result.assertions] == [
        "missing_right"
    ]
    assert missing_right_result.issues == ()
    assert missing_right_result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 0,
        "matched_count": 0,
        "drift_count": 0,
        "missing_left_count": 0,
        "missing_right_count": 1,
        "ambiguous_count": 0,
        "skipped_count": 0,
    }


def test_cross_source_corroboration_emits_duplicate_join_key_issue() -> None:
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                ),
                inventory_records=(
                    _inventory_record("alpha", "alpha:wallet_1", "shared-one"),
                ),
            ),
            _source_input(
                source="beta",
                snapshots=(_snapshot("beta", "beta:wallet_1", native_asset_id, as_of),),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-one"),
                ),
            ),
        )
    )

    assert [assertion.status for assertion in result.assertions] == ["matched"]
    assert [issue.kind for issue in result.issues] == [
        "cross_source_ambiguous_identity"
    ]
    assert "same shared join key" in result.issues[0].message
    assert result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 1,
        "matched_count": 1,
        "drift_count": 0,
        "missing_left_count": 0,
        "missing_right_count": 0,
        "ambiguous_count": 1,
        "skipped_count": 1,
    }


def test_cross_source_corroboration_skips_low_confidence_identity() -> None:
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    result = build_cross_source_corroboration(
        (
            _source_input(
                source="alpha",
                snapshots=(
                    _snapshot("alpha", "alpha:wallet_1", native_asset_id, as_of),
                ),
                inventory_records=(
                    _inventory_record(
                        "alpha",
                        "alpha:wallet_1",
                        "shared-low",
                        confidence="low",
                    ),
                ),
            ),
            _source_input(
                source="beta",
                snapshots=(_snapshot("beta", "beta:wallet_1", native_asset_id, as_of),),
                inventory_records=(
                    _inventory_record("beta", "beta:wallet_1", "shared-low"),
                ),
            ),
        )
    )

    assert result.assertions == ()
    assert [issue.kind for issue in result.issues] == [
        "cross_source_low_confidence_identity"
    ]
    assert result.summary_payload() == {
        "assertion_count": 0,
        "issue_count": 1,
        "matched_count": 0,
        "drift_count": 0,
        "missing_left_count": 0,
        "missing_right_count": 0,
        "ambiguous_count": 0,
        "skipped_count": 1,
    }


def test_cross_source_corroboration_handles_fact_backed_and_manual_sources(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    source_a = input_root / "alpha"
    source_b = input_root / "beta"
    source_a.mkdir(parents=True)
    source_b.mkdir(parents=True)

    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    facts.write_facts(
        source_a / "facts.csv",
        (
            _fact(
                fact_id="fact-alpha",
                source="alpha",
                timestamp=as_of,
                location_id="alpha:wallet_1",
                instrument_id=str(native_asset_id),
                quantity="1",
            ),
        ),
    )
    write_rows(
        source_a / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (_inventory_record("alpha", "alpha:wallet_1", "shared-one").to_row(),),
    )
    evidence.write_balance_snapshots(
        source_b / "balance_snapshots.csv",
        (
            _snapshot(
                "beta",
                "beta:wallet_1",
                native_asset_id,
                as_of,
                precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
    )
    write_rows(
        source_b / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (_inventory_record("beta", "beta:wallet_1", "shared-one").to_row(),),
    )

    source_inputs = tuple(
        build_balance_source_inputs(
            source_dir,
            facts=facts,
            evidence=evidence,
            artifacts=artifacts,
        )
        for source_dir in discover_balance_source_dirs(input_root)
    )

    result = build_cross_source_corroboration(source_inputs)

    assert source_inputs[0].input_mode == "fact_backed"
    assert source_inputs[0].snapshot_origin == "derived_from_facts"
    assert source_inputs[1].input_mode == "manual_only"
    assert source_inputs[1].snapshot_origin == "explicit_rows"
    assert [assertion.status for assertion in result.assertions] == ["matched"]
    assert result.issues == ()
    assert result.summary_payload() == {
        "assertion_count": 1,
        "issue_count": 0,
        "matched_count": 1,
        "drift_count": 0,
        "missing_left_count": 0,
        "missing_right_count": 0,
        "ambiguous_count": 0,
        "skipped_count": 0,
    }


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


def _snapshot(
    source: str,
    location_id: str,
    instrument_id: InstrumentId,
    as_of: datetime,
    *,
    quantity: str = "1",
    precision: TemporalPrecision = TemporalPrecision.DATE,
) -> BalanceSnapshot:
    return BalanceSnapshot(
        target=_target(
            source,
            location_id,
            instrument_id,
            as_of,
            precision=precision,
        ),
        quantity=Decimal(quantity),
        snapshot_basis="fact_cutoff",
    )


def _target(
    source: str,
    location_id: str,
    instrument_id: InstrumentId,
    as_of: datetime,
    *,
    precision: TemporalPrecision = TemporalPrecision.DATE,
) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=location_id_from_parts(location_id),
        instrument_id=instrument_id,
        balance_kind="available",
        target_at=as_of,
        target_precision=precision,
    )


def _inventory_record(
    source: str,
    location_id: str,
    normalized_identifier: str,
    *,
    confidence: str = "high",
) -> LocationInventoryRecord:
    return build_location_inventory_record(
        LocationInventoryBuildSpec(
            source=source,
            location_id=location_id_from_parts(location_id),
            location_kind=LocationKind.ACCOUNT,
            location_label=location_id,
            identifier_kind="address_alias",
            identifier_value=normalized_identifier,
            evidence_provenance=ProvenanceLocator.from_reference_ref("inventory.csv"),
            network_scope="ethereum",
            confidence=confidence,
        )
    )


def _source_input(
    *,
    source: str,
    snapshots: tuple[BalanceSnapshot, ...],
    inventory_records: tuple[LocationInventoryRecord, ...],
    input_mode: BalanceInputMode = "manual_only",
    snapshot_origin: BalanceSnapshotOrigin = "explicit_rows",
    has_snapshot_rows: bool = True,
) -> BalanceSourceInputs:
    return BalanceSourceInputs(
        source=source,
        root=Path("/tmp"),
        input_mode=input_mode,
        snapshot_origin=snapshot_origin,
        timezone="UTC",
        targets=tuple(snapshot.target for snapshot in snapshots),
        snapshots=snapshots,
        references=(),
        reference_issues=(),
        location_inventory=inventory_records,
        unexpected_superseded_outputs=(),
        has_facts=input_mode == "fact_backed",
        has_snapshot_rows=has_snapshot_rows,
        has_reference_rows=False,
    )
