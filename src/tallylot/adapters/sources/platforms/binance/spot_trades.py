"""Binance spot trade normalization."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import location_id_from_parts
from tallylot.adapters.support.drafts import (
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    classification,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft

from .csv_rows import read_rows
from .field_parsing import amount_with_asset, split_pair
from .timestamps import parse_export_timestamp

SUPPORTED_SPOT_SIDES = frozenset({"SELL", "BUY"})


def normalize_spot_rows(
    profile: SourceProfile, path: Path
) -> list[EconomicActivityDraft]:
    drafts: list[EconomicActivityDraft] = []
    for index, row in enumerate(read_rows(path), start=2):
        side = (row.get("Side") or "").strip().upper()
        pair = (row.get("Pair") or "").strip().upper()
        base_asset, quote_asset = split_pair(pair)
        executed_amount, executed_asset = amount_with_asset(row.get("Executed", ""))
        quote_amount, _ = amount_with_asset(row.get("Amount", ""))
        fee_amount, fee_asset = amount_with_asset(row.get("Fee", ""))
        timestamp = parse_export_timestamp((row.get("Time") or "").strip(), path.name)
        if executed_amount is None or quote_amount is None:
            continue
        if side == "SELL":
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    location_id=location_id_from_parts(str(profile.source), "spot"),
                    timestamp=timestamp,
                    classification=classification(
                        economic_kind=EconomicKind.SPOT_TRADE,
                        projection_hint=ProjectionHint.TRADE,
                        accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                        tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                    ),
                    leg_policy=_trade_policy(fee_amount, fee_asset),
                    description=f"Binance spot sell {pair}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    provider_operation_key=f"spot:{side}",
                    legs=(
                        economic_leg(
                            leg_id="primary_out",
                            kind=LegKind.PRIMARY,
                            quantity=-executed_amount,
                            instrument=symbol_claim(
                                base_asset or executed_asset, venue="binance"
                            ),
                        ),
                        economic_leg(
                            leg_id="primary_in",
                            kind=LegKind.PRIMARY,
                            quantity=quote_amount,
                            instrument=symbol_claim(quote_asset, venue="binance"),
                        ),
                        *_charge_legs(
                            fee_amount, fee_asset, attributed_to_leg_id="primary_in"
                        ),
                    ),
                )
            )
        elif side == "BUY":
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    location_id=location_id_from_parts(str(profile.source), "spot"),
                    timestamp=timestamp,
                    classification=classification(
                        economic_kind=EconomicKind.SPOT_TRADE,
                        projection_hint=ProjectionHint.TRADE,
                        accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                        tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                    ),
                    leg_policy=_trade_policy(fee_amount, fee_asset),
                    description=f"Binance spot buy {pair}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    provider_operation_key=f"spot:{side}",
                    legs=(
                        economic_leg(
                            leg_id="primary_in",
                            kind=LegKind.PRIMARY,
                            quantity=executed_amount,
                            instrument=symbol_claim(
                                base_asset or executed_asset, venue="binance"
                            ),
                        ),
                        economic_leg(
                            leg_id="primary_out",
                            kind=LegKind.PRIMARY,
                            quantity=-quote_amount,
                            instrument=symbol_claim(quote_asset, venue="binance"),
                        ),
                        *_charge_legs(
                            fee_amount, fee_asset, attributed_to_leg_id="primary_out"
                        ),
                    ),
                )
            )
    return drafts


def _trade_policy(fee_amount: Decimal | None, fee_asset: str | None) -> FactLegPolicy:
    if fee_amount is not None and fee_asset:
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    return TWO_SIDED_PRIMARY_EXCHANGE_POLICY


def _charge_legs(
    fee_amount: Decimal | None,
    fee_asset: str | None,
    *,
    attributed_to_leg_id: str,
) -> tuple[EconomicLegDraft, ...]:
    if fee_amount is None or not fee_asset:
        return ()
    return (
        economic_leg(
            leg_id="charge",
            kind=LegKind.CHARGE,
            quantity=-fee_amount,
            instrument=symbol_claim(fee_asset, venue="binance"),
            subtype="trading_fee",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )
