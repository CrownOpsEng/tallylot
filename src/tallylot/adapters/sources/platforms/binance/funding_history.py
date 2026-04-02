"""Binance deposit and withdrawal normalization."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import location_id_from_parts
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
)
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft

from .csv_rows import read_rows
from .timestamps import parse_export_timestamp

SUPPORTED_FUNDING_EXPORTS = frozenset({"deposit", "withdrawal"})


def normalize_deposit_rows(profile: SourceProfile, path: Path) -> list[EconomicActivityDraft]:
    drafts: list[EconomicActivityDraft] = []
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        if amount is None:
            continue
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"binance:{path.name}:row:{index}",
                source=str(profile.source),
                adapter_id="binance",
                location_id=location_id_from_parts(str(profile.source), "binance", "funding"),
                timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                classification=classification(
                    economic_kind=EconomicKind.ASSET_DEPOSIT,
                    projection_hint=ProjectionHint.DEPOSIT,
                    accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                    tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                ),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                description=f"Binance deposit via {(row.get('Network') or '').strip()}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                tx_hash=(row.get("TXID") or "").strip(),
                provider_operation_key="funding:deposit",
                legs=(
                    economic_leg(
                        direction="in",
                        kind=LegKind.PRIMARY,
                        asset=(row.get("Coin") or "").strip().upper(),
                        amount=amount,
                    ),
                ),
            )
        )
    return drafts


def normalize_withdraw_rows(profile: SourceProfile, path: Path) -> list[EconomicActivityDraft]:
    drafts: list[EconomicActivityDraft] = []
    for index, row in enumerate(read_rows(path), start=2):
        if (row.get("Status") or "").strip().lower() != "completed":
            continue
        amount = parse_decimal((row.get("Amount") or "").strip())
        fee = parse_decimal((row.get("Fee") or "").strip())
        if amount is None:
            continue
        coin = (row.get("Coin") or "").strip().upper()
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"binance:{path.name}:row:{index}",
                source=str(profile.source),
                adapter_id="binance",
                location_id=location_id_from_parts(str(profile.source), "binance", "funding"),
                timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                classification=classification(
                    economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                    projection_hint=ProjectionHint.WITHDRAWAL,
                    accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                    tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                ),
                leg_policy=_withdrawal_policy(fee),
                description=f"Binance withdrawal via {(row.get('Network') or '').strip()}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                tx_hash=(row.get("TXID") or "").strip(),
                provider_operation_key="funding:withdrawal",
                legs=(
                    economic_leg(direction="out", kind=LegKind.PRIMARY, asset=coin, amount=amount),
                    *_charge_legs(fee, coin),
                ),
            )
        )
    return drafts


def _withdrawal_policy(fee: Decimal | None) -> FactLegPolicy:
    if fee is None or fee <= Decimal("0"):
        return SINGLE_PRIMARY_ACTIVITY_POLICY
    return FactLegPolicy(
        limits=(
            LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, max_in_count=1, max_out_count=1),
            LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
        )
    )


def _charge_legs(fee: Decimal | None, coin: str) -> tuple[EconomicLegDraft, ...]:
    if fee is None or fee <= Decimal("0"):
        return ()
    return (
        economic_leg(
            direction="out",
            kind=LegKind.CHARGE,
            asset=coin,
            amount=fee,
            subtype="network_fee",
            attributed_to_direction="out",
        ),
    )
