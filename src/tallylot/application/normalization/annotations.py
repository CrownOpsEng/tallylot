"""Fact-annotation sidecar helpers."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import JsonValue
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_translation import EconomicActivityDraft


@dataclass(frozen=True)
class FactAnnotationRecord:
    fact_id: str
    provenance_refs: tuple[str, ...]
    review_markers: tuple[str, ...]
    adapter_metadata: tuple[AdapterMetadata, ...]

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "fact_id": self.fact_id,
            "provenance_refs": list(self.provenance_refs),
            "review_markers": list(self.review_markers),
            "adapter_metadata": [
                metadata_to_json(item) for item in self.adapter_metadata
            ],
        }


@dataclass(frozen=True)
class LocationAnnotationRecord:
    location_id: str
    adapter_metadata: tuple[AdapterMetadata, ...]

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "location_id": self.location_id,
            "adapter_metadata": [
                metadata_to_json(item) for item in self.adapter_metadata
            ],
        }


def annotation_records_from_drafts(
    drafts: tuple[EconomicActivityDraft, ...],
) -> tuple[FactAnnotationRecord, ...]:
    return tuple(
        FactAnnotationRecord(
            fact_id=draft.activity_id,
            provenance_refs=draft.provenance_refs,
            review_markers=draft.review_markers,
            adapter_metadata=draft.adapter_metadata,
        )
        for draft in drafts
    )


def location_annotation_records(
    location_inventory: tuple[LocationInventoryRecord, ...],
) -> tuple[LocationAnnotationRecord, ...]:
    return tuple(
        LocationAnnotationRecord(
            location_id=str(record.location_id),
            adapter_metadata=record.adapter_metadata,
        )
        for record in location_inventory
        if record.adapter_metadata
    )


def metadata_to_json(metadata: AdapterMetadata) -> dict[str, JsonValue]:
    return {
        "namespace": metadata.namespace,
        "values": metadata.values,
    }
