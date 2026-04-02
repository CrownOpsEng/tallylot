"""Binance deposit and withdrawal normalization."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    fee_leg,
)
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile

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
                account="Binance",
                wallet="Funding",
                timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                classification=classification(
                    economic_kind="asset_deposit",
                    projection_type="deposit",
                    journal_intent="funding_inflow",
                    tax_treatment_code="non_taxable_transfer_in",
                ),
                description=f"Binance deposit via {(row.get('Network') or '').strip()}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                tx_hash=(row.get("TXID") or "").strip(),
                provider_operation_key="funding:deposit",
                legs=(economic_leg(direction="in", asset=(row.get("Coin") or "").strip().upper(), amount=amount),),
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
        fee_legs = (fee_leg(asset=coin, amount=fee),) if fee is not None and fee > Decimal("0") else ()
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"binance:{path.name}:row:{index}",
                source=str(profile.source),
                adapter_id="binance",
                account="Binance",
                wallet="Funding",
                timestamp=parse_export_timestamp((row.get("Time") or "").strip(), path.name),
                classification=classification(
                    economic_kind="asset_withdrawal",
                    projection_type="withdrawal",
                    journal_intent="funding_outflow",
                    tax_treatment_code="non_taxable_transfer_out",
                ),
                description=f"Binance withdrawal via {(row.get('Network') or '').strip()}",
                raw_file=path.name,
                raw_row_ref=f"row:{index}",
                tx_hash=(row.get("TXID") or "").strip(),
                provider_operation_key="funding:withdrawal",
                legs=(economic_leg(direction="out", asset=coin, amount=amount),),
                fee_legs=fee_legs,
            )
        )
    return drafts
