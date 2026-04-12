from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.balances.merge import (
    balance_reference_semantic_key,
    balance_snapshot_semantic_key,
    merge_balance_reference_rows,
    merge_balance_references,
    merge_balance_snapshot_rows,
    merge_balance_snapshots,
)
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.location_identifiers import location_id_from_parts
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.evidence import (
    BALANCE_REFERENCE_HEADER,
    BALANCE_SNAPSHOT_HEADER,
)

SOURCE = "coinbase"
LOCATION_ID = str(location_id_from_parts("coinbase", "primary"))
INSTRUMENT_ID = "BTC"
TARGET_AT = datetime(2026, 3, 23, tzinfo=UTC)
TARGET_AT_ALT = datetime(2026, 3, 24, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 3, 23, tzinfo=UTC)
OBSERVED_AT_ALT = datetime(2026, 3, 24, tzinfo=UTC)


def _snapshot_row(
    quantity: str,
    *,
    target_at: datetime = TARGET_AT,
) -> dict[str, str]:
    return {
        "source": SOURCE,
        "location_id": LOCATION_ID,
        "instrument_id": INSTRUMENT_ID,
        "balance_kind": "available",
        "target_at": target_at.strftime("%Y-%m-%d %H:%M:%S"),
        "target_precision": "timestamp",
        "quantity": quantity,
        "snapshot_basis": "fact_cutoff",
        "notes": "",
    }


