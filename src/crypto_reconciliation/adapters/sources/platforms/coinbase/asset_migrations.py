"""Coinbase asset-migration pairing."""

from __future__ import annotations

from decimal import Decimal

from crypto_reconciliation.adapters.sources.mapped_event_support import MappedEventSpec, mapped_event
from crypto_reconciliation.domain.models import CanonicalEvent, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal

from .timestamps import parse_retail_timestamp


def normalize_asset_migration(
    profile: SourceProfile,
    raw_file: str,
    timestamp: str,
    rows: list[dict[str, str]],
) -> CanonicalEvent:
    if len(rows) != 2:
        raise ValueError(f"Expected 2 asset-migration rows at {timestamp}, found {len(rows)}")
    negatives = [
        row for row in rows if (parse_decimal((row.get("Quantity Transacted") or "").strip()) or Decimal("0")) < 0
    ]
    positives = [
        row for row in rows if (parse_decimal((row.get("Quantity Transacted") or "").strip()) or Decimal("0")) > 0
    ]
    if len(negatives) != 1 or len(positives) != 1:
        raise ValueError(f"Asset-migration rows at {timestamp} do not form one positive and one negative leg")

    sold_row = negatives[0]
    bought_row = positives[0]
    sold_quantity = abs(parse_decimal((sold_row.get("Quantity Transacted") or "").strip()) or Decimal("0"))
    bought_quantity = parse_decimal((bought_row.get("Quantity Transacted") or "").strip())
    if bought_quantity is None or sold_quantity <= Decimal("0"):
        raise ValueError(f"Asset-migration rows at {timestamp} are missing transacted quantities")
    sold_id = (sold_row.get("ID") or "").strip()
    bought_id = (bought_row.get("ID") or "").strip()
    return mapped_event(
        MappedEventSpec(
            event_id=f"coinbase-asset-migration-{sold_id}-{bought_id}",
            source=str(profile.source),
            adapter_id="coinbase",
            account="Coinbase",
            wallet="Coinbase",
            timestamp=parse_retail_timestamp(timestamp),
            event_kind="Swap (non taxable)",
            description="Coinbase Asset Migration",
            raw_file=raw_file,
            raw_row_ref=f"{sold_id}|{bought_id}",
            render_exchange="Coinbase",
            asset_in=(bought_row.get("Asset") or "").strip().upper(),
            amount_in=bought_quantity,
            asset_out=(sold_row.get("Asset") or "").strip().upper(),
            amount_out=sold_quantity,
            render_group="Asset Migration",
            render_comment="Coinbase Asset Migration",
            render_comment_mode="ignore",
            render_tx_id=f"coinbase-asset-migration-{sold_id}-{bought_id}",
            render_tx_id_mode="ignore",
            render_match_window_seconds="2",
            render_fee_tolerance="0.00000000",
            render_notes="Paired Coinbase Asset Migration rows normalized into one CoinTracking swap",
        )
    )
