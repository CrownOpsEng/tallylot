"""Wealthsimple crypto export adapter."""

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
    fee_leg,
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
SUPPORTED_ACTIVITY_KEYS = frozenset({("trade", "BUY"), ("trade", "SELL")})


class WealthsimpleAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("wealthsimple"),
        display_name="Wealthsimple",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Wealthsimple crypto activity exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "wealthsimple" in source.lower():
            return 100
        if any(item.header in {BROKER_HEADER, ACTIVITY_HEADER} for item in inventory):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("wealthsimple",),
            header_hints=(",".join(BROKER_HEADER).lower(), ",".join(ACTIVITY_HEADER).lower()),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="date_only")

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
) -> EconomicActivityDraft | IssueRecord | None:
    row = row_context.row
    if (row.get("account_type") or "").strip().lower() != "crypto":
        return None
    activity_type = (row.get("activity_type") or "").strip()
    activity_sub_type = (row.get("activity_sub_type") or "").strip()
    timestamp = _parse_date((row.get("settlement_date") or row.get("transaction_date") or "").strip())
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
    fee_legs = (
        (fee_leg(asset=currency, amount=commission),) if commission is not None and commission > Decimal("0") else ()
    )
    if activity_type.lower() == "trade" and activity_sub_type.upper() == "BUY":
        return EconomicActivityDraft(
            activity_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}",
            source=str(profile.source),
            adapter_id="wealthsimple",
            account=account_id,
            wallet=account_id,
            timestamp=timestamp,
            classification=classification(
                normalized_category="trade",
                economic_kind="spot_trade",
                projection_type="Trade",
                journal_intent="asset_exchange",
                tax_treatment_code="capital_exchange",
            ),
            description="Wealthsimple Crypto buy",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            provider_operation_key=provider_operation_key,
            legs=(
                economic_leg(direction="in", asset=symbol, amount=quantity),
                economic_leg(direction="out", asset=currency, amount=abs(net_cash_amount)),
            ),
            fee_legs=fee_legs,
        )
    if activity_type.lower() == "trade" and activity_sub_type.upper() == "SELL":
        return EconomicActivityDraft(
            activity_id=f"wealthsimple:{row_context.raw_file}:{row_context.raw_row_ref}",
            source=str(profile.source),
            adapter_id="wealthsimple",
            account=account_id,
            wallet=account_id,
            timestamp=timestamp,
            classification=classification(
                normalized_category="trade",
                economic_kind="spot_trade",
                projection_type="Trade",
                journal_intent="asset_exchange",
                tax_treatment_code="capital_exchange",
            ),
            description="Wealthsimple Crypto sell",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            provider_operation_key=provider_operation_key,
            legs=(
                economic_leg(direction="in", asset=currency, amount=abs(net_cash_amount)),
                economic_leg(direction="out", asset=symbol, amount=quantity),
            ),
            fee_legs=fee_legs,
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


def _skip_unrecognized_csv(path: Path) -> bool:
    return read_csv_header(path) not in {BROKER_HEADER, ACTIVITY_HEADER}


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).replace(tzinfo=None)
    except ValueError:
        return None


ADAPTER = WealthsimpleAdapter()
