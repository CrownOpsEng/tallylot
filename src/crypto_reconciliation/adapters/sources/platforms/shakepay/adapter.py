"""Shakepay export adapter."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from crypto_reconciliation.adapters.sources.intake_support import match_intake_by_path_or_header, no_intake_route
from crypto_reconciliation.adapters.sources.mapped_transaction_support import (
    MappedTransactionSpec,
    NormalizationIssueSpec,
    mapped_transaction,
    normalization_issue,
)
from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    extract_pdf_balances as _extract_pdf_balances,
)
from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import (
    match_pdf_statement as _match_pdf_statement,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    NormalizedTransaction,
    SourceProfile,
    TransactionCategory,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

TORONTO = ZoneInfo("America/Toronto")


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
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"america_toronto": rows_with_dates} if rows_with_dates else {},
        }, ()

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
        transactions: list[NormalizedTransaction] = []
        issues: list[IssueRecord] = []
        for path in sorted(raw_dir.rglob("*.csv")):
            for index, row in enumerate(_read_rows(path), start=2):
                parsed = _normalize_row(profile, path.name, index, row)
                if isinstance(parsed, IssueRecord):
                    issues.append(parsed)
                    continue
                if parsed is not None:
                    transactions.append(parsed)
        return NormalizationResult(
            transactions=tuple(transactions),
            balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _normalize_row(
    profile: SourceProfile,
    raw_file: str,
    index: int,
    row: dict[str, str],
) -> NormalizedTransaction | IssueRecord | None:
    row_ref = f"row:{index}"
    timestamp = _parse_local_timestamp((row.get("Date") or "").strip())
    if raw_file == "cash_transactions_summary.csv":
        debit = parse_decimal((row.get("Debit") or "").strip())
        credit = parse_decimal((row.get("Credit") or "").strip())
        description = (row.get("Description") or "").strip()
        row_type = (row.get("Type") or "").strip()
        category: TransactionCategory | None = None
        asset_in = ""
        amount_in = None
        asset_out = ""
        amount_out = None
        if credit is not None and credit > Decimal("0"):
            category = "deposit"
            asset_in = "CAD"
            amount_in = credit
        elif debit is not None and debit > Decimal("0"):
            category = "expense" if row_type == "Card purchase" else "withdrawal"
            asset_out = "CAD"
            amount_out = debit
        else:
            return None
        return mapped_transaction(
            MappedTransactionSpec(
                transaction_id=f"shakepay:{raw_file}:{row_ref}",
                source=str(profile.source),
                adapter_id="shakepay",
                account="Shakepay",
                wallet="Shakepay",
                timestamp=timestamp,
                category=category,
                description=description,
                raw_file=raw_file,
                raw_row_ref=row_ref,
                asset_in=asset_in,
                amount_in=amount_in,
                asset_out=asset_out,
                amount_out=amount_out,
                tx_hash=f"shakepay:{raw_file}:{row_ref}",
            )
        )
    debited_amount = parse_decimal((row.get("Amount Debited") or "").strip())
    credited_amount = parse_decimal((row.get("Amount Credited") or "").strip())
    debited_asset = (row.get("Asset Debited") or "").strip().upper()
    credited_asset = (row.get("Asset Credited") or "").strip().upper()
    description = (row.get("Description") or "").strip().lower()
    row_type = (row.get("Type") or "").strip()
    transaction_id = f"shakepay:{raw_file}:{row_ref}"
    if row_type == "Reward" and credited_amount is not None and credited_asset:
        spec = MappedTransactionSpec(
            transaction_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            category="reward",
            description=description,
            raw_file=raw_file,
            raw_row_ref=row_ref,
            asset_in=credited_asset,
            amount_in=credited_amount,
            tx_hash=transaction_id,
        )
        return mapped_transaction(spec)
    if row_type == "Buy" and debited_amount is not None and credited_amount is not None:
        spec = MappedTransactionSpec(
            transaction_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            category="trade",
            description=(row.get("Description") or "").strip(),
            raw_file=raw_file,
            raw_row_ref=row_ref,
            asset_in=credited_asset,
            amount_in=credited_amount,
            asset_out=debited_asset,
            amount_out=debited_amount,
            tx_hash=transaction_id,
        )
        return mapped_transaction(spec)
    if row_type == "Send" and debited_amount is not None and debited_asset:
        spec = MappedTransactionSpec(
            transaction_id=transaction_id,
            source=str(profile.source),
            adapter_id="shakepay",
            account="Shakepay",
            wallet="Shakepay",
            timestamp=timestamp,
            category="withdrawal",
            description=(row.get("Description") or "").strip(),
            raw_file=raw_file,
            raw_row_ref=row_ref,
            asset_out=debited_asset,
            amount_out=debited_amount,
            tx_hash=transaction_id,
        )
        return mapped_transaction(spec)
    return normalization_issue(
        NormalizationIssueSpec(
            source=str(profile.source),
            adapter_id="shakepay",
            issue_id=transaction_id,
            kind="unsupported_row",
            message=f"Unsupported Shakepay row type: {row_type}",
            raw_file=raw_file,
            raw_row_ref=row_ref,
        )
    )


def _parse_local_timestamp(value: str) -> datetime:
    local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TORONTO)
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


ADAPTER = ShakepayAdapter()
