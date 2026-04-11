"""Ronin explorer draft construction rules."""

from __future__ import annotations

from decimal import Decimal

from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    EconomicActivityDraft,
    EconomicLegDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.types import LocationId
from tallylot.ports.source_profiles import SourceProfile

from .rows import (
    ZERO,
    RoninRawDraftContext,
    RoninRawRow,
    RoninSummaryRow,
    SummaryDraftContext,
    ronin_location_id,
    staking_in_semantics,
    staking_out_semantics,
    staking_reward_semantics,
    transfer_in_semantics,
    transfer_out_semantics,
)


def simple_transfer_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> EconomicActivityDraft | None:
    if (
        row.inbound_quantity > Decimal("0")
        and row.outbound_quantity == Decimal("0")
        and row.to_address in owned_addresses
    ):
        return _transfer_draft(
            row=row,
            quantity=row.inbound_quantity,
            context=RoninRawDraftContext(
                source=str(profile.source),
                location_id=ronin_location_id(row.to_address),
                semantics=transfer_in_semantics(),
                fee=authoritative_fee,
            ),
        )
    if (
        row.outbound_quantity > Decimal("0")
        and row.inbound_quantity == Decimal("0")
        and row.from_address in owned_addresses
    ):
        return _transfer_draft(
            row=row,
            quantity=-row.outbound_quantity,
            context=RoninRawDraftContext(
                source=str(profile.source),
                location_id=ronin_location_id(row.from_address),
                semantics=transfer_out_semantics(),
                fee=authoritative_fee,
            ),
        )
    return None


def _transfer_draft(
    *,
    row: RoninRawRow,
    quantity: Decimal,
    context: RoninRawDraftContext,
) -> EconomicActivityDraft:
    primary_leg_id = "primary_in" if quantity > Decimal("0") else "primary_out"
    return EconomicActivityDraft(
        activity_id=f"ronin:{row.path_name}:{row.tx_hash}",
        source=context.source,
        adapter_id="ronin",
        location_id=context.location_id,
        timestamp=row.timestamp,
        classification=context.semantics.to_classification(),
        leg_policy=_single_primary_with_optional_fee_policy(context.fee),
        description=f"Ronin {row.method} - {row.tx_hash}",
        raw_file=row.path_name,
        raw_row_ref=row.raw_row_ref,
        tx_hash=row.tx_hash,
        provider_operation_key=row.method,
        legs=(
            economic_leg(
                leg_id=primary_leg_id,
                kind=LegKind.PRIMARY,
                quantity=quantity,
                instrument=symbol_claim(row.asset_symbol, venue="ronin"),
            ),
            *_fee_legs(context.fee, attributed_to_leg_id=primary_leg_id),
        ),
    )


def staking_transfer_out_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
    fee: Decimal = ZERO,
) -> EconomicActivityDraft:
    return _transfer_draft(
        row=row,
        quantity=-row.outbound_quantity,
        context=RoninRawDraftContext(
            source=str(profile.source),
            location_id=location_id,
            semantics=staking_out_semantics(),
            fee=fee,
        ),
    )


def staking_reward_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
    fee: Decimal = ZERO,
) -> EconomicActivityDraft:
    return _transfer_draft(
        row=row,
        quantity=row.inbound_quantity,
        context=RoninRawDraftContext(
            source=str(profile.source),
            location_id=location_id,
            semantics=staking_reward_semantics(),
            fee=fee,
        ),
    )


def staking_transfer_in_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
    fee: Decimal = ZERO,
) -> EconomicActivityDraft:
    return _transfer_draft(
        row=row,
        quantity=row.inbound_quantity,
        context=RoninRawDraftContext(
            source=str(profile.source),
            location_id=location_id,
            semantics=staking_in_semantics(),
            fee=fee,
        ),
    )


def summary_transfer_draft(
    profile: SourceProfile,
    row: RoninSummaryRow,
    context: SummaryDraftContext,
) -> EconomicActivityDraft:
    primary_leg_id = "primary_in" if context.quantity > Decimal("0") else "primary_out"
    return EconomicActivityDraft(
        activity_id=f"ronin:{row.path_name}:{row.tx_hash}:{row.row_index}",
        source=str(profile.source),
        adapter_id="ronin",
        location_id=context.location_id,
        timestamp=context.timestamp,
        classification=context.semantics.to_classification(),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=f"Ronin {row.action_type} - {row.tx_hash}",
        raw_file=row.path_name,
        raw_row_ref=row.raw_row_ref,
        tx_hash=row.tx_hash,
        provider_operation_key=row.action_type,
        legs=(
            economic_leg(
                leg_id=primary_leg_id,
                kind=LegKind.PRIMARY,
                quantity=context.quantity,
                instrument=symbol_claim(row.asset_symbol, venue="ronin"),
            ),
        ),
    )


def raw_restake_pair_drafts(
    profile: SourceProfile,
    raw_rows: tuple[RoninRawRow, ...],
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[EconomicActivityDraft, ...] | None:
    if len(raw_rows) != 2:
        return None
    reward_row = next(
        (
            row
            for row in raw_rows
            if row.inbound_quantity > Decimal("0")
            and row.outbound_quantity == Decimal("0")
            and row.to_address in owned_addresses
        ),
        None,
    )
    stake_row = next(
        (
            row
            for row in raw_rows
            if row.outbound_quantity > Decimal("0")
            and row.inbound_quantity == Decimal("0")
            and row.from_address in owned_addresses
        ),
        None,
    )
    if reward_row is None or stake_row is None:
        return None
    if reward_row.asset_symbol != stake_row.asset_symbol:
        return None
    return (
        staking_reward_draft(
            profile,
            reward_row,
            location_id=ronin_location_id(reward_row.to_address),
        ),
        staking_transfer_out_draft(
            profile,
            stake_row,
            location_id=ronin_location_id(stake_row.from_address),
            fee=authoritative_fee,
        ),
    )


def _single_primary_with_optional_fee_policy(fee: Decimal) -> FactLegPolicy:
    if fee <= Decimal("0"):
        return SINGLE_PRIMARY_ACTIVITY_POLICY
    return FactLegPolicy(
        limits=(
            LegShapeLimit(
                kind=LegKind.PRIMARY,
                max_count=1,
                max_positive_count=1,
                max_negative_count=1,
            ),
            LegShapeLimit(
                kind=LegKind.CHARGE,
                max_count=1,
                max_positive_count=0,
                max_negative_count=1,
            ),
        )
    )


def _fee_legs(
    fee: Decimal,
    *,
    attributed_to_leg_id: str,
) -> tuple[EconomicLegDraft, ...]:
    if fee <= Decimal("0"):
        return ()
    return (
        economic_leg(
            leg_id="charge",
            kind=LegKind.CHARGE,
            quantity=-fee,
            instrument=symbol_claim("RON", venue="ronin"),
            subtype="network_fee",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )
