"""Crypto.com transaction export adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import (
    CsvRowContext,
    IssueSpec,
    collect_csv_row_results,
    issue_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    read_csv_header,
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

HEADER_FIELDS = {
    "Timestamp (UTC)",
    "Transaction Description",
    "Currency",
    "Amount",
    "To Currency",
    "To Amount",
    "Transaction Kind",
}
SUPPORTED_TRANSACTION_KINDS = frozenset({"viban_deposit", "viban_purchase", "crypto_withdrawal"})


class CryptoComAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("crypto_com"),
        display_name="Crypto.com",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Crypto.com transaction exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "crypto.com" in source.lower() or "crypto_com" in source.lower():
            return 100
        if any(HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("crypto.com", "crypto_com"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="value_utc")

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        drafts, issues = collect_csv_row_results(
            raw_dir,
            lambda row_context: _normalize_row(profile, row_context),
            skip_file=_skip_unrecognized_csv,
        )
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
        )


def _normalize_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
) -> EconomicActivityDraft | IssueRecord:
    row = row_context.row
    timestamp = _parse_timestamp((row.get("Timestamp (UTC)") or "").strip())
    transaction_id = f"crypto_com:{row_context.raw_file}:{row_context.raw_row_ref}"
    if timestamp is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="crypto_com",
                issue_id=f"{transaction_id}:invalid_timestamp",
                kind="unsupported_row",
                message="Crypto.com row is missing a supported UTC timestamp.",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    description = (row.get("Transaction Description") or "").strip()
    kind = (row.get("Transaction Kind") or "").strip()
    tx_hash = (row.get("Transaction Hash") or "").strip()
    currency = (row.get("Currency") or "").strip().upper()
    amount = parse_decimal((row.get("Amount") or "").strip())
    to_currency = (row.get("To Currency") or "").strip().upper()
    to_amount = parse_decimal((row.get("To Amount") or "").strip())
    if kind == "viban_deposit" and amount is not None and amount > Decimal("0"):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            account=str(profile.source),
            wallet=str(profile.source),
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
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(economic_leg(direction="in", asset=currency, amount=amount),),
        )
    if kind == "viban_purchase" and amount is not None and amount < Decimal("0") and to_amount is not None:
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            account=str(profile.source),
            wallet=str(profile.source),
            timestamp=timestamp,
            classification=classification(
                normalized_category="trade",
                economic_kind="spot_trade",
                projection_type="Trade",
                journal_intent="asset_exchange",
                tax_treatment_code="capital_exchange",
            ),
            description=f"{currency} -> {to_currency}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(
                economic_leg(direction="in", asset=to_currency, amount=to_amount),
                economic_leg(direction="out", asset=currency, amount=abs(amount)),
            ),
        )
    if kind == "crypto_withdrawal" and amount is not None and amount < Decimal("0"):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            account=str(profile.source),
            wallet=str(profile.source),
            timestamp=timestamp,
            classification=classification(
                normalized_category="withdrawal",
                economic_kind="asset_withdrawal",
                projection_type="Withdrawal",
                journal_intent="funding_outflow",
                tax_treatment_code="non_taxable_transfer_out",
            ),
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(economic_leg(direction="out", asset=currency, amount=abs(amount)),),
        )
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="crypto_com",
            issue_id=transaction_id,
            kind="unsupported_row",
            message=f"Unsupported Crypto.com transaction kind: {kind}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
        )
    )


def _skip_unrecognized_csv(path: Path) -> bool:
    return not HEADER_FIELDS.issubset(set(read_csv_header(path)))


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)
    except ValueError:
        return None


ADAPTER = CryptoComAdapter()
