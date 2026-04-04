"""Shakepay row translation rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tallylot.adapters.support import (
    CsvRowContext,
    IssueSpec,
    issue_record,
    location_id_from_parts,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    EconomicActivityDraft,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile

TORONTO = ZoneInfo("America/Toronto")


def translate_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
) -> EconomicActivityDraft | IssueRecord | None:
    row = row_context.row
    timestamp = _parse_local_timestamp((row.get("Date") or "").strip())
    if timestamp is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="shakepay",
                issue_id=f"shakepay:{row_context.raw_file}:{row_context.raw_row_ref}:invalid_timestamp",
                kind="unsupported_row",
                message="Shakepay row is missing a supported local timestamp.",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    row_type = (row.get("Type") or "").strip()
    transaction_id = f"shakepay:{row_context.raw_file}:{row_context.raw_row_ref}"
    if row_context.raw_file == "cash_transactions_summary.csv":
        return _normalize_cash_row(
            profile, row_context, timestamp, transaction_id, row_type
        )
    return _normalize_crypto_row(
        profile, row_context, timestamp, transaction_id, row_type
    )


def _normalize_cash_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
    timestamp: datetime,
    transaction_id: str,
    row_type: str,
) -> EconomicActivityDraft | None:
    row = row_context.row
    debit = parse_decimal((row.get("Debit") or "").strip())
    credit = parse_decimal((row.get("Credit") or "").strip())
    description = (row.get("Description") or "").strip()
    if credit is not None and credit > Decimal("0"):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.FIAT_DEPOSIT,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type or "cash_credit",
            legs=(
                economic_leg(
                    leg_id="cash_in",
                    kind=LegKind.PRIMARY,
                    quantity=credit,
                    instrument="CAD",
                ),
            ),
        )
    if debit is None or debit <= Decimal("0"):
        return None
    if row_type == "Card purchase":
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.CASH_EXPENSE,
                projection_hint=ProjectionHint.EXPENSE_NON_TAXABLE,
                accounting_intent_hint=AccountingIntentHint.EXPENSE_RECOGNITION,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_EXPENSE,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(
                    leg_id="cash_out",
                    kind=LegKind.PRIMARY,
                    quantity=-debit,
                    instrument="CAD",
                ),
            ),
        )
    return EconomicActivityDraft(
        activity_id=transaction_id,
        source=str(profile.source),
        adapter_id="shakepay",
        location_id=location_id_from_parts(str(profile.source)),
        timestamp=timestamp,
        classification=classification(
            economic_kind=EconomicKind.CASH_WITHDRAWAL,
            projection_hint=ProjectionHint.WITHDRAWAL,
            accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=description,
        raw_file=row_context.raw_file,
        raw_row_ref=row_context.raw_row_ref,
        tx_hash=transaction_id,
        provider_operation_key=row_type or "cash_debit",
        legs=(
            economic_leg(
                leg_id="cash_out",
                kind=LegKind.PRIMARY,
                quantity=-debit,
                instrument="CAD",
            ),
        ),
    )


def _normalize_crypto_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
    timestamp: datetime,
    transaction_id: str,
    row_type: str,
) -> EconomicActivityDraft | IssueRecord:
    row = row_context.row
    debited_amount = parse_decimal((row.get("Amount Debited") or "").strip())
    credited_amount = parse_decimal((row.get("Amount Credited") or "").strip())
    debited_asset = (row.get("Asset Debited") or "").strip().upper()
    credited_asset = (row.get("Asset Credited") or "").strip().upper()
    description = (row.get("Description") or "").strip()
    fiat_amount, fiat_currency = _row_fiat_value(row)
    if row_type == "Reward" and credited_amount is not None and credited_asset:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.PLATFORM_REWARD,
                projection_hint=ProjectionHint.REWARD_BONUS,
                accounting_intent_hint=AccountingIntentHint.INCOME_RECOGNITION,
                tax_treatment_hint=TaxTreatmentHint.ORDINARY_INCOME,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(
                    leg_id="reward_in",
                    kind=LegKind.PRIMARY,
                    quantity=credited_amount,
                    instrument=credited_asset,
                ),
            ),
        )
    if row_type == "Buy" and credited_amount is not None and credited_asset:
        counterparty_amount = (
            debited_amount if debited_amount is not None else fiat_amount
        )
        counterparty_asset = debited_asset if debited_asset else fiat_currency
        if counterparty_amount is not None and counterparty_asset:
            return EconomicActivityDraft(
                activity_id=transaction_id,
                source=str(profile.source),
                adapter_id="shakepay",
                location_id=location_id_from_parts(str(profile.source)),
                timestamp=timestamp,
                classification=classification(
                    economic_kind=EconomicKind.SPOT_TRADE,
                    projection_hint=ProjectionHint.TRADE,
                    accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                    tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                ),
                leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
                description=description,
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
                tx_hash=transaction_id,
                provider_operation_key=row_type,
                legs=(
                    economic_leg(
                        leg_id="asset_in",
                        kind=LegKind.PRIMARY,
                        quantity=credited_amount,
                        instrument=credited_asset,
                    ),
                    economic_leg(
                        leg_id="asset_out",
                        kind=LegKind.PRIMARY,
                        quantity=-counterparty_amount,
                        instrument=counterparty_asset,
                    ),
                ),
            )
    if (
        row_type == "Sell"
        and debited_amount is not None
        and debited_asset
        and fiat_amount is not None
        and fiat_currency
    ):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(
                    leg_id="asset_in",
                    kind=LegKind.PRIMARY,
                    quantity=fiat_amount,
                    instrument=fiat_currency,
                ),
                economic_leg(
                    leg_id="asset_out",
                    kind=LegKind.PRIMARY,
                    quantity=-debited_amount,
                    instrument=debited_asset,
                ),
            ),
        )
    if row_type == "Receive" and credited_amount is not None and credited_asset:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(
                    leg_id="asset_in",
                    kind=LegKind.PRIMARY,
                    quantity=credited_amount,
                    instrument=credited_asset,
                ),
            ),
        )
    if row_type == "Send" and debited_amount is not None and debited_asset:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                projection_hint=ProjectionHint.WITHDRAWAL,
                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=(row.get("Description") or "").strip(),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(
                    leg_id="asset_out",
                    kind=LegKind.PRIMARY,
                    quantity=-debited_amount,
                    instrument=debited_asset,
                ),
            ),
        )
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="shakepay",
            issue_id=transaction_id,
            kind="unsupported_row",
            message=f"Unsupported Shakepay row type: {row_type}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
        )
    )


def _row_fiat_value(row: dict[str, str]) -> tuple[Decimal | None, str]:
    for amount_field, currency_field in (
        ("Market Value", "Market Value Currency"),
        ("Book Cost", "Book Cost Currency"),
    ):
        amount = parse_decimal((row.get(amount_field) or "").strip())
        currency = (row.get(currency_field) or "").strip().upper()
        if amount is not None and currency:
            return amount, currency
    return None, ""


def _parse_local_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TORONTO)
    except ValueError:
        return None
    return local.astimezone(ZoneInfo("UTC"))
