from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.balances import (
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
from tallylot.domain.locations import LocationKind
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import SourceId
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.ports.evidence import LOCATION_INVENTORY_HEADER


def test_cross_source_corroboration_keeps_later_groups_after_an_earlier_ambiguity(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    source_a = input_root / "alpha"
    source_b = input_root / "beta"
    source_a.mkdir(parents=True)
    source_b.mkdir(parents=True)

    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    evidence.write_balance_snapshots(
        source_a / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("alpha", "alpha:wallet_3", native_asset_id, as_of),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    evidence.write_balance_snapshots(
        source_b / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("beta", "beta:wallet_1", native_asset_id, as_of),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    write_rows(
        source_a / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            _inventory_row(
                source="alpha",
                location_id="alpha:wallet_1",
                normalized_identifier="shared-one",
            ),
            _inventory_row(
                source="alpha",
                location_id="alpha:wallet_2",
                normalized_identifier="shared-one",
            ),
            _inventory_row(
                source="alpha",
                location_id="alpha:wallet_3",
                normalized_identifier="shared-two",
            ),
        ),
    )
    write_rows(
        source_b / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            _inventory_row(
                source="beta",
                location_id="beta:wallet_1",
                normalized_identifier="shared-two",
            ),
        ),
    )

    source_inputs = tuple(
        build_balance_source_inputs(
            source_dir,
            facts=FilesystemFactRepository(),
            evidence=evidence,
            artifacts=artifacts,
        )
        for source_dir in discover_balance_source_dirs(input_root)
    )

    result = build_cross_source_corroboration(
        source_inputs,
    )

    assert [assertion.status for assertion in result.assertions] == ["matched"]
    assert result.assertions[0].left_source == "alpha"
    assert result.assertions[0].right_source == "beta"
    assert result.assertions[0].normalized_identifier == "shared-two"
    assert [issue.kind for issue in result.issues] == [
        "cross_source_ambiguous_identity"
    ]
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


def test_cross_source_corroboration_keeps_high_confidence_row_when_low_confidence_row_follows(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    source_a = input_root / "alpha"
    source_b = input_root / "beta"
    source_a.mkdir(parents=True)
    source_b.mkdir(parents=True)

    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    native_asset_id = InstrumentId("asset:evm:ethereum:native")

    evidence.write_balance_snapshots(
        source_a / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("alpha", "alpha:wallet_1", native_asset_id, as_of),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    evidence.write_balance_snapshots(
        source_b / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("beta", "beta:wallet_1", native_asset_id, as_of),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    write_rows(
        source_a / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            _inventory_row(
                source="alpha",
                location_id="alpha:wallet_1",
                normalized_identifier="shared-one",
            ),
            _inventory_row(
                source="alpha",
                location_id="alpha:wallet_1",
                normalized_identifier="shared-one",
                confidence="low",
            ),
        ),
    )
    write_rows(
        source_b / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            _inventory_row(
                source="beta",
                location_id="beta:wallet_1",
                normalized_identifier="shared-one",
            ),
        ),
    )

    source_inputs = tuple(
        build_balance_source_inputs(
            source_dir,
            facts=FilesystemFactRepository(),
            evidence=evidence,
            artifacts=artifacts,
        )
        for source_dir in discover_balance_source_dirs(input_root)
    )

    result = build_cross_source_corroboration(
        source_inputs,
    )

    assert [assertion.status for assertion in result.assertions] == ["matched"]
    assert result.assertions[0].left_source == "alpha"
    assert result.assertions[0].right_source == "beta"
    assert result.issues == ()


def _target(
    source: str,
    location_id: str,
    instrument_id: InstrumentId,
    as_of: datetime,
) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=require_location_id(
            location_id, label="cross source target location_id"
        ),
        instrument_id=instrument_id,
        balance_kind="available",
        target_at=as_of,
        target_precision=TemporalPrecision.DATE,
    )


def _inventory_row(
    *,
    source: str,
    location_id: str,
    normalized_identifier: str,
    confidence: str = "high",
) -> dict[str, str]:
    return build_location_inventory_record(
        LocationInventoryBuildSpec(
            source=source,
            location_id=require_location_id(
                location_id, label="cross source location_id"
            ),
            location_kind=LocationKind.ACCOUNT,
            location_label=location_id,
            identifier_kind="address_alias",
            identifier_value=normalized_identifier,
            evidence_provenance=ProvenanceLocator.from_reference_ref("inventory.csv"),
            network_scope="ethereum",
            confidence=confidence,
        )
    ).to_row()
