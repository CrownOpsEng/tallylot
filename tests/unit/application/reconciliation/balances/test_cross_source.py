from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.reconciliation.balances.cross_source import (
    build_cross_source_corroboration,
)
from tallylot.application.reconciliation.balances.sources import (
    discover_balance_source_dirs,
)
from tallylot.domain.balances import BalanceSnapshot, BalanceTarget
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import SourceId
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
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
            {
                "source": "alpha",
                "location_id": "alpha:wallet_1",
                "normalized_identifier": "shared-one",
                "network_scope": "ethereum",
                "confidence": "high",
            },
            {
                "source": "alpha",
                "location_id": "alpha:wallet_2",
                "normalized_identifier": "shared-one",
                "network_scope": "ethereum",
                "confidence": "high",
            },
            {
                "source": "alpha",
                "location_id": "alpha:wallet_3",
                "normalized_identifier": "shared-two",
                "network_scope": "ethereum",
                "confidence": "high",
            },
        ),
    )
    write_rows(
        source_b / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "beta",
                "location_id": "beta:wallet_1",
                "normalized_identifier": "shared-two",
                "network_scope": "ethereum",
                "confidence": "high",
            },
        ),
    )

    result = build_cross_source_corroboration(
        discover_balance_source_dirs(input_root),
        evidence=evidence,
        artifacts=artifacts,
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
            {
                "source": "alpha",
                "location_id": "alpha:wallet_1",
                "normalized_identifier": "shared-one",
                "network_scope": "ethereum",
                "confidence": "high",
            },
            {
                "source": "alpha",
                "location_id": "alpha:wallet_1",
                "normalized_identifier": "shared-one",
                "network_scope": "ethereum",
                "confidence": "low",
            },
        ),
    )
    write_rows(
        source_b / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (
            {
                "source": "beta",
                "location_id": "beta:wallet_1",
                "normalized_identifier": "shared-one",
                "network_scope": "ethereum",
                "confidence": "high",
            },
        ),
    )

    result = build_cross_source_corroboration(
        discover_balance_source_dirs(input_root),
        evidence=evidence,
        artifacts=artifacts,
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
