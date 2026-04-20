"""ClaimSet domain models and JSON payload helpers."""

# pylint: disable=too-many-arguments,too-many-instance-attributes

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
from typing import cast

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import format_decimal, format_temporal_value

CLAIM_SET_SCHEMA_VERSION = 1


class ClaimKind(StrEnum):
    ACTIVITY = "activity"
    BALANCE = "balance"
    INSTRUMENT = "instrument"
    LOCATION = "location"
    BENEFICIAL_OWNER = "beneficial_owner"
    VALUATION = "valuation"


class ClaimRecordStatus(StrEnum):
    ASSERTED = "asserted"
    SUPERSEDED = "superseded"


class ClaimBundleDecisionOutcome(StrEnum):
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"


class ClaimBundleDecisionBasis(StrEnum):
    SINGLE_BUNDLE = "single_bundle"
    INSUFFICIENT_IDENTITY = "insufficient_identity"
    INSUFFICIENT_TEMPORAL_PRECISION = "insufficient_temporal_precision"
    CONFLICTING_CLAIMS = "conflicting_claims"
    UPSTREAM_GAP = "upstream_gap"
    POLICY_DECISION_REQUIRED = "policy_decision_required"
    LATER_BUNDLE_SELECTED = "later_bundle_selected"


def _hash_payload(payload: JsonValue) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _optional_temporal(
    value: datetime | None,
    *,
    precision: TemporalPrecision | None,
    label: str,
) -> str:
    if value is None or precision is None:
        return ""
    return format_temporal_value(value, precision=precision, label=label)


def _sorted_texts(values: tuple[str, ...]) -> list[JsonValue]:
    return list(sorted(values))


@dataclass(frozen=True)
class ClaimLegSpec:
    slot: int
    role: str
    quantity: Decimal
    instrument_claim_refs: tuple[str, ...]
    location_claim_ref: str
    subtype: str
    attributed_to_slot: int | None = None

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "slot": self.slot,
            "role": self.role,
            "quantity": format_decimal(self.quantity),
            "instrument_claim_refs": _sorted_texts(self.instrument_claim_refs),
            "location_claim_ref": self.location_claim_ref,
            "subtype": self.subtype,
            "attributed_to_slot": self.attributed_to_slot,
        }


def _is_set(value: object) -> bool:
    if value in ("", (), None):
        return False
    return True


