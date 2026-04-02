"""Ledger Live grouped operation translation helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import location_id_from_parts, matching_file_paths, read_csv_rows
from tallylot.adapters.support.drafts import (
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    EconomicActivityDraft,
    EconomicLegDraft,
    FactLegPolicy,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tallylot.ports.source_profiles import SourceProfile


def translate_operations(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    operations_by_hash: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for path in matching_file_paths(raw_dir):
        for index, row in enumerate(read_csv_rows(path), start=2):
            operation_hash = (row.get("Operation Hash") or row.get("Transaction ID") or "").strip()
            if not operation_hash:
                continue
            operations_by_hash[operation_hash].append((f"{path.name}:row:{index}", row))

    for operation_hash, grouped_rows in sorted(operations_by_hash.items()):
        rows_by_type: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        for raw_ref, row in grouped_rows:
            rows_by_type[(row.get("Operation Type", "") or "").strip().upper()].append((raw_ref, row))
        inbound_rows = rows_by_type.get("IN", [])
        outbound_rows = rows_by_type.get("OUT", [])
        fee_rows = rows_by_type.get("FEES", [])
        raw_file = grouped_rows[0][0].split(":row:", maxsplit=1)[0]
        raw_row_ref = ";".join(f"{raw_file}:{ref.split(':', maxsplit=1)[1]}" for ref, _ in grouped_rows)
        if len(inbound_rows) != 1 or len(outbound_rows) != 1 or len(fee_rows) > 1:
            issues.append(
                IssueRecord(
                    issue_id=f"ledger_live:{raw_file}:{operation_hash}:unsupported_group",
                    source=str(profile.source),
                    adapter_id="ledger_live",
                    severity="medium",
                    kind="unsupported_group",
                    message=(
                        "Ledger Live grouped operation has an unsupported leg shape; "
                        "expected exactly one IN row, one OUT row, and at most one FEES row."
                    ),
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                )
            )
            continue
        _, inbound = inbound_rows[0]
        _, outbound = outbound_rows[0]
        fee_row = fee_rows[0][1] if fee_rows else None
        timestamp = parse_timestamp((inbound.get("Operation Date") or "").strip())
        account_label = (inbound.get("Account Name") or "").strip()
        fee_amount = Decimal((fee_row or {}).get("Operation Amount") or "0")
        fee_asset = (fee_row or outbound).get("Currency Ticker") or ""
        drafts.append(
            EconomicActivityDraft(
                activity_id=f"ledger_live:{raw_file}:{operation_hash}",
                source=str(profile.source),
                adapter_id="ledger_live",
                location_id=location_id_from_parts(str(profile.source), account_label or operation_hash),
                timestamp=timestamp,
                classification=classification(
                    economic_kind=EconomicKind.ASSET_SWAP,
                    projection_hint=ProjectionHint.TRADE,
                    accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                    tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                ),
                leg_policy=_swap_policy(fee_amount, fee_asset),
                description=account_label,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                tx_hash=operation_hash,
                provider_operation_key="ledger_live_swap",
                operation_group_id=operation_hash,
                legs=(
                    economic_leg(
                        direction="in",
                        kind=LegKind.PRIMARY,
                        asset=(inbound.get("Currency Ticker") or "").strip().upper(),
                        amount=Decimal((inbound.get("Operation Amount") or "0").strip()),
                    ),
                    economic_leg(
                        direction="out",
                        kind=LegKind.PRIMARY,
                        asset=(outbound.get("Currency Ticker") or "").strip().upper(),
                        amount=Decimal((outbound.get("Operation Amount") or "0").strip()),
                    ),
                    *_charge_legs(fee_amount, fee_asset),
                ),
            )
        )
    return tuple(drafts), tuple(issues)


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def _swap_policy(fee_amount: Decimal, fee_asset: str) -> FactLegPolicy:
    if fee_amount > 0 and fee_asset:
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    return TWO_SIDED_PRIMARY_EXCHANGE_POLICY


def _charge_legs(fee_amount: Decimal, fee_asset: str) -> tuple[EconomicLegDraft, ...]:
    if fee_amount <= Decimal("0") or not fee_asset:
        return ()
    return (
        economic_leg(
            direction="out",
            kind=LegKind.CHARGE,
            asset=fee_asset.strip().upper(),
            amount=fee_amount,
            subtype="network_fee",
            attributed_to_direction="out",
        ),
    )
