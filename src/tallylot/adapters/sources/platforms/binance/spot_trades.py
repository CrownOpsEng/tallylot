"""Binance spot trade normalization."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    fee_leg,
)
from tallylot.ports.source_profiles import SourceProfile

from .csv_rows import read_rows
from .field_parsing import amount_with_asset, split_pair
from .timestamps import parse_export_timestamp

SUPPORTED_SPOT_SIDES = frozenset({"SELL", "BUY"})


def normalize_spot_rows(profile: SourceProfile, path: Path) -> list[EconomicActivityDraft]:
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
        fee_legs = (fee_leg(asset=fee_asset, amount=fee_amount),) if fee_amount is not None and fee_asset else ()
        if side == "SELL":
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Spot",
                    wallet="Spot",
                    timestamp=timestamp,
                    classification=classification(
                        economic_kind="spot_trade",
                        projection_type="Trade",
                        journal_intent="asset_exchange",
                        tax_treatment_code="capital_exchange",
                    ),
                    description=f"Binance spot sell {pair}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    provider_operation_key=f"spot:{side}",
                    legs=(
                        economic_leg(direction="in", asset=quote_asset, amount=quote_amount),
                        economic_leg(direction="out", asset=base_asset or executed_asset, amount=executed_amount),
                    ),
                    fee_legs=fee_legs,
                )
            )
        elif side == "BUY":
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"binance:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="binance",
                    account="Spot",
                    wallet="Spot",
                    timestamp=timestamp,
                    classification=classification(
                        economic_kind="spot_trade",
                        projection_type="Trade",
                        journal_intent="asset_exchange",
                        tax_treatment_code="capital_exchange",
                    ),
                    description=f"Binance spot buy {pair}",
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    provider_operation_key=f"spot:{side}",
                    legs=(
                        economic_leg(direction="in", asset=base_asset or executed_asset, amount=executed_amount),
                        economic_leg(direction="out", asset=quote_asset, amount=quote_amount),
                    ),
                    fee_legs=fee_legs,
                )
            )
    return drafts
