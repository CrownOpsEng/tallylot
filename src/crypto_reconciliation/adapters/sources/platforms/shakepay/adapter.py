"""Shakepay export adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    extract_pdf_balances as _extract_pdf_balances,
)
from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    match_pdf_statement as _match_pdf_statement,
)
from crypto_reconciliation.adapters.support import (
    CsvRowContext,
    IssueSpec,
    collect_csv_row_results,
    issue_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    normalization_result_from_drafts,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

TORONTO = ZoneInfo("America/Toronto")
SUPPORTED_ROW_TYPES = frozenset({"Reward", "Buy", "Send", "Card purchase"})


class ShakepayAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("shakepay"),
        display_name="Shakepay",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Shakepay cash and crypto export summaries.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "shakepay" in source.lower():
            return 100
        if any("crypto_transactions_summary.csv" in item.relative_path for item in inventory):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("shakepay", "crypto_transactions_summary.csv", "cash_transactions_summary.csv"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="america_toronto")

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        return _match_pdf_statement(pdf_path, text)

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        return _extract_pdf_balances(text, pdf_path.name)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        drafts, issues = collect_csv_row_results(raw_dir, lambda row_context: _normalize_row(profile, row_context))
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
        )


def _normalize_row(
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
                normalized_category="deposit",
                economic_kind="fiat_deposit",
                projection_type="Deposit",
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
                normalized_category="expense",
                economic_kind="cash_expense",
                projection_type="Expense (non taxable)",
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
            normalized_category="withdrawal",
            economic_kind="cash_withdrawal",
            projection_type="Withdrawal",
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
                normalized_category="reward",
                economic_kind="platform_reward",
                projection_type="Reward / Bonus",
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
                normalized_category="trade",
                economic_kind="spot_trade",
                projection_type="Trade",
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
                normalized_category="withdrawal",
                economic_kind="asset_withdrawal",
                projection_type="Withdrawal",
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


ADAPTER = ShakepayAdapter()
