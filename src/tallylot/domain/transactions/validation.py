"""Validation helpers for transaction fact models."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class _KindLike(Protocol):
    @property
    def value(self) -> str: ...


class _LegShapeLimitLike(Protocol):
    @property
    def kind(self) -> _KindLike: ...

    @property
    def max_count(self) -> int: ...

    @property
    def min_count(self) -> int: ...

    @property
    def max_positive_count(self) -> int | None: ...

    @property
    def min_positive_count(self) -> int | None: ...

    @property
    def max_negative_count(self) -> int | None: ...

    @property
    def min_negative_count(self) -> int | None: ...


class _FactLegPolicyLike(Protocol):
    @property
    def limits(self) -> tuple[_LegShapeLimitLike, ...]: ...


class _EconomicLegLike(Protocol):
    @property
    def leg_id(self) -> str: ...

    @property
    def kind(self) -> _KindLike: ...

    @property
    def quantity(self) -> Decimal: ...

    @property
    def attributed_to_leg_id(self) -> str | None: ...


def validate_non_negative_count(value: int, *, label: str) -> None:
    if value < 0:
        raise ValueError(f"leg shape limit {label} must be non-negative")


def _validate_optional_non_negative_count(value: int | None, *, label: str) -> None:
    if value is None:
        return
    validate_non_negative_count(value, label=label)


def _validate_optional_within_max(
    value: int | None, *, label: str, max_count: int
) -> None:
    if value is None:
        return
    if value > max_count:
        raise ValueError(f"leg shape limit {label} must not exceed max_count")


def _validate_optional_min_max(
    minimum: int | None,
    maximum: int | None,
    *,
    min_label: str,
    max_label: str,
) -> None:
    if minimum is None or maximum is None:
        return
    if minimum > maximum:
        raise ValueError(f"leg shape limit {min_label} must not exceed {max_label}")


def validate_leg_shape_counts(limit: _LegShapeLimitLike) -> None:
    _validate_optional_non_negative_count(
        limit.min_positive_count, label="min_positive_count"
    )
    _validate_optional_non_negative_count(
        limit.max_positive_count, label="max_positive_count"
    )
    _validate_optional_non_negative_count(
        limit.min_negative_count, label="min_negative_count"
    )
    _validate_optional_non_negative_count(
        limit.max_negative_count, label="max_negative_count"
    )
    _validate_optional_within_max(
        limit.min_positive_count, label="min_positive_count", max_count=limit.max_count
    )
    _validate_optional_within_max(
        limit.max_positive_count, label="max_positive_count", max_count=limit.max_count
    )
    _validate_optional_within_max(
        limit.min_negative_count, label="min_negative_count", max_count=limit.max_count
    )
    _validate_optional_within_max(
        limit.max_negative_count, label="max_negative_count", max_count=limit.max_count
    )
    _validate_optional_min_max(
        limit.min_positive_count,
        limit.max_positive_count,
        min_label="min_positive_count",
        max_label="max_positive_count",
    )
    _validate_optional_min_max(
        limit.min_negative_count,
        limit.max_negative_count,
        min_label="min_negative_count",
        max_label="max_negative_count",
    )
    if limit.min_positive_count is None or limit.min_negative_count is None:
        return
    if limit.min_positive_count + limit.min_negative_count > limit.max_count:
        raise ValueError(
            "leg shape limit signed minimum counts must not exceed max_count"
        )


def fact_leg_counts(
    legs: tuple[_EconomicLegLike, ...],
    policy: _FactLegPolicyLike,
) -> tuple[
    dict[str, int],
    dict[tuple[str, str], int],
    dict[str, str],
]:
    counts_by_kind: dict[str, int] = {}
    signed_counts: dict[tuple[str, str], int] = {}
    leg_ids_by_kind: dict[str, str] = {}
    seen_leg_ids: set[str] = set()
    for leg in legs:
        kind_key = leg.kind.value
        _validate_policy_kind_allowed(policy, kind_key)
        if leg.leg_id in seen_leg_ids:
            raise ValueError(f"transaction fact duplicates leg_id {leg.leg_id}")
        seen_leg_ids.add(leg.leg_id)
        counts_by_kind[kind_key] = counts_by_kind.get(kind_key, 0) + 1
        sign_key = "positive" if leg.quantity > Decimal("0") else "negative"
        signed_count_key = (kind_key, sign_key)
        signed_counts[signed_count_key] = signed_counts.get(signed_count_key, 0) + 1
        if kind_key == "primary":
            leg_ids_by_kind[leg.leg_id] = kind_key
    return counts_by_kind, signed_counts, leg_ids_by_kind


def _validate_policy_kind_allowed(policy: _FactLegPolicyLike, kind_value: str) -> None:
    if any(limit.kind.value == kind_value for limit in policy.limits):
        return
    raise ValueError(
        f"transaction fact leg kind {kind_value} is not allowed by declared leg policy"
    )


def validate_fact_counts(
    policy: _FactLegPolicyLike,
    counts_by_kind: dict[str, int],
    signed_counts: dict[tuple[str, str], int],
) -> None:
    for limit in policy.limits:
        kind_key = limit.kind.value
        _validate_fact_total_count(limit, counts_by_kind.get(kind_key, 0))
        _validate_fact_signed_count(
            limit, "positive", signed_counts.get((kind_key, "positive"), 0)
        )
        _validate_fact_signed_count(
            limit, "negative", signed_counts.get((kind_key, "negative"), 0)
        )


def _validate_fact_total_count(limit: _LegShapeLimitLike, total_count: int) -> None:
    if total_count < limit.min_count:
        raise ValueError(
            f"transaction fact {limit.kind.value} legs fall below declared leg policy"
        )
    if total_count > limit.max_count:
        raise ValueError(
            f"transaction fact {limit.kind.value} legs exceed declared leg policy"
        )


def _validate_fact_signed_count(
    limit: _LegShapeLimitLike, sign: str, count: int
) -> None:
    min_count = (
        limit.min_positive_count if sign == "positive" else limit.min_negative_count
    )
    max_count = (
        limit.max_positive_count if sign == "positive" else limit.max_negative_count
    )
    sign_label = "positive" if sign == "positive" else "negative"
    if min_count is not None and count < min_count:
        raise ValueError(
            f"transaction fact {sign_label} {limit.kind.value} legs fall below declared leg policy"
        )
    if max_count is not None and count > max_count:
        raise ValueError(
            f"transaction fact {sign_label} {limit.kind.value} legs exceed declared leg policy"
        )


def validate_fact_leg_attribution(
    legs: tuple[_EconomicLegLike, ...],
    leg_ids_by_kind: dict[str, str],
) -> None:
    for leg in legs:
        if leg.attributed_to_leg_id is None:
            continue
        if leg.attributed_to_leg_id not in leg_ids_by_kind:
            raise ValueError(
                "transaction fact attributed_to_leg_id must reference one primary leg in the same fact"
            )
