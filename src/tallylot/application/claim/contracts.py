"""Claim-stage builder contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tallylot.domain.assessment import (
    GapExplanation,
    GapRecord,
    ReviewExplanation,
    ReviewRecord,
)
from tallylot.domain.types import JsonValue
from tallylot.domain.claim import ClaimSet
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.annotations import AdapterMetadata


@dataclass(frozen=True)
class DraftProjectionFieldRecord:
    claim_bundle_id: str
    economic_kind: str
    projection_hint: str
    accounting_intent_hint: str
    tax_treatment_hint: str
    description: str
    tx_hash_or_null: str
    operation_group_id_or_null: str
    confidence: str
    status: str
    draft_order: int
    review_markers: tuple[str, ...] = ()
    adapter_metadata: tuple[AdapterMetadata, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "claim_bundle_id": self.claim_bundle_id,
            "economic_kind": self.economic_kind,
            "projection_hint": self.projection_hint,
            "accounting_intent_hint": self.accounting_intent_hint,
            "tax_treatment_hint": self.tax_treatment_hint,
            "description": self.description,
            "tx_hash_or_null": self.tx_hash_or_null,
            "operation_group_id_or_null": self.operation_group_id_or_null,
            "confidence": self.confidence,
            "status": self.status,
            "draft_order": self.draft_order,
            "review_markers": list(self.review_markers),
            "adapter_metadata": [
                {
                    "namespace": metadata.namespace,
                    "values": metadata.values,
                }
                for metadata in self.adapter_metadata
            ],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "DraftProjectionFieldRecord":
        return cls(
            claim_bundle_id=str(payload["claim_bundle_id"]),
            economic_kind=str(payload["economic_kind"]),
            projection_hint=str(payload["projection_hint"]),
            accounting_intent_hint=str(payload["accounting_intent_hint"]),
            tax_treatment_hint=str(payload["tax_treatment_hint"]),
            description=str(payload["description"]),
            tx_hash_or_null=str(payload["tx_hash_or_null"]),
            operation_group_id_or_null=str(payload["operation_group_id_or_null"]),
            confidence=str(payload["confidence"]),
            status=str(payload["status"]),
            draft_order=int(cast(int | str, payload["draft_order"])),
            review_markers=tuple(
                str(item)
                for item in cast(list[object], payload.get("review_markers", []))
            ),
            adapter_metadata=tuple(
                AdapterMetadata(
                    namespace=str(item["namespace"]),
                    values=cast(dict[str, JsonValue], item["values"]),
                )
                for item in cast(
                    list[dict[str, object]],
                    payload.get("adapter_metadata", []),
                )
            ),
        )


@dataclass(frozen=True)
class CoinbaseClaimBuildResult:
    claim_set: ClaimSet
    gap_records: tuple[GapRecord, ...]
    gap_explanations: tuple[GapExplanation, ...]
    review_records: tuple[ReviewRecord, ...]
    review_explanations: tuple[ReviewExplanation, ...]
    draft_projection_field_records: tuple[DraftProjectionFieldRecord, ...]
    compatibility_issue_records: tuple[IssueRecord, ...]
    compatibility_review_records: tuple[NormalizationReviewRecord, ...]
