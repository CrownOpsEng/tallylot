"""Shared transaction fact leg-shape policies."""

from __future__ import annotations

from .models import FactLegPolicy, LegKind, LegShapeLimit

SINGLE_PRIMARY_ACTIVITY_POLICY = FactLegPolicy(
    limits=(LegShapeLimit(kind=LegKind.PRIMARY, min_count=1, max_count=1, max_in_count=1, max_out_count=1),)
)
TWO_SIDED_PRIMARY_EXCHANGE_POLICY = FactLegPolicy(
    limits=(
        LegShapeLimit(
            kind=LegKind.PRIMARY,
            min_count=2,
            max_count=2,
            min_in_count=1,
            max_in_count=1,
            min_out_count=1,
            max_out_count=1,
        ),
    )
)
TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY = FactLegPolicy(
    limits=(
        LegShapeLimit(
            kind=LegKind.PRIMARY,
            min_count=2,
            max_count=2,
            min_in_count=1,
            max_in_count=1,
            min_out_count=1,
            max_out_count=1,
        ),
        LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
    )
)
