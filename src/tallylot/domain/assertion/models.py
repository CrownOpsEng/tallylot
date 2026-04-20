"""Target assertion value models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
from typing import TypeAlias, cast

from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import format_decimal

SubjectRef: TypeAlias = tuple[str, tuple[object, ...]]


def _json_text(payload: JsonValue) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _json_ready(value: object) -> JsonValue:
    if isinstance(value, tuple):
        tuple_items = cast(tuple[object, ...], value)
        return [_json_ready(item) for item in tuple_items]
    if isinstance(value, list):
        list_items = cast(list[object], value)
        return [_json_ready(item) for item in list_items]
    if isinstance(value, dict):
        dict_items = cast(dict[object, object], value)
        return {str(key): _json_ready(item) for key, item in dict_items.items()}
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise ValueError(f"unsupported JSON value in assertion payload: {value!r}")


def _subject_ref_payload(subject_ref: SubjectRef) -> list[JsonValue]:
    kind, key = subject_ref
    return [kind, _json_ready(key)]


@dataclass(frozen=True)
class QuantityValue:
    quantity: Decimal
    subject_ref: SubjectRef

    @property
    def assertion_value_kind(self) -> str:
        return "quantity"

    def value_content(self) -> list[JsonValue]:
        return [format_decimal(self.quantity), _subject_ref_payload(self.subject_ref)]

    def canonical_tuple(self) -> tuple[object, object]:
        return (
            self.assertion_value_kind,
            tuple(self.value_content()),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "assertion_value_kind": self.assertion_value_kind,
            "quantity": format_decimal(self.quantity),
            "subject_ref": _subject_ref_payload(self.subject_ref),
        }


@dataclass(frozen=True)
class MoneyValue:
    amount: Decimal
    currency: str

    @property
    def assertion_value_kind(self) -> str:
        return "money"

    def value_content(self) -> list[JsonValue]:
        return [format_decimal(self.amount), self.currency]

    def canonical_tuple(self) -> tuple[object, object]:
        return (
            self.assertion_value_kind,
            tuple(self.value_content()),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "assertion_value_kind": self.assertion_value_kind,
            "amount": format_decimal(self.amount),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class OwnerValue:
    legal_owner_ref: str = ""
    beneficial_owner_ref: str = ""
    counterparty_ref: str = ""

    @property
    def assertion_value_kind(self) -> str:
        return "owner"

    def __post_init__(self) -> None:
        if not any(
            (self.legal_owner_ref, self.beneficial_owner_ref, self.counterparty_ref)
        ):
            raise ValueError("owner value requires at least one owner reference")

    def value_content(self) -> list[JsonValue]:
        return [
            self.legal_owner_ref,
            self.beneficial_owner_ref,
            self.counterparty_ref,
        ]

    def canonical_tuple(self) -> tuple[object, object]:
        return (
            self.assertion_value_kind,
            tuple(self.value_content()),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "assertion_value_kind": self.assertion_value_kind,
            "legal_owner_ref": self.legal_owner_ref,
            "beneficial_owner_ref": self.beneficial_owner_ref,
            "counterparty_ref": self.counterparty_ref,
        }


@dataclass(frozen=True)
class LocationValue:
    location_ref: str

    @property
    def assertion_value_kind(self) -> str:
        return "location"

    def __post_init__(self) -> None:
        if not self.location_ref:
            raise ValueError("location value requires location_ref")

    def value_content(self) -> list[JsonValue]:
        return [self.location_ref]

    def canonical_tuple(self) -> tuple[object, object]:
        return (
            self.assertion_value_kind,
            tuple(self.value_content()),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "assertion_value_kind": self.assertion_value_kind,
            "location_ref": self.location_ref,
        }


AssertionValue: TypeAlias = QuantityValue | MoneyValue | OwnerValue | LocationValue


def assertion_value_payload(value: AssertionValue) -> list[JsonValue]:
    return [value.assertion_value_kind, value.value_content()]


def assertion_value_json(value: AssertionValue) -> str:
    return _json_text(assertion_value_payload(value))


def assertion_value_fingerprint(value: AssertionValue) -> str:
    return sha256(assertion_value_json(value).encode("utf-8")).hexdigest()
