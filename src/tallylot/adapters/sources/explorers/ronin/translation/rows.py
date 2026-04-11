"""Ronin explorer row models and parsing rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from tallylot.adapters.support import (
    DecimalPrecisionExpectation,
    ReviewSpec,
    check_decimal_precision,
    review_record,
)
from tallylot.adapters.support.drafts import ActivitySemantics
from tallylot.domain.issues import NormalizationReviewRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.domain.value_objects import format_timestamp, parse_decimal
from tallylot.ports.source_profiles import SourceProfile

ZERO = Decimal("0")


@dataclass(frozen=True)
class RoninRawRow:
    path_name: str
    row_index: int
    tx_hash: str
    timestamp: datetime
    from_address: str
    to_address: str
    method: str
    asset_symbol: str
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    fee_text: str
    fee: Decimal
    status: str

    @property
    def raw_row_ref(self) -> str:
        return f"row:{self.row_index}"


@dataclass(frozen=True)
class RoninSummaryRow:
    path_name: str
    row_index: int
    tx_hash: str
    local_timestamp: datetime
    action_type: str
    ronin_address: str
    from_address: str
    to_address: str
    asset_symbol: str
    quantity: Decimal

    @property
    def raw_row_ref(self) -> str:
        return f"row:{self.row_index}"


@dataclass(frozen=True)
class SummaryDraftContext:
    timestamp: datetime
    location_id: LocationId
    quantity: Decimal
    semantics: ActivitySemantics


@dataclass(frozen=True)
class RoninRawDraftContext:
    source: str
    location_id: LocationId
    semantics: ActivitySemantics
    fee: Decimal = ZERO


@dataclass(frozen=True)
class RoninFeeResolution:
    authoritative_fee: Decimal = ZERO
    review: NormalizationReviewRecord | None = None


# Current Ronin explorer CSV exports can round some newly downloaded
# historical-activity fees to six fractional digits. Treat only 9+ digit
# non-zero fees as authoritative.
RONIN_FEE_PRECISION = DecimalPrecisionExpectation(
    minimum_fraction_digits=9, allow_zero=True
)


def parse_raw_row(
    path_name: str, row_index: int, row: dict[str, str]
) -> RoninRawRow | None:
    tx_hash = (row.get("Txhash") or "").strip()
    timestamp = _parse_utc_timestamp((row.get("DateTime") or "").strip())
    from_address = _ronin_address((row.get("From") or "").strip())
    to_address = _ronin_address((row.get("To") or "").strip())
    method = (row.get("Method") or "").strip().lower()
    asset_symbol = _asset_symbol((row.get("Token / Collectibles") or "").strip())
    inbound_quantity = parse_decimal((row.get("Value in") or "").strip()) or Decimal(
        "0"
    )
    outbound_quantity = parse_decimal((row.get("Value out") or "").strip()) or Decimal(
        "0"
    )
    fee_text = (row.get("TxnFee(RON)") or "").strip()
    fee = parse_decimal(fee_text) or Decimal("0")
    status = (row.get("Status") or "").strip().lower()
    if not tx_hash or timestamp is None or not asset_symbol:
        return None
    return RoninRawRow(
        path_name=path_name,
        row_index=row_index,
        tx_hash=tx_hash,
        timestamp=timestamp,
        from_address=from_address,
        to_address=to_address,
        method=method,
        asset_symbol=asset_symbol,
        inbound_quantity=inbound_quantity,
        outbound_quantity=outbound_quantity,
        fee_text=fee_text,
        fee=fee,
        status=status,
    )


def raw_signature(row: RoninRawRow) -> tuple[object, ...]:
    return (
        row.tx_hash,
        row.timestamp,
        row.from_address,
        row.to_address,
        row.method,
        row.asset_symbol,
        row.inbound_quantity,
        row.outbound_quantity,
        row.fee_text,
        row.fee,
        row.status,
    )


def parse_summary_row(
    path_name: str, row_index: int, row: dict[str, str]
) -> RoninSummaryRow | None:
    tx_hash = (row.get("TxnHash") or "").strip()
    local_timestamp = _parse_summary_local_timestamp(
        (row.get("Timestamp") or "").strip()
    )
    action_type = (row.get("ActionType") or "").strip().lower()
    ronin_address = _ronin_address((row.get("RoninAddress") or "").strip())
    from_address = _ronin_address((row.get("From") or "").strip())
    to_address = _ronin_address((row.get("To") or "").strip())
    asset_symbol, quantity = _summary_asset_quantity(row)
    if (
        not tx_hash
        or local_timestamp is None
        or not asset_symbol
        or quantity == Decimal("0")
    ):
        return None
    return RoninSummaryRow(
        path_name=path_name,
        row_index=row_index,
        tx_hash=tx_hash,
        local_timestamp=local_timestamp,
        action_type=action_type,
        ronin_address=ronin_address,
        from_address=from_address,
        to_address=to_address,
        asset_symbol=asset_symbol,
        quantity=quantity,
    )


def _summary_asset_quantity(row: dict[str, str]) -> tuple[str, Decimal]:
    for symbol in ("AXS", "RON", "SLP", "USDC", "ETH"):
        quantity = parse_decimal((row.get(symbol) or "").strip()) or Decimal("0")
        if quantity != Decimal("0"):
            return symbol, quantity
    return "", Decimal("0")


def transfer_in_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
        projection_hint=ProjectionHint.DEPOSIT,
        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
    )


def transfer_out_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
        projection_hint=ProjectionHint.WITHDRAWAL,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
    )


def staking_out_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
        projection_hint=ProjectionHint.WITHDRAWAL,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
    )


def staking_reward_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_REWARD,
        projection_hint=ProjectionHint.STAKING,
        accounting_intent_hint=AccountingIntentHint.INCOME_RECOGNITION,
        tax_treatment_hint=TaxTreatmentHint.STAKING_INCOME,
    )


def staking_in_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_TRANSFER_IN,
        projection_hint=ProjectionHint.DEPOSIT,
        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
    )


def is_supported_restake_pair(
    positive_row: RoninSummaryRow | None,
    negative_row: RoninSummaryRow | None,
    owned_addresses: set[str],
) -> bool:
    if positive_row is None or negative_row is None:
        return False
    return (
        positive_row.asset_symbol == negative_row.asset_symbol
        and positive_row.quantity == abs(negative_row.quantity)
        and positive_row.to_address in owned_addresses
        and negative_row.from_address in owned_addresses
    )


def summary_time_calibrations(
    raw_groups_by_hash: dict[str, tuple[RoninRawRow, ...]],
    summary_rows: tuple[RoninSummaryRow, ...],
) -> tuple[tuple[datetime, timedelta], ...]:
    calibrations: dict[tuple[datetime, timedelta], None] = {}
    for row in summary_rows:
        raw_group = raw_groups_by_hash.get(row.tx_hash)
        if not raw_group:
            continue
        offset = raw_group[0].timestamp.replace(tzinfo=None) - row.local_timestamp
        calibrations[(row.local_timestamp, offset)] = None
    return tuple(sorted(calibrations, key=lambda item: item[0]))


def infer_summary_utc_timestamp(
    local_timestamp: datetime,
    calibrations: tuple[tuple[datetime, timedelta], ...],
) -> datetime | None:
    if not calibrations:
        return None
    _, offset = min(
        calibrations,
        key=lambda item: abs((item[0] - local_timestamp).total_seconds()),
    )
    return (local_timestamp + offset).replace(tzinfo=UTC)


def resolve_fee(
    profile: SourceProfile,
    rows: tuple[RoninRawRow, ...],
) -> RoninFeeResolution:
    fee_rows = [row for row in rows if row.fee > Decimal("0")]
    if not fee_rows:
        return RoninFeeResolution()
    row = fee_rows[0]
    precision_check = check_decimal_precision(
        row.fee_text, expectation=RONIN_FEE_PRECISION
    )
    if precision_check is not None and precision_check.satisfies_expectation:
        return RoninFeeResolution(authoritative_fee=row.fee)
    mismatch = (
        precision_check.mismatch_message
        if precision_check is not None
        else RONIN_FEE_PRECISION.describe()
    )
    return RoninFeeResolution(
        review=review_record(
            ReviewSpec(
                review_id=f"ronin:{row.path_name}:{row.raw_row_ref}:insufficient_decimal_precision",
                source=str(profile.source),
                adapter_id="ronin",
                scope="row",
                kind="insufficient_decimal_precision",
                message=(
                    "Ronin explorer TxnFee(RON) did not expose enough fractional digits to prove an authoritative "
                    "network fee. The fee was omitted from the normalized fact. "
                    f"Observed value {row.fee_text} {mismatch}."
                ),
                context_timestamp=format_timestamp(row.timestamp),
                raw_file=row.path_name,
                raw_row_ref=row.raw_row_ref,
                field_name="TxnFee(RON)",
                original_value=row.fee_text,
                normalized_value="",
            )
        )
    )


def _asset_symbol(token_name: str) -> str:
    return {
        "axie infinity shard": "AXS",
        "ron": "RON",
    }.get(token_name.strip().lower(), token_name.strip().upper())


def _ronin_address(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("ronin:"):
        suffix = normalized.split(":", 1)[1]
        return f"0x{suffix}"
    return normalized


def _parse_utc_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_summary_local_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%d/%m/%Y, %H:%M:%S", "%m/%d/%Y, %H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt).replace(tzinfo=UTC)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def ronin_location_id(address: str) -> LocationId:
    return LocationId(f"evm:ronin:{address.strip().lower()}")
