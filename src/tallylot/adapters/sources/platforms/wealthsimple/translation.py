"""Wealthsimple crypto row translation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import CsvRowContext, IssueSpec, issue_record, location_id_from_parts, read_csv_header
from tallylot.adapters.support.drafts import (
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft

BROKER_HEADER = (
    "transaction_date",
    "settlement_date",
    "account_id",
    "account_type",
    "activity_type",
    "activity_sub_type",
    "direction",
    "symbol",
    "name",
    "currency",
    "quantity",
    "unit_price",
    "commission",
    "net_cash_amount",
)
ACTIVITY_HEADER = (
    "transaction_date",
    "settlement_date",
    "account_id",
    "account_type",
    "activity_type",
    "activity_sub_type",
    "quantity",
    "currency",
    "symbol",
    "commission",
    "net_cash_amount",
)


@dataclass(frozen=True)
class _TradeDraftContext:
    account_id: str
    symbol: str
    currency: str
    quantity: Decimal
    commission: Decimal | None
    net_cash_amount: Decimal
    timestamp: datetime
    effective_at: datetime | None
    provider_operation_key: str


def normalize_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
) -> EconomicActivityDraft | IssueRecord | None:
    row = row_context.row
    if (row.get("account_type") or "").strip().lower() != "crypto":
        return None
    activity_type = (row.get("activity_type") or "").strip()
    activity_sub_type = (row.get("activity_sub_type") or "").strip()
    transaction_date = _parse_date((row.get("transaction_date") or "").strip())
    settlement_date = _parse_date((row.get("settlement_date") or "").strip())
    timestamp = transaction_date or settlement_date
    if timestamp is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="wealthsimple",
                issue_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}:invalid_date",
                kind="unsupported_row",
                message="Wealthsimple crypto activity row is missing a supported settlement or transaction date.",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    account_id = (row.get("account_id") or "").strip()
    symbol = (row.get("symbol") or "").strip().upper()
    currency = (row.get("currency") or "").strip().upper()
    quantity = parse_decimal((row.get("quantity") or "").strip())
    commission = parse_decimal((row.get("commission") or "").strip())
    net_cash_amount = parse_decimal((row.get("net_cash_amount") or "").strip())
    if quantity is None or net_cash_amount is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="wealthsimple",
                issue_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}:missing_amount",
                kind="unsupported_row",
                message="Wealthsimple crypto activity row is missing quantity or cash amount.",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    provider_operation_key = f"{activity_type.lower()}:{activity_sub_type.upper()}"
    if activity_type.lower() == "trade" and activity_sub_type.upper() in {"BUY", "SELL"}:
        return _trade_draft_or_issue(
            profile=profile,
            row_context=row_context,
            trade_side=activity_sub_type.upper(),
            context=_TradeDraftContext(
                account_id=account_id,
                symbol=symbol,
                currency=currency,
                quantity=quantity,
                commission=commission,
                net_cash_amount=net_cash_amount,
                timestamp=timestamp,
                effective_at=settlement_date,
                provider_operation_key=provider_operation_key,
            ),
        )
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="wealthsimple",
            issue_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}",
            kind="unsupported_row",
            message=f"Unsupported Wealthsimple crypto activity: {activity_type}/{activity_sub_type}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
        )
    )


def skip_unrecognized_csv(path: Path) -> bool:
    return read_csv_header(path) not in {BROKER_HEADER, ACTIVITY_HEADER}


def _charge_legs(
    commission: Decimal | None,
    currency: str,
    *,
    attributed_to_leg_id: str,
    leg_id: str,
) -> tuple[EconomicLegDraft, ...]:
    if commission is None or commission <= Decimal("0"):
        return ()
    return (
        economic_leg(
            leg_id=leg_id,
            kind=LegKind.CHARGE,
            quantity=-commission,
            instrument=symbol_claim(currency, venue="wealthsimple"),
            subtype="commission",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )


def _trade_draft_or_issue(
    *,
    profile: SourceProfile,
    row_context: CsvRowContext,
    trade_side: str,
    context: _TradeDraftContext,
) -> EconomicActivityDraft | IssueRecord:
    trade_side_lower = trade_side.lower()
    cash_amount = _gross_cash_amount(
        context.net_cash_amount,
        context.commission,
        trade_side=trade_side_lower,
    )
    if cash_amount is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="wealthsimple",
                issue_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}:invalid_cash_amount",
                kind="unsupported_row",
                message=(
                    f"Wealthsimple {trade_side_lower} row has a non-positive gross cash amount "
                    "after commission expansion."
                ),
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    return EconomicActivityDraft(
        activity_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}",
        source=str(profile.source),
        adapter_id="wealthsimple",
        location_id=location_id_from_parts(str(profile.source), context.account_id),
        timestamp=context.timestamp,
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_hint=ProjectionHint.TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
        ),
        effective_at=context.effective_at,
        effective_precision=TemporalPrecision.DATE if context.effective_at is not None else None,
        leg_policy=_trade_policy(context.commission),
        description=f"Wealthsimple Crypto {trade_side_lower}",
        raw_file=row_context.raw_file,
        raw_row_ref=row_context.raw_row_ref,
        provider_operation_key=context.provider_operation_key,
        legs=(
            economic_leg(
                leg_id="primary_in" if trade_side == "BUY" else "primary_out",
                kind=LegKind.PRIMARY,
                quantity=context.quantity if trade_side == "BUY" else -context.quantity,
                instrument=symbol_claim(context.symbol, venue="wealthsimple"),
            ),
            economic_leg(
                leg_id="primary_out" if trade_side == "BUY" else "primary_in",
                kind=LegKind.PRIMARY,
                quantity=-cash_amount if trade_side == "BUY" else cash_amount,
                instrument=symbol_claim(context.currency, venue="wealthsimple"),
            ),
            *_charge_legs(
                context.commission,
                context.currency,
                attributed_to_leg_id="primary_out" if trade_side == "BUY" else "primary_in",
                leg_id="charge",
            ),
        ),
    )


def _gross_cash_amount(
    net_cash_amount: Decimal,
    commission: Decimal | None,
    *,
    trade_side: str,
) -> Decimal | None:
    gross_cash_amount = abs(net_cash_amount)
    if commission is not None and commission > Decimal("0"):
        if trade_side == "buy":
            gross_cash_amount -= commission
        else:
            gross_cash_amount += commission
    if gross_cash_amount <= Decimal("0"):
        return None
    return gross_cash_amount


def _trade_policy(commission: Decimal | None) -> FactLegPolicy:
    if commission is not None and commission > Decimal("0"):
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    return FactLegPolicy(
        limits=(
            LegShapeLimit(
                kind=LegKind.PRIMARY,
                min_count=2,
                max_count=2,
                min_positive_count=1,
                max_positive_count=1,
                min_negative_count=1,
                max_negative_count=1,
            ),
        )
    )


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None
