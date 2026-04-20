"""Instrument identity and registry records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

InstrumentId = NewType("InstrumentId", str)

_IDENTIFIER_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class InstrumentKind(StrEnum):
    UNKNOWN = "unknown"
    CRYPTO = "crypto"
    FIAT = "fiat"
    EQUITY = "equity"
    DERIVATIVE = "derivative"


@dataclass(frozen=True)
class InstrumentRecord:
    instrument_id: InstrumentId
    kind: InstrumentKind
    display_name: str
    precision: int | None = None

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("instrument_id must not be blank")
        if not self.display_name.strip():
            raise ValueError("instrument display_name must not be blank")
        if self.precision is not None and self.precision < 0:
            raise ValueError("instrument precision must be non-negative")


@dataclass(frozen=True)
class InstrumentIdentifierRecord:
    instrument_id: InstrumentId
    scheme: str
    value: str
    venue: str | None = None

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("instrument identifier instrument_id must not be blank")
        _validate_identifier_scheme(self.scheme)
        if not self.value.strip():
            raise ValueError("instrument identifier value must not be blank")


@dataclass(frozen=True)
class InstrumentIdentityClaim:
    scheme: str
    value: str
    venue: str | None = None
    kind_hint: InstrumentKind = InstrumentKind.UNKNOWN
    display_name: str = ""
    precision_hint: int | None = None

    def __post_init__(self) -> None:
        _validate_identifier_scheme(self.scheme)
        if not self.value.strip():
            raise ValueError("instrument identity claim value must not be blank")
        if self.precision_hint is not None and self.precision_hint < 0:
            raise ValueError(
                "instrument identity claim precision_hint must be non-negative"
            )


def _validate_identifier_scheme(value: str) -> None:
    if not _IDENTIFIER_SCHEME_PATTERN.fullmatch(value):
        raise ValueError("instrument identifier scheme must be lowercase snake_case")
