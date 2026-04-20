"""Assessment sidecar models and payload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tallylot.domain.types import JsonValue

ASSESSMENT_SCHEMA_VERSION = 1
_STAGE_ORDER = {
    "claim": 0,
    "economics": 1,
    "reconciliation": 2,
    "checkpoint": 3,
    "journal": 4,
    "tax": 5,
}


class GapKind(StrEnum):
    MISSING_EVIDENCE = "missing_evidence"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    UNRESOLVED_LINKAGE = "unresolved_linkage"
    CONTRADICTION = "contradiction"
    POLICY_DECISION_REQUIRED = "policy_decision_required"
    MANUAL_DECISION_REQUIRED = "manual_decision_required"


class GapStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class GapMateriality(StrEnum):
    MATERIAL = "material"
    SUPPORTING = "supporting"
    INFORMATIONAL = "informational"


class GapConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class ReviewConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _stage_sort_key(stage: str) -> tuple[int, str]:
    return (_STAGE_ORDER.get(stage, len(_STAGE_ORDER)), stage)


@dataclass(frozen=True)
class GapRecord:
    gap_id: str
    owner_stage: str
    blocking_stages: tuple[str, ...]
    scope_kind: str
    scope_ref: str | None
    subject_ref: tuple[str, ...] | None
    gap_kind: GapKind
    gap_key: str
    status: GapStatus
    materiality: GapMateriality
    confidence: GapConfidence

    def __post_init__(self) -> None:
        if self.scope_kind != "claim_scope":
            raise ValueError("this slice supports only scope_kind='claim_scope'")
        if not self.scope_ref:
            raise ValueError("claim_scope gap records require scope_ref")
        if self.subject_ref is not None:
            raise ValueError("this slice requires subject_ref=None")

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "gap_id": self.gap_id,
            "owner_stage": self.owner_stage,
            "blocking_stages": list(
                stage for stage in sorted(self.blocking_stages, key=_stage_sort_key)
            ),
            "scope_kind": self.scope_kind,
            "scope_ref": self.scope_ref,
            "subject_ref": None,
            "gap_kind": self.gap_kind.value,
            "gap_key": self.gap_key,
            "status": self.status.value,
            "materiality": self.materiality.value,
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True)
class GapExplanation:
    gap_id: str
    known_facts: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    possible_meanings: tuple[str, ...]
    required_evidence: tuple[str, ...]
    resolution_options: tuple[str, ...]
    next_action: str
    provenance_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "gap_id": self.gap_id,
            "known_facts": list(self.known_facts),
            "missing_inputs": list(self.missing_inputs),
            "possible_meanings": list(self.possible_meanings),
            "required_evidence": list(self.required_evidence),
            "resolution_options": list(self.resolution_options),
            "next_action": self.next_action,
            "provenance_refs": list(sorted(self.provenance_refs)),
        }


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    owner_stage: str
    scope_kind: str
    scope_ref: str | None
    subject_ref: tuple[str, ...] | None
    review_kind: str
    review_key: str
    status: ReviewStatus
    confidence: ReviewConfidence
    gap_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.scope_kind != "claim_scope":
            raise ValueError("this slice supports only scope_kind='claim_scope'")
        if not self.scope_ref:
            raise ValueError("claim_scope review records require scope_ref")
        if self.subject_ref is not None:
            raise ValueError("this slice requires subject_ref=None")

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "review_id": self.review_id,
            "owner_stage": self.owner_stage,
            "scope_kind": self.scope_kind,
            "scope_ref": self.scope_ref,
            "subject_ref": None,
            "review_kind": self.review_kind,
            "review_key": self.review_key,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "gap_ids": list(sorted(self.gap_ids)),
        }


@dataclass(frozen=True)
class ReviewExplanation:
    review_id: str
    headline: str
    known_facts: tuple[str, ...]
    follow_up: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "review_id": self.review_id,
            "headline": self.headline,
            "known_facts": list(self.known_facts),
            "follow_up": list(self.follow_up),
            "provenance_refs": list(sorted(self.provenance_refs)),
        }


def stable_gap_id(
    *,
    owner_stage: str,
    scope_kind: str,
    scope_ref: str,
    gap_kind: GapKind,
    gap_key: str,
) -> str:
    return ":".join((owner_stage, scope_kind, scope_ref, gap_kind.value, gap_key))


def stable_review_id(
    *,
    owner_stage: str,
    scope_kind: str,
    scope_ref: str,
    review_kind: str,
    review_key: str,
) -> str:
    return ":".join((owner_stage, scope_kind, scope_ref, review_kind, review_key))


def canonical_gap_records(records: tuple[GapRecord, ...]) -> tuple[GapRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.owner_stage,
                item.scope_kind,
                item.subject_ref or (),
                item.scope_ref or "",
                item.gap_kind.value,
                item.gap_id,
            ),
        )
    )


def canonical_review_records(
    records: tuple[ReviewRecord, ...],
) -> tuple[ReviewRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.owner_stage,
                item.scope_kind,
                item.subject_ref or (),
                item.scope_ref or "",
                item.review_kind,
                item.review_id,
            ),
        )
    )


def gap_records_payload(records: tuple[GapRecord, ...]) -> list[JsonValue]:
    return [record.to_payload() for record in canonical_gap_records(records)]


def gap_explanations_payload(
    explanations: tuple[GapExplanation, ...],
) -> list[JsonValue]:
    return [
        explanation.to_payload()
        for explanation in sorted(explanations, key=lambda item: item.gap_id)
    ]


def review_records_payload(records: tuple[ReviewRecord, ...]) -> list[JsonValue]:
    return [record.to_payload() for record in canonical_review_records(records)]


def review_explanations_payload(
    explanations: tuple[ReviewExplanation, ...],
) -> list[JsonValue]:
    return [
        explanation.to_payload()
        for explanation in sorted(explanations, key=lambda item: item.review_id)
    ]
