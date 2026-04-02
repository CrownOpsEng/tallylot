"""Shakepay row translation rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tallylot.adapters.support import CsvRowContext, IssueSpec, issue_record
from tallylot.adapters.support.drafts import EconomicActivityDraft, classification, economic_leg
from tallylot.domain.issues import IssueRecord
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
                economic_kind="fiat_deposit",
                projection_type="deposit",
                journal_intent="funding_inflow",
                tax_treatment_code="non_taxable_transfer_in",
            ),
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type or "cash_credit",
            legs=(economic_leg(direction="in", asset="CAD", amount=credit),),
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
                economic_kind="cash_expense",
                projection_type="expense_non_taxable",
                journal_intent="expense_recognition",
                tax_treatment_code="non_taxable_expense",
            ),
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="out", asset="CAD", amount=debit),),
        )
    return EconomicActivityDraft(
        activity_id=transaction_id,
        source=str(profile.source),
        adapter_id="shakepay",
        account="Shakepay",
        wallet="Shakepay",
        timestamp=timestamp,
        classification=classification(
            economic_kind="cash_withdrawal",
            projection_type="withdrawal",
            journal_intent="funding_outflow",
            tax_treatment_code="non_taxable_transfer_out",
        ),
        description=description,
        raw_file=row_context.raw_file,
        raw_row_ref=row_context.raw_row_ref,
        tx_hash=transaction_id,
        provider_operation_key=row_type or "cash_debit",
        legs=(economic_leg(direction="out", asset="CAD", amount=debit),),
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
                economic_kind="platform_reward",
                projection_type="reward_bonus",
                journal_intent="income_recognition",
                tax_treatment_code="ordinary_income",
            ),
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="in", asset=credited_asset, amount=credited_amount),),
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
                economic_kind="spot_trade",
                projection_type="trade",
                journal_intent="asset_exchange",
                tax_treatment_code="capital_exchange",
            ),
            description=(row.get("Description") or "").strip(),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(
                economic_leg(direction="in", asset=credited_asset, amount=credited_amount),
                economic_leg(direction="out", asset=debited_asset, amount=debited_amount),
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
                economic_kind="asset_withdrawal",
                projection_type="withdrawal",
                journal_intent="funding_outflow",
                tax_treatment_code="non_taxable_transfer_out",
            ),
            description=(row.get("Description") or "").strip(),
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=transaction_id,
            provider_operation_key=row_type,
            legs=(economic_leg(direction="out", asset=debited_asset, amount=debited_amount),),
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
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
