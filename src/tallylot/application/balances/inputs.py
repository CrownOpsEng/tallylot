"""Shared balance input discovery, classification, and package assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tallylot.application.balances.filenames import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_REFERENCE_ISSUE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)
from tallylot.application.evidence.location_inventory import (
    LocationInventoryBuildSpec,
    build_location_inventory_record,
)
from tallylot.domain.balances import BalanceReference, BalanceSnapshot, BalanceTarget
from tallylot.domain.captures import provenance_locator_from_row
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.types import LocationId
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import (
    LocationInventoryRecord,
    EvidenceRepositoryPort,
)
from tallylot.ports.facts import FactRepositoryPort

from .snapshots import derive_balance_snapshots
from .targets import latest_balance_targets

FACT_FILENAME = "facts.csv"
LOCATION_INVENTORY_FILENAME = "location_inventory.csv"
SUPERSEDED_BALANCES_FILENAME = "balances.csv"
SUPERSEDED_BALANCE_EVIDENCE_FILENAME = "balance_evidence.csv"

BalanceInputMode = Literal["fact_backed", "manual_only", "empty"]
BalanceSnapshotOrigin = Literal["derived_from_facts", "explicit_rows", "none"]


@dataclass(frozen=True)
class BalanceSourceDir:
    name: str
    root: Path

    @property
    def facts_path(self) -> Path:
        return self.root / FACT_FILENAME

    @property
    def snapshot_path(self) -> Path:
        return self.root / BALANCE_SNAPSHOT_FILENAME

    @property
    def reference_path(self) -> Path:
        return self.root / BALANCE_REFERENCE_FILENAME

    @property
    def reference_issue_path(self) -> Path:
        return self.root / BALANCE_REFERENCE_ISSUE_FILENAME

    @property
    def location_inventory_path(self) -> Path:
        return self.root / LOCATION_INVENTORY_FILENAME

    @property
    def superseded_balances_path(self) -> Path:
        return self.root / SUPERSEDED_BALANCES_FILENAME

    @property
    def superseded_balance_evidence_path(self) -> Path:
        return self.root / SUPERSEDED_BALANCE_EVIDENCE_FILENAME

    def output_root(self, base_output_root: Path, *, single_source: bool) -> Path:
        return base_output_root if single_source else base_output_root / self.name


@dataclass(frozen=True)
class BalanceSourceInputs:
    source: str
    root: Path
    input_mode: BalanceInputMode
    snapshot_origin: BalanceSnapshotOrigin
    targets: tuple[BalanceTarget, ...]
    snapshots: tuple[BalanceSnapshot, ...]
    references: tuple[BalanceReference, ...]
    reference_issues: tuple[IssueRecord, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]
    unexpected_superseded_outputs: tuple[Path, ...]
    has_facts: bool
    has_snapshot_rows: bool
    has_reference_rows: bool


def build_balance_source_inputs(
    source_dir: BalanceSourceDir,
    *,
    facts: FactRepositoryPort,
    evidence: EvidenceRepositoryPort,
    artifacts: ArtifactStorePort,
) -> BalanceSourceInputs:
    fact_rows = (
        facts.read_facts(source_dir.facts_path)
        if source_dir.facts_path.is_file()
        else ()
    )
    reference_rows = (
        evidence.read_balance_references(source_dir.reference_path)
        if source_dir.reference_path.is_file()
        else ()
    )
    reference_issues = _read_issue_records(artifacts, source_dir.reference_issue_path)
    location_inventory = _read_location_inventory(
        artifacts, source_dir.location_inventory_path
    )
    unexpected_superseded_outputs = tuple(
        path
        for path in (
            source_dir.superseded_balances_path,
            source_dir.superseded_balance_evidence_path,
        )
        if path.is_file()
    )
    has_facts = bool(fact_rows)
    has_snapshot_rows = source_dir.snapshot_path.is_file()
    has_reference_rows = bool(reference_rows)
    if has_facts:
        targets = latest_balance_targets(fact_rows)
        snapshots, _ = derive_balance_snapshots(fact_rows, targets)
        input_mode: BalanceInputMode = "fact_backed"
        snapshot_origin: BalanceSnapshotOrigin = "derived_from_facts"
    elif has_snapshot_rows:
        snapshot_rows = (
            evidence.read_balance_snapshots(source_dir.snapshot_path)
            if source_dir.snapshot_path.is_file()
            else ()
        )
        has_snapshot_rows = bool(snapshot_rows)
        targets = tuple(snapshot.target for snapshot in snapshot_rows)
        snapshots = snapshot_rows
        input_mode = "manual_only"
        snapshot_origin = "explicit_rows"
    else:
        targets = ()
        snapshots = ()
        input_mode = "empty"
        snapshot_origin = "none"
    return BalanceSourceInputs(
        source=source_dir.name,
        root=source_dir.root,
        input_mode=input_mode,
        snapshot_origin=snapshot_origin,
        targets=targets,
        snapshots=snapshots,
        references=reference_rows,
        reference_issues=reference_issues,
        location_inventory=location_inventory,
        unexpected_superseded_outputs=unexpected_superseded_outputs,
        has_facts=has_facts,
        has_snapshot_rows=has_snapshot_rows,
        has_reference_rows=has_reference_rows,
    )


def discover_balance_source_dirs(input_root: Path) -> tuple[BalanceSourceDir, ...]:
    if not input_root.is_dir():
        raise ValueError(f"balance input root must be a directory: {input_root}")
    if input_root.name == "captures" or input_root.parent.name == "captures":
        raise ValueError(
            "balance input root must reference assembled source datasets, not capture-normalized outputs"
        )
    if source_dir_input(input_root):
        return (BalanceSourceDir(name=input_root.name, root=input_root),)
    return tuple(
        BalanceSourceDir(name=source_dir.name, root=source_dir)
        for source_dir in sorted(input_root.iterdir())
        if source_dir.is_dir() and _has_balance_inputs(source_dir)
    )


def select_balance_source_dirs(
    source_dirs: tuple[BalanceSourceDir, ...],
    requested_sources: tuple[str, ...],
) -> tuple[BalanceSourceDir, ...]:
    if not requested_sources:
        return source_dirs
    selected = tuple(
        source_dir for source_dir in source_dirs if source_dir.name in requested_sources
    )
    selected_names = {source_dir.name for source_dir in selected}
    missing = tuple(
        source for source in requested_sources if source not in selected_names
    )
    if missing:
        raise ValueError(f"unknown balance source selection: {', '.join(missing)}")
    return selected


def source_dir_input(input_root: Path) -> bool:
    return _has_balance_inputs(input_root)


def _has_balance_inputs(path: Path) -> bool:
    return any(
        (path / filename).is_file()
        for filename in (
            FACT_FILENAME,
            BALANCE_SNAPSHOT_FILENAME,
            BALANCE_REFERENCE_FILENAME,
            BALANCE_REFERENCE_ISSUE_FILENAME,
            LOCATION_INVENTORY_FILENAME,
        )
    )


def _read_issue_records(
    artifacts: ArtifactStorePort,
    path: Path,
) -> tuple[IssueRecord, ...]:
    if not path.is_file():
        return ()
    rows = artifacts.read_rows(path)
    return tuple(_issue_record_from_row(row) for row in rows)


def _issue_record_from_row(row: dict[str, str]) -> IssueRecord:
    return IssueRecord(
        issue_id=row["issue_id"],
        source=row["source"],
        adapter_id=row["adapter_id"],
        severity=row["severity"],
        kind=row["kind"],
        message=row["message"],
        context_timestamp=row.get("context_timestamp", ""),
        raw_file=row.get("raw_file", ""),
        raw_provenance=(
            provenance_locator_from_row(row, prefix="raw")
            if row.get("raw_capture_uid", "").strip()
            or row.get("raw_relative_path", "").strip()
            else None
        ),
        raw_row_ref=row.get("raw_row_ref", ""),
        status=row.get("status", "open"),
    )


def _read_location_inventory(
    artifacts: ArtifactStorePort,
    path: Path,
) -> tuple[LocationInventoryRecord, ...]:
    if not path.is_file():
        return ()
    rows = artifacts.read_rows(path)
    return tuple(_location_inventory_record_from_row(row) for row in rows)


def _location_inventory_record_from_row(
    row: dict[str, str],
) -> LocationInventoryRecord:
    evidence_provenance = provenance_locator_from_row(row, prefix="evidence")
    if evidence_provenance is None:
        raise ValueError("location inventory rows must include evidence provenance")
    parent_location_id = row.get("parent_location_id", "").strip()
    location_path = tuple(
        segment.strip()
        for segment in row.get("location_path", "").split(" / ")
        if segment.strip()
    )
    return build_location_inventory_record(
        LocationInventoryBuildSpec(
            source=row["source"],
            location_id=require_location_id(
                row["location_id"], label="location inventory location_id"
            ),
            location_kind=LocationKind(row["location_kind"]),
            location_label=row["location_label"],
            identifier_kind=row["identifier_kind"],
            identifier_value=row.get("identifier_value", row["display_identifier"]),
            evidence_provenance=evidence_provenance,
            parent_location_id=(
                None if not parent_location_id else LocationId(parent_location_id)
            ),
            location_path=location_path,
            capture_uid=row.get("capture_uid", ""),
            capture_label=row.get("capture_label", ""),
            capture_root_ref=row.get("capture_root_ref", ""),
            network_scope=row.get("network_scope", ""),
            controller=row.get("controller", ""),
            parent_location_label=row.get("parent_location_label", ""),
            evidence_kind=row.get("evidence_kind", ""),
            confidence=row.get("confidence", ""),
            notes=row.get("notes", ""),
        )
    )