@dataclass(frozen=True)
class ClaimRecord:
    claim_set_id: str
    scope_id: str
    bundle_id: str
    claim_id: str
    kind: ClaimKind
    status: ClaimRecordStatus
    key: tuple[str, ...]
    member_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]
    effective_at: datetime | None
    precision: TemporalPrecision | None
    provenance_refs: tuple[str, ...]
    activity_label: str = ""
    location_claim_ref: str = ""
    leg_specs: tuple[ClaimLegSpec, ...] = ()
    instrument_claim_refs: tuple[str, ...] = ()
    balance_kind: str = ""
    quantity: Decimal | None = None
    observed_at: datetime | None = None
    scheme: str = ""
    value: str = ""
    venue: str = ""
    instrument_kind: str = ""
    name: str = ""
    location_ref: str = ""
    location_group_label: str = ""
    location_label: str = ""
    beneficial_owner_ref: str = ""
    purpose: str = ""
    amount: Decimal | None = None
    currency: str = ""
    valued_at: datetime | None = None

    def __post_init__(self) -> None:
        self._validate_kind_fields()

    def _validate_kind_fields(self) -> None:
        balance_fields = (
            self.instrument_claim_refs,
            self.balance_kind,
            self.quantity,
            self.observed_at,
        )
        instrument_fields = (
            self.scheme,
            self.value,
            self.venue,
            self.instrument_kind,
            self.name,
        )
        location_fields = (
            self.location_ref,
            self.location_group_label,
            self.location_label,
        )
        beneficial_owner_fields = (self.beneficial_owner_ref,)
        valuation_fields = (self.purpose, self.amount, self.currency, self.valued_at)
        if self.kind is ClaimKind.ACTIVITY and any(
            _is_set(value)
            for value in (
                *balance_fields,
                *instrument_fields,
                *location_fields,
                *beneficial_owner_fields,
                *valuation_fields,
            )
        ):
            raise ValueError("activity claims must not set balance fields")
        if self.kind is ClaimKind.BALANCE and not all(
            (
                self.location_claim_ref,
                self.instrument_claim_refs,
                self.balance_kind,
                self.quantity is not None,
                self.observed_at is not None,
                self.precision is not None,
            )
        ):
            raise ValueError(
                "balance claims require location, instrument, quantity, observed_at, and precision"
            )
        if self.kind is ClaimKind.INSTRUMENT and not all(
            (self.scheme, self.value, self.instrument_kind)
        ):
            raise ValueError(
                "instrument claims require scheme, value, and instrument_kind"
            )
        if self.kind is ClaimKind.LOCATION and not self.location_ref:
            raise ValueError("location claims require location_ref")
        if self.kind is ClaimKind.BENEFICIAL_OWNER and not self.beneficial_owner_ref:
            raise ValueError("beneficial_owner claims require beneficial_owner_ref")
        if self.kind is ClaimKind.VALUATION and not all(
            (
                self.purpose,
                self.amount is not None,
                self.currency,
                self.valued_at is not None,
                self.location_claim_ref,
                self.instrument_claim_refs,
            )
        ):
            raise ValueError(
                "valuation claims require purpose, amount, currency, valued_at, location, and instruments"
            )

    def semantic_payload(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "kind": self.kind.value,
            "status": self.status.value,
            "key": list(self.key),
            "member_refs": _sorted_texts(self.member_refs),
            "observation_refs": _sorted_texts(self.observation_refs),
            "effective_at": _optional_temporal(
                self.effective_at,
                precision=self.precision,
                label="claim effective_at",
            ),
            "precision": "" if self.precision is None else self.precision.value,
            "provenance_refs": _sorted_texts(self.provenance_refs),
        }
        if self.kind is ClaimKind.ACTIVITY:
            payload.update(
                {
                    "activity_label": self.activity_label,
                    "location_claim_ref": self.location_claim_ref,
                    "leg_specs": [
                        spec.to_payload()
                        for spec in sorted(self.leg_specs, key=lambda item: item.slot)
                    ],
                }
            )
        elif self.kind is ClaimKind.BALANCE:
            payload.update(
                {
                    "location_claim_ref": self.location_claim_ref,
                    "instrument_claim_refs": _sorted_texts(self.instrument_claim_refs),
                    "balance_kind": self.balance_kind,
                    "quantity": format_decimal(self.quantity),
                    "observed_at": _optional_temporal(
                        self.observed_at,
                        precision=self.precision,
                        label="claim observed_at",
                    ),
                }
            )
        elif self.kind is ClaimKind.INSTRUMENT:
            payload.update(
                {
                    "scheme": self.scheme,
                    "value": self.value,
                    "venue": self.venue,
                    "instrument_kind": self.instrument_kind,
                    "name": self.name,
                }
            )
        elif self.kind is ClaimKind.LOCATION:
            payload.update(
                {
                    "location_ref": self.location_ref,
                    "location_group_label": self.location_group_label,
                    "location_label": self.location_label,
                }
            )
        elif self.kind is ClaimKind.BENEFICIAL_OWNER:
            payload["beneficial_owner_ref"] = self.beneficial_owner_ref
        elif self.kind is ClaimKind.VALUATION:
            payload.update(
                {
                    "purpose": self.purpose,
                    "amount": format_decimal(self.amount),
                    "currency": self.currency,
                    "valued_at": _optional_temporal(
                        self.valued_at,
                        precision=self.precision,
                        label="claim valued_at",
                    ),
                    "location_claim_ref": self.location_claim_ref,
                    "instrument_claim_refs": _sorted_texts(self.instrument_claim_refs),
                }
            )
        return payload

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "claim_set_id": self.claim_set_id,
            "scope_id": self.scope_id,
            "bundle_id": self.bundle_id,
            "claim_id": self.claim_id,
            **self.semantic_payload(),
        }


