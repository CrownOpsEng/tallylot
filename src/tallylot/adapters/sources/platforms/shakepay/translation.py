"""Shakepay row translation rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tallylot.adapters.support import CsvRowContext, IssueSpec, issue_record
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    EconomicActivityDraft,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile

TORONTO = ZoneInfo("America/Toronto")


def translate_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
) -> EconomicActivityDraft | IssueRecord | None:
    row = row_context.row
    timestamp = _parse_local_timestamp((row.get("Date") or "").strip())
    row_type = (row.get("Type") or "").strip()
    transaction_id = f"shakepay:{row_context.raw_file}:{row_context.raw_row_ref}"
    if row_context.raw_file == "cash_transactions_summary.csv":
        return _normalize_cash_row(profile, row_context, timestamp, transaction_id, row_type)
    return _normalize_crypto_row(profile, row_context, timestamp, transaction_id, row_type)


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
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.FIAT_DEPOSIT,
                projection_type=ProjectionType.DEPOSIT,
                journal_intent=JournalIntent.FUNDING_INFLOW,
                tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_IN,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type or "cash_credit",
            legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset="CAD", amount=credit),),
        )
    if debit is None or debit <= Decimal("0"):
        return None
    if row_type == "Card purchase":
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.CASH_EXPENSE,
                projection_type=ProjectionType.EXPENSE_NON_TAXABLE,
                journal_intent=JournalIntent.EXPENSE_RECOGNITION,
                tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_EXPENSE,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="out", kind=LegKind.PRIMARY, asset="CAD", amount=debit),),
        )
    return EconomicActivityDraft(
        activity_id=transaction_id,
        source=str(profile.source),
        adapter_id="shakepay",
        account="Shakepay",
        wallet="Shakepay",
        timestamp=timestamp,
        classification=classification(
            economic_kind=EconomicKind.CASH_WITHDRAWAL,
            projection_type=ProjectionType.WITHDRAWAL,
            journal_intent=JournalIntent.FUNDING_OUTFLOW,
            tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=description,
        raw_file=row_context.raw_file,
        raw_row_ref=row_context.raw_row_ref,
        tx_hash=transaction_id,
        provider_operation_key=row_type or "cash_debit",
        legs=(economic_leg(direction="out", kind=LegKind.PRIMARY, asset="CAD", amount=debit),),
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
    description = (row.get("Description") or "").strip().lower()
    if row_type == "Reward" and credited_amount is not None and credited_asset:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.PLATFORM_REWARD,
                projection_type=ProjectionType.REWARD_BONUS,
                journal_intent=JournalIntent.INCOME_RECOGNITION,
                tax_treatment_code=TaxTreatmentCode.ORDINARY_INCOME,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="in", kind=LegKind.PRIMARY, asset=credited_asset, amount=credited_amount),),
        )
    if row_type == "Buy" and debited_amount is not None and credited_amount is not None:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_type=ProjectionType.TRADE,
                journal_intent=JournalIntent.ASSET_EXCHANGE,
                tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
            description=(row.get("Description") or "").strip(),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(direction="in", kind=LegKind.PRIMARY, asset=credited_asset, amount=credited_amount),
                economic_leg(direction="out", kind=LegKind.PRIMARY, asset=debited_asset, amount=debited_amount),
            ),
        )
    if row_type == "Send" and debited_amount is not None and debited_asset:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                projection_type=ProjectionType.WITHDRAWAL,
                journal_intent=JournalIntent.FUNDING_OUTFLOW,
                tax_treatment_code=TaxTreatmentCode.NON_TAXABLE_TRANSFER_OUT,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=(row.get("Description") or "").strip(),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="out", kind=LegKind.PRIMARY, asset=debited_asset, amount=debited_amount),),
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


def _parse_local_timestamp(value: str) -> datetime:
    local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TORONTO)
    return local.astimezone(ZoneInfo("UTC"))
