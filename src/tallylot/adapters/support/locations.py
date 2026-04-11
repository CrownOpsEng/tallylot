"""Shared location-evidence helpers for adapters."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord
from tallylot.domain.location_identifiers import (
    BTC_ADDRESS_PATTERN as _BTC_ADDRESS_PATTERN,
    EVM_ADDRESS_PATTERN as _EVM_ADDRESS_PATTERN,
    SOLANA_ADDRESS_PATTERN as _SOLANA_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN as _TRON_ADDRESS_PATTERN,
    identifier_kind_for_value as _identifier_kind_for_value,
    is_onchain_location_id as _is_onchain_location_id,
    location_id_from_identifier as _location_id_from_identifier,
    location_id_from_parts as _location_id_from_parts,
    normalized_identifier as _normalized_identifier,
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
    "is_onchain_location_id",
    "location_id_from_parts",
    "location_id_from_identifier",
    "location_identifier_kind",
    "location_issue",
    "location_record",
    "normalized_identifier",
)

BTC_ADDRESS_PATTERN = _BTC_ADDRESS_PATTERN
EVM_ADDRESS_PATTERN = _EVM_ADDRESS_PATTERN
SOLANA_ADDRESS_PATTERN = _SOLANA_ADDRESS_PATTERN
TRON_ADDRESS_PATTERN = _TRON_ADDRESS_PATTERN


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
    evidence_provenance: ProvenanceLocator
    confidence: str
    note: str = ""
    capture_uid: str = ""
    capture_label: str = ""
    capture_root_ref: str = ""
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


def location_id_from_parts(*parts: str) -> LocationId:
    return _location_id_from_parts(*parts)


def location_identifier_kind(identifier_value: str) -> str:
    return _identifier_kind_for_value(identifier_value)


def normalized_identifier(identifier_kind: str, identifier_value: str) -> str:
    return _normalized_identifier(identifier_kind, identifier_value)


def is_onchain_location_id(location_id: str) -> bool:
    return _is_onchain_location_id(location_id)


def location_id_from_identifier(
    identifier_kind: str,
    identifier_value: str,
    *,
    network_scope: str = "",
    suffix: tuple[str, ...] = (),
) -> LocationId:
    return _location_id_from_identifier(
        identifier_kind,
        identifier_value,
        network_scope=network_scope,
        suffix=suffix,
    )


def location_record(spec: LocationRecordSpec) -> LocationInventoryRecord:
    return LocationInventoryRecord(
        source=spec.source,
        location_id=spec.location_id,
        location_kind=spec.location_kind,
        location_label=spec.location_label,
        parent_location_id=spec.parent_location_id,
        location_path=spec.location_path,
        identifier_kind=spec.identifier_kind,
        identifier_value=spec.identifier_value,
        capture_uid=spec.capture_uid,
        capture_label=spec.capture_label,
        capture_root_ref=spec.capture_root_ref,
        normalized_identifier=normalized_identifier(
            spec.identifier_kind, spec.identifier_value
        ),
        display_identifier=spec.identifier_value,
        network_scope=spec.network_scope,
        controller=spec.controller,
        parent_location_label=spec.parent_location_label,
        evidence_kind=spec.evidence_kind,
        evidence_provenance=spec.evidence_provenance,
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