@dataclass(frozen=True)
class ClaimBundleRecord:
    claim_set_id: str
    scope_id: str
    bundle_id: str
    key: str
    scope_key: tuple[str, ...]
    claim_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "claim_set_id": self.claim_set_id,
            "scope_id": self.scope_id,
            "bundle_id": self.bundle_id,
            "key": self.key,
            "scope_key": list(self.scope_key),
            "claim_refs": _sorted_texts(self.claim_refs),
        }


@dataclass(frozen=True)
class ClaimBundleDecisionRecord:
    claim_set_id: str
    scope_id: str
    decision_id: str
    outcome: ClaimBundleDecisionOutcome
    accepted_bundle_ref: str
    rejected_bundle_refs: tuple[str, ...]
    deferred_bundle_refs: tuple[str, ...]
    basis: ClaimBundleDecisionBasis
    blocking_gap_refs: tuple[str, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "claim_set_id": self.claim_set_id,
            "scope_id": self.scope_id,
            "decision_id": self.decision_id,
            "outcome": self.outcome.value,
            "accepted_bundle_ref": self.accepted_bundle_ref,
            "rejected_bundle_refs": _sorted_texts(self.rejected_bundle_refs),
            "deferred_bundle_refs": _sorted_texts(self.deferred_bundle_refs),
            "basis": self.basis.value,
            "blocking_gap_refs": _sorted_texts(self.blocking_gap_refs),
        }


def canonical_claim_records(
    records: tuple[ClaimRecord, ...],
) -> tuple[ClaimRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.bundle_id,
                item.kind.value,
                _optional_temporal(
                    item.effective_at, precision=item.precision, label="claim sort"
                ),
                "" if item.precision is None else item.precision.value,
                item.claim_id,
            ),
        )
    )


def canonical_claim_bundle_records(
    records: tuple[ClaimBundleRecord, ...],
) -> tuple[ClaimBundleRecord, ...]:
    return tuple(
        sorted(records, key=lambda item: (item.scope_id, item.key, item.bundle_id))
    )


def canonical_claim_bundle_decision_records(
    records: tuple[ClaimBundleDecisionRecord, ...],
) -> tuple[ClaimBundleDecisionRecord, ...]:
    return tuple(sorted(records, key=lambda item: (item.scope_id, item.decision_id)))


@dataclass(frozen=True)
class ClaimSet:
    claim_set_id: str
    evidence_set_ref: str
    emitter_id: str
    claim_records: tuple[ClaimRecord, ...]
    claim_bundle_records: tuple[ClaimBundleRecord, ...]
    claim_bundle_decision_records: tuple[ClaimBundleDecisionRecord, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "claim_set_id": self.claim_set_id,
            "schema_version": CLAIM_SET_SCHEMA_VERSION,
            "evidence_set_ref": self.evidence_set_ref,
            "emitter_id": self.emitter_id,
            "claim_records": [
                record.to_payload()
                for record in canonical_claim_records(self.claim_records)
            ],
            "claim_bundle_records": [
                record.to_payload()
                for record in canonical_claim_bundle_records(self.claim_bundle_records)
            ],
            "claim_bundle_decision_records": [
                record.to_payload()
                for record in canonical_claim_bundle_decision_records(
                    self.claim_bundle_decision_records
                )
            ],
        }


def stable_claim_set_id(*, evidence_set_id: str, emitter_id: str) -> str:
    return ":".join((evidence_set_id, emitter_id))


def stable_claim_scope_id(*, claim_set_id: str, scope_key: tuple[str, ...]) -> str:
    return ":".join((claim_set_id, *scope_key))


def stable_claim_bundle_id(*, scope_id: str, key: str) -> str:
    return ":".join((scope_id, key))


def stable_claim_id(*, bundle_id: str, kind: ClaimKind, key: tuple[str, ...]) -> str:
    return ":".join((bundle_id, kind.value, *key))


def stable_claim_bundle_decision_id(*, scope_id: str) -> str:
    return scope_id


def claim_set_fingerprint(claim_set: ClaimSet) -> str:
    return _hash_payload(cast(JsonValue, claim_set.to_payload()))
