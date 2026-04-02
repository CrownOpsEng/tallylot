"""Wealthsimple crypto export adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import (
    CsvRowContext,
    IssueSpec,
    collect_csv_row_results,
    issue_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    read_csv_header,
)
from tallylot.adapters.support.drafts import (
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
    translation_batch_from_drafts,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import EconomicKind, FactDirection, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import WalletInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft, SourceTranslationBatch

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
    provider_operation_key: str


class WealthsimpleAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("wealthsimple"),
        display_name="Wealthsimple",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}),
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

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        drafts, issues = collect_csv_row_results(
            raw_dir,
            lambda row_context: _normalize_row(profile, row_context),
            skip_file=_skip_unrecognized_csv,
        )
        return translation_batch_from_drafts(
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


def _charge_legs(
    commission: Decimal | None,
    currency: str,
    *,
    attributed_to_direction: FactDirection,
) -> tuple[EconomicLegDraft, ...]:
    if commission is None or commission <= Decimal("0"):
        return ()
    return (
        economic_leg(
            direction="out",
            kind=LegKind.CHARGE,
            asset=currency,
            amount=commission,
            subtype="commission",
            attributed_to_direction=attributed_to_direction,
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
        account=context.account_id,
        wallet=context.account_id,
        timestamp=context.timestamp,
        classification=classification(
            economic_kind=EconomicKind.SPOT_TRADE,
            projection_type=ProjectionType.TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
        ),
        leg_policy=_trade_policy(context.commission),
        description=f"Wealthsimple Crypto {trade_side_lower}",
        raw_file=row_context.raw_file,
        raw_row_ref=row_context.raw_row_ref,
        provider_operation_key=context.provider_operation_key,
        legs=(
            economic_leg(
                direction="in" if trade_side == "BUY" else "out",
                kind=LegKind.PRIMARY,
                asset=context.symbol,
                amount=context.quantity,
            ),
            economic_leg(
                direction="out" if trade_side == "BUY" else "in",
                kind=LegKind.PRIMARY,
                asset=context.currency,
                amount=cash_amount,
            ),
            *_charge_legs(
                context.commission,
                context.currency,
                attributed_to_direction="out" if trade_side == "BUY" else "in",
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
    return FactLegPolicy(limits=(LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1),))


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