def _snapshot_object(
    quantity: str,
    *,
    target_at: datetime = TARGET_AT,
) -> BalanceSnapshot:
    return BalanceSnapshot(
        target=BalanceTarget(
            source=SourceId(SOURCE),
            location_id=location_id_from_parts("coinbase", "primary"),
            instrument_id=InstrumentId(INSTRUMENT_ID),
            balance_kind="available",
            target_at=target_at,
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal(quantity),
        snapshot_basis="fact_cutoff",
    )


def _reference_row(
    quantity: str,
    *,
    target_at: datetime = TARGET_AT,
    observed_at: datetime = OBSERVED_AT,
    support_ref: str = "statement.pdf#page=1",
) -> dict[str, str]:
    return {
        "source": SOURCE,
        "location_id": LOCATION_ID,
        "instrument_id": INSTRUMENT_ID,
        "balance_kind": "available",
        "target_at": target_at.strftime("%Y-%m-%d %H:%M:%S"),
        "target_precision": "timestamp",
        "quantity": quantity,
        "reference_kind": BalanceReferenceKind.SOURCE_DOCUMENT.value,
        "observed_at": observed_at.strftime("%Y-%m-%d %H:%M:%S"),
        "observed_precision": "timestamp",
        "support_ref": support_ref,
        "provider_family": "",
        "provider_locator": "",
        "provider_block_ref": "",
        "reviewed_by": "",
        "reviewed_at": "",
        "notes": "",
    }


def _reference_object(
    quantity: str,
    *,
    target_at: datetime = TARGET_AT,
    observed_at: datetime = OBSERVED_AT,
    support_ref: str = "statement.pdf#page=1",
) -> BalanceReference:
    return BalanceReference(
        target=BalanceTarget(
            source=SourceId(SOURCE),
            location_id=location_id_from_parts("coinbase", "primary"),
            instrument_id=InstrumentId(INSTRUMENT_ID),
            balance_kind="available",
            target_at=target_at,
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal(quantity),
        reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
        observed_at=observed_at,
        observed_precision=TemporalPrecision.TIMESTAMP,
        support_ref=support_ref,
    )


@pytest.mark.parametrize("kind", ("snapshot", "reference"))
def test_balance_semantic_key_matches_for_rows_and_objects(kind: str) -> None:
    if kind == "snapshot":
        snapshot_row = _snapshot_row("1.0")
        snapshot_object = _snapshot_object("1.0")
        assert balance_snapshot_semantic_key(
            snapshot_row
        ) == balance_snapshot_semantic_key(snapshot_object)
        return

    reference_row = _reference_row("1.0")
    reference_object = _reference_object("1.0")
    assert balance_reference_semantic_key(
        reference_row
    ) == balance_reference_semantic_key(reference_object)


@pytest.mark.parametrize("kind", ("snapshot", "reference"))
def test_balance_row_merges_deduplicate_identical_rows_and_keep_order(
    tmp_path: Path,
    kind: str,
) -> None:
    artifacts = FilesystemArtifactStore()
    root_a = tmp_path / "capture-a"
    root_b = tmp_path / "capture-b"
    root_a.mkdir()
    root_b.mkdir()

    if kind == "snapshot":
        rows_a = (
            _snapshot_row("2.0", target_at=TARGET_AT_ALT),
            _snapshot_row("1.0", target_at=TARGET_AT),
        )
        rows_b = (
            _snapshot_row("1.0", target_at=TARGET_AT),
            _snapshot_row("2.0", target_at=TARGET_AT_ALT),
        )
        artifacts.write_rows(
            root_a / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            rows_a,
        )
        artifacts.write_rows(
            root_b / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            rows_b,
        )

        merged_rows, issues = merge_balance_snapshot_rows(
            artifacts,
            (root_a, root_b),
            source=SOURCE,
        )
        assert merged_rows == (
            _snapshot_row("1.0", target_at=TARGET_AT),
            _snapshot_row("2.0", target_at=TARGET_AT_ALT),
        )
        assert issues == ()
        return

    rows_a = (
        _reference_row("2.0", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT),
        _reference_row("1.0", target_at=TARGET_AT, observed_at=OBSERVED_AT),
    )
    rows_b = (
        _reference_row("1.0", target_at=TARGET_AT, observed_at=OBSERVED_AT),
        _reference_row("2.0", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT),
    )
    artifacts.write_rows(
        root_a / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        rows_a,
    )
    artifacts.write_rows(
        root_b / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        rows_b,
    )

    merged_rows, issues = merge_balance_reference_rows(
        artifacts,
        (root_a, root_b),
        source=SOURCE,
    )
    assert merged_rows == (
        _reference_row("1.0", target_at=TARGET_AT, observed_at=OBSERVED_AT),
        _reference_row("2.0", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT),
    )
    assert issues == ()


@pytest.mark.parametrize("kind", ("snapshot", "reference"))
def test_balance_row_merges_emit_conflict_issue_for_same_semantic_key_and_quantity_change(
    tmp_path: Path,
    kind: str,
) -> None:
    artifacts = FilesystemArtifactStore()
    root_a = tmp_path / "capture-a"
    root_b = tmp_path / "capture-b"
    root_a.mkdir()
    root_b.mkdir()

    if kind == "snapshot":
        artifacts.write_rows(
            root_a / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            (_snapshot_row("1.0"),),
        )
        artifacts.write_rows(
            root_b / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            (_snapshot_row("2.0"),),
        )
        merged_rows, issues = merge_balance_snapshot_rows(
            artifacts,
            (root_a, root_b),
            source=SOURCE,
        )
        assert len(merged_rows) == 2
        assert len(issues) == 1
        assert issues[0].to_row()["kind"] == "assembly_semantic_conflict"
        assert issues[0].to_row()["raw_file"] == "balance_snapshots.csv"
        return

    artifacts.write_rows(
        root_a / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        (_reference_row("1.0"),),
    )
    artifacts.write_rows(
        root_b / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        (_reference_row("2.0"),),
    )
    merged_rows, issues = merge_balance_reference_rows(
        artifacts,
        (root_a, root_b),
        source=SOURCE,
    )
    assert len(merged_rows) == 2
    assert len(issues) == 1
    assert issues[0].to_row()["kind"] == "assembly_semantic_conflict"
    assert issues[0].to_row()["raw_file"] == "balance_references.csv"


@pytest.mark.parametrize("kind", ("snapshot", "reference"))
def test_balance_merge_functions_match_between_assembly_rows_and_submission_objects(
    tmp_path: Path,
    kind: str,
) -> None:
    artifacts = FilesystemArtifactStore()
    root_a = tmp_path / "capture-a"
    root_b = tmp_path / "capture-b"
    root_a.mkdir()
    root_b.mkdir()

    if kind == "snapshot":
        artifacts.write_rows(
            root_a / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            (
                _snapshot_row("2", target_at=TARGET_AT_ALT),
                _snapshot_row("1", target_at=TARGET_AT),
            ),
        )
        artifacts.write_rows(
            root_b / "balance_snapshots.csv",
            BALANCE_SNAPSHOT_HEADER,
            (_snapshot_row("2", target_at=TARGET_AT_ALT),),
        )
        merged_rows, issues = merge_balance_snapshot_rows(
            artifacts,
            (root_a, root_b),
            source=SOURCE,
        )
        merged_snapshot_objects = merge_balance_snapshots(
            existing_snapshots=(
                _snapshot_object("2", target_at=TARGET_AT_ALT),
                _snapshot_object("1", target_at=TARGET_AT),
            ),
            submitted_snapshots=(_snapshot_object("2", target_at=TARGET_AT_ALT),),
        )
        expected_rows = tuple(snapshot.to_row() for snapshot in merged_snapshot_objects)
        assert merged_rows == expected_rows
        assert issues == ()
        return

    artifacts.write_rows(
        root_a / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        (
            _reference_row("2", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT),
            _reference_row("1", target_at=TARGET_AT, observed_at=OBSERVED_AT),
        ),
    )
    artifacts.write_rows(
        root_b / "balance_references.csv",
        BALANCE_REFERENCE_HEADER,
        (_reference_row("2", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT),),
    )
    merged_rows, issues = merge_balance_reference_rows(
        artifacts,
        (root_a, root_b),
        source=SOURCE,
    )
    merged_reference_objects = merge_balance_references(
        existing_references=(
            _reference_object(
                "2", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT
            ),
            _reference_object("1", target_at=TARGET_AT, observed_at=OBSERVED_AT),
        ),
        submitted_references=(
            _reference_object(
                "2", target_at=TARGET_AT_ALT, observed_at=OBSERVED_AT_ALT
            ),
        ),
    )
    expected_rows = tuple(reference.to_row() for reference in merged_reference_objects)
    assert merged_rows == expected_rows
    assert issues == ()
