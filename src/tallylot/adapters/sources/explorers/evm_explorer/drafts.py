"""EVM explorer draft construction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    ActivitySemantics,
    EconomicActivityDraft,
    LegKind,
    economic_leg,
)
from tallylot.domain.instruments import InstrumentIdentityClaim
from tallylot.domain.types import LocationId
from tallylot.ports.source_profiles import SourceProfile


@dataclass(frozen=True)
class EvmDraftContext:
    path_name: str
    row_index: int
    tx_hash: str
    timestamp: datetime
    location_id: LocationId
    quantity: Decimal
    instrument: InstrumentIdentityClaim


def location_id_from_identifier(
    identifier_kind: str,
    identifier_value: str,
    *,
    network_scope: str = "",
) -> LocationId:
    if identifier_kind != "evm_address" or not network_scope.strip():
        raise ValueError("unsupported EVM location identifier")
    return LocationId(
        f"evm:{network_scope.strip().lower()}:{identifier_value.strip().lower()}"
    )


def draft_transfer(
    profile: SourceProfile,
    draft_context: EvmDraftContext,
    semantics: ActivitySemantics,
) -> EconomicActivityDraft:
    return EconomicActivityDraft(
        activity_id=f"evm_explorer:{draft_context.path_name}:{draft_context.tx_hash}",
        source=str(profile.source),
        adapter_id="evm_explorer",
        location_id=draft_context.location_id,
        timestamp=draft_context.timestamp,
        classification=semantics.to_classification(),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=f"Transfer - {draft_context.tx_hash}",
        raw_file=draft_context.path_name,
        raw_row_ref=f"row:{draft_context.row_index}",
        tx_hash=draft_context.tx_hash,
        provider_operation_key="explorer_transfer",
        legs=(
            economic_leg(
                leg_id="primary",
                kind=LegKind.PRIMARY,
                quantity=draft_context.quantity,
                instrument=draft_context.instrument,
            ),
        ),
    )
