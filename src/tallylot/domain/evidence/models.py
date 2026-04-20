"""EvidenceSet domain models and JSON payload helpers."""

# pylint: disable=too-many-arguments

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
)

EVIDENCE_SET_SCHEMA_VERSION = 1
_EMPTY_ARRAY: tuple[str, ...] = ()


class EvidenceSelectionBasis(StrEnum):
    SINGLE_MEMBER = "single_member"
    DUPLICATE = "duplicate"
    COVERAGE = "coverage"
    FRESHNESS = "freshness"
    AMBIGUOUS_OVERLAP = "ambiguous_overlap"
    UPSTREAM_GAP = "upstream_gap"


class EvidenceMemberStatus(StrEnum):
    SELECTED = "selected"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"


class EvidenceMemberKind(StrEnum):
    RETAIL_ACTIVITY_EXPORT_FILE = "retail_activity_export_file"
    STATEMENT_DOCUMENT_FILE = "statement_document_file"


class EvidenceObservationKind(StrEnum):
    STATEMENT_DOCUMENT = "statement_document"
    STATEMENT_BALANCE_ROW = "statement_balance_row"


def _hash_payload(payload: JsonValue) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _tuple_json(values: tuple[str, ...]) -> list[JsonValue]:
    return list(values)


def _refs_json(values: tuple[tuple[str, ...], ...]) -> list[JsonValue]:
    return [list(item) for item in values]


def _optional_temporal(
    value: datetime | None,
    *,
    precision: TemporalPrecision | None,
    label: str,
) -> str:
    if value is None or precision is None:
        return ""
    return format_temporal_value(value, precision=precision, label=label)


@dataclass(frozen=True)
class EvidenceObservationRecord:
    evidence_set_id: str
    member_id: str
    observation_id: str
    kind: EvidenceObservationKind
    key: tuple[str, ...]
    observed_at: datetime | None = None
    precision: TemporalPrecision | None = None
    provenance_refs: tuple[tuple[str, ...], ...] = ()
    statement_kind: str = ""
    document_effective_at: datetime | None = None
    document_effective_precision: TemporalPrecision | None = None
    statement_as_of: datetime | None = None
    statement_as_of_precision: TemporalPrecision | None = None
    location_group_label: str = ""
    location_label: str = ""
    balance_kind: str = ""
    instrument_symbol: str = ""
    quantity: Decimal | None = None
    notes: str = ""
    staked_quantity_text: str = ""
    value_amount_text: str = ""
    value_currency: str = ""
    price_amount_text: str = ""
    price_currency: str = ""

    def semantic_payload(self) -> dict[str, JsonValue]:
        return {
            "kind": self.kind.value,
            "key": _tuple_json(self.key),
            "observed_at": _optional_temporal(
                self.observed_at,
                precision=self.precision,
                label="evidence observation observed_at",
            ),
            "precision": "" if self.precision is None else self.precision.value,
            "provenance_refs": _refs_json(tuple(sorted(self.provenance_refs))),
            "statement_kind": self.statement_kind,
            "document_effective_at": _optional_temporal(
                self.document_effective_at,
                precision=self.document_effective_precision,
                label="evidence observation document_effective_at",
            ),
            "document_effective_precision": (
                ""
                if self.document_effective_precision is None
                else self.document_effective_precision.value
            ),
            "statement_as_of": _optional_temporal(
                self.statement_as_of,
                precision=self.statement_as_of_precision,
                label="evidence observation statement_as_of",
            ),
            "statement_as_of_precision": (
                ""
                if self.statement_as_of_precision is None
                else self.statement_as_of_precision.value
            ),
            "location_group_label": self.location_group_label,
            "location_label": self.location_label,
            "balance_kind": self.balance_kind,
            "instrument_symbol": self.instrument_symbol,
            "quantity": format_decimal(self.quantity),
            "notes": self.notes,
            "staked_quantity_text": self.staked_quantity_text,
            "value_amount_text": self.value_amount_text,
            "value_currency": self.value_currency,
            "price_amount_text": self.price_amount_text,
            "price_currency": self.price_currency,
        }

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "evidence_set_id": self.evidence_set_id,
            "member_id": self.member_id,
            "observation_id": self.observation_id,
            **self.semantic_payload(),
        }


@dataclass(frozen=True)
class EvidenceMemberRecord:
    evidence_set_id: str
    selection_id: str
    member_id: str
    source_slug: str
    adapter_id: str
    capture_uid: str
    kind: EvidenceMemberKind
    locator: tuple[str, ...]
    status: EvidenceMemberStatus
    capture_manifest_fingerprint: str

    def semantic_payload(self) -> dict[str, JsonValue]:
        return {
            "source_slug": self.source_slug,
            "adapter_id": self.adapter_id,
            "capture_uid": self.capture_uid,
            "kind": self.kind.value,
            "locator": _tuple_json(self.locator),
            "status": self.status.value,
            "capture_manifest_fingerprint": self.capture_manifest_fingerprint,
        }

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "evidence_set_id": self.evidence_set_id,
            "selection_id": self.selection_id,
            "member_id": self.member_id,
            **self.semantic_payload(),
        }


