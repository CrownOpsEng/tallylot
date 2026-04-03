"""Shared location-evidence helpers for adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tallylot.domain.issues import IssueRecord
from tallylot.domain.location_identifiers import (
    BTC_ADDRESS_PATTERN,
    EVM_ADDRESS_PATTERN,
    SOLANA_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    identifier_kind_for_value,
    normalized_identifier,
)
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import LocationId
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.evidence import LocationInventoryRecord

__all__ = (
    "BTC_ADDRESS_PATTERN",
    "EVM_ADDRESS_PATTERN",
    "SOLANA_ADDRESS_PATTERN",
    "TRON_ADDRESS_PATTERN",
    "LocationIssueSpec",
    "LocationRecordSpec",
    "location_id_from_parts",
    "location_identifier_kind",
    "location_issue",
    "location_record",
    "normalized_identifier",
)


@dataclass(frozen=True)
class LocationRecordSpec:
    source: str
    location_id: LocationId
    location_kind: LocationKind
    location_label: str
    identifier_kind: str
    identifier_value: str
    network_scope: str
    controller: str
    evidence_kind: str
    evidence_path: str
    confidence: str
    note: str = ""
    capture_path: str = ""
    parent_location_id: LocationId | None = None
    location_path: tuple[str, ...] = ()
    parent_location_label: str = ""
    adapter_metadata: tuple[AdapterMetadata, ...] = ()


@dataclass(frozen=True)
class LocationIssueSpec:
    source: str
    adapter_id: str
    issue_kind: str
    message: str
    location_id: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""


_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def location_id_from_parts(*parts: str) -> LocationId:
    normalized_parts = tuple(normalized_part for part in parts if (normalized_part := _normalized_location_part(part)))
    if not normalized_parts:
        raise ValueError("location_id requires at least one non-empty part")
    return LocationId(":".join(normalized_parts))


def location_identifier_kind(identifier_value: str) -> str:
    return identifier_kind_for_value(identifier_value)


def location_record(spec: LocationRecordSpec) -> LocationInventoryRecord:
    normalized = normalized_identifier(spec.identifier_kind, spec.identifier_value)
    return LocationInventoryRecord(
        source=spec.source,
        location_id=spec.location_id,
        location_kind=spec.location_kind,
        location_label=spec.location_label,
        parent_location_id=spec.parent_location_id,
        location_path=spec.location_path,
        identifier_kind=spec.identifier_kind,
        identifier_value=spec.identifier_value,
        capture_path=spec.capture_path,
        normalized_identifier=normalized,
        display_identifier=spec.identifier_value,
        network_scope=spec.network_scope,
        controller=spec.controller,
        parent_location_label=spec.parent_location_label,
        evidence_kind=spec.evidence_kind,
        evidence_path=spec.evidence_path,
        confidence=spec.confidence,
        notes=spec.note,
        adapter_metadata=spec.adapter_metadata,
    )


def location_issue(spec: LocationIssueSpec) -> IssueRecord:
    issue_ref = spec.location_id or spec.raw_file or spec.issue_kind
    return IssueRecord(
        issue_id=f"{spec.adapter_id}:{spec.source}:{spec.issue_kind}:{issue_ref}",
        source=spec.source,
        adapter_id=spec.adapter_id,
        severity="medium",
        kind=spec.issue_kind,
        message=spec.message,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
    )


def _normalized_location_part(part: str) -> str:
    return _NON_ALNUM_PATTERN.sub("_", part.strip().lower()).strip("_")
