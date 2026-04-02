"""Fact-annotation sidecar helpers."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import JsonValue
from tallylot.ports.source_translation import EconomicActivityDraft


@dataclass(frozen=True)
class FactAnnotationRecord:
    fact_id: str
    provenance_refs: tuple[str, ...]
    review_markers: tuple[str, ...]

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "fact_id": self.fact_id,
            "provenance_refs": list(self.provenance_refs),
            "review_markers": list(self.review_markers),
        }


def annotation_records_from_drafts(
    drafts: tuple[EconomicActivityDraft, ...],
) -> tuple[FactAnnotationRecord, ...]:
    return tuple(
        FactAnnotationRecord(
            fact_id=draft.activity_id,
            provenance_refs=draft.provenance_refs,
            review_markers=draft.review_markers,
        )
        for draft in drafts
    )
