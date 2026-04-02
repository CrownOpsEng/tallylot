"""Validation helpers for transaction fact models."""

from __future__ import annotations

from typing import Literal, Protocol, TypeGuard, cast, get_args

FactDirection = Literal["in", "out"]


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
    def max_in_count(self) -> int | None: ...

    @property
    def min_in_count(self) -> int | None: ...

    @property
    def max_out_count(self) -> int | None: ...

    @property
    def min_out_count(self) -> int | None: ...


class _FactLegPolicyLike(Protocol):
    @property
    def limits(self) -> tuple[_LegShapeLimitLike, ...]: ...


class _EconomicLegLike(Protocol):
    @property
    def direction(self) -> FactDirection: ...

    @property
    def kind(self) -> _KindLike: ...

    @property
    def attributed_to_direction(self) -> FactDirection | None: ...


_FACT_DIRECTIONS = cast(tuple[FactDirection, ...], get_args(FactDirection))


def validate_non_negative_count(value: int, *, label: str) -> None:
    if value < 0:
        raise ValueError(f"leg shape limit {label} must be non-negative")


def _validate_optional_non_negative_count(value: int | None, *, label: str) -> None:
    if value is None:
        return
    validate_non_negative_count(value, label=label)


def _validate_optional_within_max(value: int | None, *, label: str, max_count: int) -> None:
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


def validate_directional_counts(limit: _LegShapeLimitLike) -> None:
    _validate_optional_non_negative_count(limit.min_in_count, label="min_in_count")
    _validate_optional_non_negative_count(limit.max_in_count, label="max_in_count")
    _validate_optional_non_negative_count(limit.min_out_count, label="min_out_count")
    _validate_optional_non_negative_count(limit.max_out_count, label="max_out_count")
    _validate_optional_within_max(limit.min_in_count, label="min_in_count", max_count=limit.max_count)
    _validate_optional_within_max(limit.max_in_count, label="max_in_count", max_count=limit.max_count)
    _validate_optional_within_max(limit.min_out_count, label="min_out_count", max_count=limit.max_count)
    _validate_optional_within_max(limit.max_out_count, label="max_out_count", max_count=limit.max_count)
    _validate_optional_min_max(
        limit.min_in_count,
        limit.max_in_count,
        min_label="min_in_count",
        max_label="max_in_count",
    )
    _validate_optional_min_max(
        limit.min_out_count,
        limit.max_out_count,
        min_label="min_out_count",
        max_label="max_out_count",
    )
    if limit.min_in_count is None or limit.min_out_count is None:
        return
    if limit.min_in_count + limit.min_out_count > limit.max_count:
        raise ValueError("leg shape limit directional minimum counts must not exceed max_count")


def fact_leg_counts(
    legs: tuple[_EconomicLegLike, ...],
    policy: _FactLegPolicyLike,
) -> tuple[
    dict[str, int],
    dict[tuple[str, FactDirection], int],
    dict[FactDirection, int],
]:
    counts_by_kind: dict[str, int] = {}
    directional_counts: dict[tuple[str, FactDirection], int] = {}
    primary_legs_by_direction: dict[FactDirection, int] = {"in": 0, "out": 0}
    for leg in legs:
        kind_key = leg.kind.value
        _validate_policy_kind_allowed(policy, kind_key)
        counts_by_kind[kind_key] = counts_by_kind.get(kind_key, 0) + 1
        directional_key = (kind_key, leg.direction)
        directional_counts[directional_key] = directional_counts.get(directional_key, 0) + 1
        if kind_key == "primary":
            primary_legs_by_direction[leg.direction] += 1
    return counts_by_kind, directional_counts, primary_legs_by_direction


def _validate_policy_kind_allowed(policy: _FactLegPolicyLike, kind_value: str) -> None:
    if any(limit.kind.value == kind_value for limit in policy.limits):
        return
    raise ValueError(f"transaction fact leg kind {kind_value} is not allowed by declared leg policy")


def validate_fact_counts(
    policy: _FactLegPolicyLike,
    counts_by_kind: dict[str, int],
    directional_counts: dict[tuple[str, FactDirection], int],
) -> None:
    for limit in policy.limits:
        kind_key = limit.kind.value
        _validate_fact_total_count(limit, counts_by_kind.get(kind_key, 0))
        _validate_fact_directional_count(limit, "in", directional_counts.get((kind_key, "in"), 0))
        _validate_fact_directional_count(limit, "out", directional_counts.get((kind_key, "out"), 0))


def _validate_fact_total_count(limit: _LegShapeLimitLike, total_count: int) -> None:
    if total_count < limit.min_count:
        raise ValueError(f"transaction fact {limit.kind.value} legs fall below declared leg policy")
    if total_count > limit.max_count:
        raise ValueError(f"transaction fact {limit.kind.value} legs exceed declared leg policy")


def _validate_fact_directional_count(limit: _LegShapeLimitLike, direction: FactDirection, count: int) -> None:
    min_count = limit.min_in_count if direction == "in" else limit.min_out_count
    max_count = limit.max_in_count if direction == "in" else limit.max_out_count
    direction_label = "inbound" if direction == "in" else "outbound"
    if min_count is not None and count < min_count:
        raise ValueError(f"transaction fact {direction_label} {limit.kind.value} legs fall below declared leg policy")
    if max_count is not None and count > max_count:
        raise ValueError(f"transaction fact {direction_label} {limit.kind.value} legs exceed declared leg policy")


def validate_fact_leg_attribution(
    legs: tuple[_EconomicLegLike, ...],
    primary_legs_by_direction: dict[FactDirection, int],
) -> None:
    for leg in legs:
        if leg.attributed_to_direction is None:
            continue
        if primary_legs_by_direction[leg.attributed_to_direction] != 1:
            raise ValueError(
                "transaction fact attributed_to_direction must reference exactly one primary leg on that side"
            )


def validate_fact_direction(value: str, *, label: str) -> FactDirection:
    if not _is_fact_direction(value):
        raise ValueError(f"unsupported {label}: {value}")
    return value


def _is_fact_direction(value: str) -> TypeGuard[FactDirection]:
    return value in _FACT_DIRECTIONS
