"""Build location inventory records for application and adapter callers."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.location_identifiers import normalized_identifier
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import LocationId
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.evidence import LocationInventoryRecord


@dataclass(frozen=True)
class LocationInventoryBuildSpec:
    source: str
    location_id: LocationId
    location_kind: LocationKind
    location_label: str
    identifier_kind: str
    identifier_value: str
    evidence_provenance: ProvenanceLocator
    parent_location_id: LocationId | None = None
    location_path: tuple[str, ...] = ()
    capture_uid: str = ""
    capture_label: str = ""
    capture_root_ref: str = ""
    network_scope: str = ""
    controller: str = ""
    parent_location_label: str = ""
    evidence_kind: str = ""
    confidence: str = ""
    notes: str = ""
    adapter_metadata: tuple[AdapterMetadata, ...] = ()


def build_location_inventory_record(
    spec: LocationInventoryBuildSpec,
) -> LocationInventoryRecord:
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
        notes=spec.notes,
        adapter_metadata=spec.adapter_metadata,
    )
