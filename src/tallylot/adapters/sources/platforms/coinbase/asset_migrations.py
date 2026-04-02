"""Coinbase asset-migration pairing."""

from __future__ import annotations

from decimal import Decimal

from tallylot.adapters.support import location_id_from_parts
from tallylot.adapters.support.drafts import (
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    EconomicActivityDraft,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile

from .timestamps import parse_retail_timestamp


def normalize_asset_migration(
    profile: SourceProfile,
    raw_file: str,
    timestamp: str,
    rows: list[dict[str, str]],
) -> EconomicActivityDraft:
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
    return EconomicActivityDraft(
        activity_id=f"coinbase-asset-migration-{sold_id}-{bought_id}",
        source=str(profile.source),
        adapter_id="coinbase",
        location_id=location_id_from_parts(str(profile.source)),
        timestamp=parse_retail_timestamp(timestamp),
        classification=classification(
            economic_kind=EconomicKind.ASSET_MIGRATION,
            projection_hint=ProjectionHint.SWAP_NON_TAXABLE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_ASSET_MIGRATION,
        ),
        leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
        description="Coinbase Asset Migration",
        raw_file=raw_file,
        raw_row_ref=f"{sold_id}|{bought_id}",
        provider_operation_key="asset_migration",
        legs=(
            economic_leg(
                direction="in",
                kind=LegKind.PRIMARY,
                asset=(bought_row.get("Asset") or "").strip().upper(),
                amount=bought_quantity,
            ),
            economic_leg(
                direction="out",
                kind=LegKind.PRIMARY,
                asset=(sold_row.get("Asset") or "").strip().upper(),
                amount=sold_quantity,
            ),
        ),
    )