@dataclass(frozen=True)
class EvidenceSelectionRecord:
    evidence_set_id: str
    selection_id: str
    key: tuple[str, ...]
    fingerprint: str
    basis: EvidenceSelectionBasis
    blocking_gap_refs: tuple[str, ...] = ()

    def semantic_payload(self) -> dict[str, JsonValue]:
        return {
            "key": _tuple_json(self.key),
            "fingerprint": self.fingerprint,
            "basis": self.basis.value,
            "blocking_gap_refs": list(sorted(self.blocking_gap_refs)),
        }

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "evidence_set_id": self.evidence_set_id,
            "selection_id": self.selection_id,
            **self.semantic_payload(),
        }


@dataclass(frozen=True)
class EvidenceSet:
    evidence_set_id: str
    selection_fingerprint: str
    capture_manifest_fingerprint: str
    evidence_selection_records: tuple[EvidenceSelectionRecord, ...]
    evidence_member_records: tuple[EvidenceMemberRecord, ...]
    evidence_observation_records: tuple[EvidenceObservationRecord, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "capture_manifest_fingerprint": self.capture_manifest_fingerprint,
            "evidence_member_records": [
                record.to_payload() for record in self.evidence_member_records
            ],
            "evidence_observation_records": [
                record.to_payload() for record in self.evidence_observation_records
            ],
            "evidence_selection_records": [
                record.to_payload() for record in self.evidence_selection_records
            ],
            "evidence_set_id": self.evidence_set_id,
            "schema_version": EVIDENCE_SET_SCHEMA_VERSION,
            "selection_fingerprint": self.selection_fingerprint,
        }


def stable_evidence_set_id(
    *,
    source_slug: str,
    adapter_id: str,
    capture_uid: str,
    selection_fingerprint: str,
) -> str:
    return ":".join((source_slug, adapter_id, capture_uid, selection_fingerprint))


def stable_selection_id(*, evidence_set_id: str, key: tuple[str, ...]) -> str:
    return ":".join((evidence_set_id, *key))


def stable_member_id(
    *,
    evidence_set_id: str,
    kind: EvidenceMemberKind,
    locator: tuple[str, ...],
) -> str:
    return ":".join((evidence_set_id, kind.value, *locator))


def stable_observation_id(
    *,
    member_id: str,
    kind: EvidenceObservationKind,
    key: tuple[str, ...],
) -> str:
    return ":".join((member_id, kind.value, *key))


def selection_fingerprint_for_records(
    *,
    selections: tuple[EvidenceSelectionRecord, ...],
    members: tuple[EvidenceMemberRecord, ...],
    observations: tuple[EvidenceObservationRecord, ...],
) -> str:
    selection_semantics: list[JsonValue] = []
    for selection in sorted(selections, key=lambda item: item.key):
        selection_members = tuple(
            member
            for member in members
            if member.selection_id == selection.selection_id
            or (
                not member.selection_id
                and member.evidence_set_id == selection.evidence_set_id
                and member.selection_id == ""
            )
        )
        payload = selection_semantics_payload(
            selection=selection,
            members=selection_members,
            observations=observations,
        )
        selection_semantics.append(payload)
    return _hash_payload(selection_semantics)


def selection_semantics_payload(
    *,
    selection: EvidenceSelectionRecord,
    members: tuple[EvidenceMemberRecord, ...],
    observations: tuple[EvidenceObservationRecord, ...],
) -> dict[str, JsonValue]:
    member_payloads: list[JsonValue] = []
    for member in sorted(members, key=lambda item: (item.status.value, item.locator)):
        member_observations = tuple(
            observation
            for observation in observations
            if observation.member_id == member.member_id
            or (
                not observation.member_id
                and observation.evidence_set_id == member.evidence_set_id
            )
        )
        member_payloads.append(
            {
                **member.semantic_payload(),
                "observations": [
                    observation.semantic_payload()
                    for observation in sorted(
                        member_observations,
                        key=lambda item: (item.kind.value, item.key),
                    )
                ],
            }
        )
    return {
        "basis": selection.basis.value,
        "blocking_gap_refs": list(sorted(selection.blocking_gap_refs)),
        "key": list(selection.key),
        "members": member_payloads,
    }


def selection_record_fingerprints(
    *,
    selections: tuple[EvidenceSelectionRecord, ...],
    members: tuple[EvidenceMemberRecord, ...],
    observations: tuple[EvidenceObservationRecord, ...],
) -> dict[str, str]:
    return {
        selection.selection_id: _hash_payload(
            selection_semantics_payload(
                selection=selection,
                members=tuple(
                    member
                    for member in members
                    if member.selection_id == selection.selection_id
                ),
                observations=observations,
            )
        )
        for selection in selections
    }
