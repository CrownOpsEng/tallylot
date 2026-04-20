"""Shared decimal precision validation helpers for source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tallylot.domain.value_objects import parse_decimal


@dataclass(frozen=True)
class DecimalPrecisionExpectation:
    minimum_fraction_digits: int | None = None
    exact_fraction_digits: int | None = None
    allow_zero: bool = False

    def __post_init__(self) -> None:
        uses_minimum = self.minimum_fraction_digits is not None
        uses_exact = self.exact_fraction_digits is not None
        if uses_minimum == uses_exact:
            raise ValueError(
                "decimal precision expectation requires exactly one of minimum_fraction_digits or exact_fraction_digits"
            )
        if (
            self.minimum_fraction_digits is not None
            and self.minimum_fraction_digits < 0
        ):
            raise ValueError("minimum_fraction_digits must be non-negative")
        if self.exact_fraction_digits is not None and self.exact_fraction_digits < 0:
            raise ValueError("exact_fraction_digits must be non-negative")

    def describe(self) -> str:
        if self.minimum_fraction_digits is not None:
            requirement = f"at least {self.minimum_fraction_digits} fractional digits"
        else:
            assert self.exact_fraction_digits is not None
            requirement = f"exactly {self.exact_fraction_digits} fractional digits"
        if self.allow_zero:
            return f"{requirement} for non-zero values"
        return requirement


@dataclass(frozen=True)
class DecimalPrecisionCheck:
    value_text: str
    value: Decimal
    fraction_digits: int
    expectation: DecimalPrecisionExpectation
    satisfies_expectation: bool

    @property
    def mismatch_message(self) -> str:
        return f"has {self.fraction_digits} fractional digits; expected {self.expectation.describe()}"


def decimal_fraction_digits(value_text: str) -> int | None:
    normalized = value_text.strip()
    parsed = parse_decimal(normalized)
    if parsed is None:
        return None
    unsigned = normalized.removeprefix("+").removeprefix("-")
    mantissa = unsigned.split("e", 1)[0].split("E", 1)[0]
    if "." not in mantissa:
        return 0
    return len(mantissa.split(".", 1)[1])


def check_decimal_precision(
    value_text: str,
    *,
    expectation: DecimalPrecisionExpectation,
) -> DecimalPrecisionCheck | None:
    normalized = value_text.strip()
    if not normalized:
        return None
    value = parse_decimal(normalized)
    if value is None:
        return None
    fraction_digits = decimal_fraction_digits(normalized)
    if fraction_digits is None:
        return None
    if value == Decimal("0") and expectation.allow_zero:
        satisfies_expectation = True
    elif expectation.minimum_fraction_digits is not None:
        satisfies_expectation = fraction_digits >= expectation.minimum_fraction_digits
    else:
        assert expectation.exact_fraction_digits is not None
        satisfies_expectation = fraction_digits == expectation.exact_fraction_digits
    return DecimalPrecisionCheck(
        value_text=normalized,
        value=value,
        fraction_digits=fraction_digits,
        expectation=expectation,
        satisfies_expectation=satisfies_expectation,
    )
