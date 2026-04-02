"""Ronin explorer translation rules."""

# pylint: disable=too-many-lines

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.ronin.families import classified_csv_paths
from tallylot.adapters.support import (
    IssueSpec,
    ReviewSpec,
    canonical_location_id_from_identifier,
    issue_record,
    read_csv_rows,
    review_record,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    ActivitySemantics,
    EconomicActivityDraft,
    LegKind,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.domain.value_objects import format_decimal, format_timestamp, parse_decimal
from tallylot.ports.source_profiles import SourceProfile


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


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...], tuple[NormalizationReviewRecord, ...]]:
    raw_groups, raw_issues = _collect_raw_groups(profile, raw_dir)
    summary_rows, summary_issues = _collect_summary_rows(profile, raw_dir)
    drafts: list[EconomicActivityDraft] = []
    issues = [*raw_issues, *summary_issues]
    reviews: list[NormalizationReviewRecord] = []
    raw_groups_by_hash = {group[0].tx_hash: group for group in raw_groups}
    summary_by_hash: dict[str, list[RoninSummaryRow]] = {}
    for row in summary_rows:
        summary_by_hash.setdefault(row.tx_hash, []).append(row)
    summary_calibrations = _summary_time_calibrations(raw_groups_by_hash, summary_rows)
    for tx_hash in sorted(set(raw_groups_by_hash) | set(summary_by_hash)):
        raw_group = raw_groups_by_hash.get(tx_hash)
        summary_group = tuple(summary_by_hash.get(tx_hash, ()))
        if raw_group is not None:
            raw_drafts, raw_group_issues, raw_group_reviews = _translate_raw_group(
                profile,
                raw_group,
                owned_addresses=owned_addresses,
                summary_rows=summary_group,
            )
            drafts.extend(raw_drafts)
            issues.extend(raw_group_issues)
            reviews.extend(raw_group_reviews)
            continue
        summary_drafts, summary_group_issues = _translate_summary_group(
            profile,
            summary_group,
            owned_addresses=owned_addresses,
            calibrations=summary_calibrations,
        )
        drafts.extend(summary_drafts)
        issues.extend(summary_group_issues)
    return tuple(drafts), tuple(issues), tuple(reviews)


def _collect_raw_groups(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[tuple[RoninRawRow, ...], ...], tuple[IssueRecord, ...]]:
    rows_by_hash: dict[str, dict[tuple[object, ...], RoninRawRow]] = {}
    issues: list[IssueRecord] = []
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "explorer_export":
            continue
        for index, row in enumerate(read_csv_rows(path), start=2):
            parsed = _parse_raw_row(path.name, index, row)
            if parsed is None:
                issues.append(
                    _row_issue(
                        profile,
                        path.name,
                        f"row:{index}",
                        "invalid_row",
                        "Ronin explorer row is missing a supported tx hash, timestamp, or asset amount.",
                    )
                )
                continue
            rows_by_hash.setdefault(parsed.tx_hash, {})[_raw_signature(parsed)] = parsed
    groups = tuple(
        sorted(
            (
                tuple(sorted(group.values(), key=lambda row: (row.timestamp, row.path_name, row.row_index)))
                for group in rows_by_hash.values()
            ),
            key=lambda group: (group[0].timestamp, group[0].tx_hash),
        )
    )
    return groups, tuple(issues)


def _collect_summary_rows(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[RoninSummaryRow, ...], tuple[IssueRecord, ...]]:
    parsed_rows: list[RoninSummaryRow] = []
    issues: list[IssueRecord] = []
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "action_summary":
            continue
        seen_signatures: set[tuple[str, str, str, str]] = set()
        for index, row in enumerate(read_csv_rows(path), start=2):
            parsed = _parse_summary_row(path.name, index, row)
            if parsed is None:
                issues.append(
                    _row_issue(
                        profile,
                        path.name,
                        f"row:{index}",
                        "invalid_row",
                        "Ronin summary row is missing a supported tx hash, timestamp, or asset amount.",
                    )
                )
                continue
            signature = (parsed.tx_hash, parsed.action_type, parsed.asset_symbol, str(parsed.quantity))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            parsed_rows.append(parsed)
    return tuple(sorted(parsed_rows, key=lambda row: (row.local_timestamp, row.tx_hash, row.row_index))), tuple(issues)


def _translate_raw_group(
    profile: SourceProfile,
    raw_rows: tuple[RoninRawRow, ...],
    *,
    owned_addresses: set[str],
    summary_rows: tuple[RoninSummaryRow, ...],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...], tuple[NormalizationReviewRecord, ...]]:
    methods = {row.method for row in raw_rows}
    if len(methods) != 1:
        return (
            (),
            (
                _row_issue(
                    profile,
                    raw_rows[0].path_name,
                    raw_rows[0].raw_row_ref,
                    "ambiguous_raw_group",
                    f"Ronin raw rows disagree on method for tx {raw_rows[0].tx_hash}.",
                ),
            ),
            (),
        )
    method = next(iter(methods))
    if method == "restakerewards":
        if summary_rows:
            summary_drafts, summary_issues = _translate_summary_group(
                profile,
                summary_rows,
                owned_addresses=owned_addresses,
                timestamp_override=raw_rows[0].timestamp,
            )
            if summary_drafts:
                return summary_drafts, summary_issues, ()
        raw_pair_drafts = _raw_restake_pair_drafts(profile, raw_rows, owned_addresses=owned_addresses)
        if raw_pair_drafts is not None:
            return raw_pair_drafts, (), ()
        return (
            (),
            (
                _row_issue(
                    profile,
                    raw_rows[0].path_name,
                    raw_rows[0].raw_row_ref,
                    "unsupported_restake",
                    "Ronin restake rows do not match a supported raw or summary-backed pair.",
                ),
            ),
            (),
        )
    if len(raw_rows) != 1:
        return (
            (),
            (
                _row_issue(
                    profile,
                    raw_rows[0].path_name,
                    raw_rows[0].raw_row_ref,
                    "unsupported_raw_group",
                    f"Ronin emitted {len(raw_rows)} raw rows for {method}, which is not a supported grouped shape.",
                ),
            ),
            (),
        )
    drafts, issues = _translate_raw_row(profile, raw_rows[0], owned_addresses=owned_addresses)
    return drafts, issues, _fee_reviews(profile, raw_rows[0], draft_count=len(drafts))


def _translate_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    # pylint: disable=too-many-return-statements
    if row.status != "success":
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_status",
                "Ronin row is not successful.",
            ),
        )
    if row.method == "transfer":
        draft = _simple_transfer_draft(profile, row, owned_addresses=owned_addresses)
        if draft is not None:
            return (draft,), ()
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_shape",
                "Ronin transfer row does not match a supported wallet direction.",
            ),
        )
    if row.method == "stake":
        if row.from_address in owned_addresses and row.outbound_quantity > Decimal("0"):
            return (_staking_transfer_out_draft(profile, row, location_id=_ronin_location_id(row.from_address)),), ()
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_shape",
                "Ronin stake row does not match a supported wallet outflow.",
            ),
        )
    if row.method == "unstake":
        if row.to_address in owned_addresses and row.inbound_quantity > Decimal("0"):
            return (_staking_transfer_in_draft(profile, row, location_id=_ronin_location_id(row.to_address)),), ()
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_shape",
                "Ronin unstake row does not match a supported wallet inflow.",
            ),
        )
    if row.method == "claimpendingrewards":
        if row.to_address in owned_addresses and row.inbound_quantity > Decimal("0"):
            return (_staking_reward_draft(profile, row, location_id=_ronin_location_id(row.to_address)),), ()
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_shape",
                "Ronin reward row does not match a supported wallet inflow.",
            ),
        )
    if row.method == "approve":
        return (), (
            _row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_method:approve",
                "Ronin approve rows are recognized but not normalized automatically.",
            ),
        )
    return (), (
        _row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            f"unsupported_method:{row.method}",
            f"Unsupported Ronin explorer method: {row.method}",
        ),
    )


def _translate_summary_group(
    profile: SourceProfile,
    summary_rows: tuple[RoninSummaryRow, ...],
    *,
    owned_addresses: set[str],
    calibrations: tuple[tuple[datetime, timedelta], ...] = (),
    timestamp_override: datetime | None = None,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    # pylint: disable=too-many-return-statements
    if not summary_rows:
        return (), ()
    local_timestamps = {row.local_timestamp for row in summary_rows}
    if len(local_timestamps) != 1:
        return (), (
            _row_issue(
                profile,
                summary_rows[0].path_name,
                summary_rows[0].raw_row_ref,
                "ambiguous_summary_timestamp",
                f"Ronin summary rows disagree on timestamp for tx {summary_rows[0].tx_hash}.",
            ),
        )
    timestamp = timestamp_override or _infer_summary_utc_timestamp(summary_rows[0].local_timestamp, calibrations)
    if timestamp is None:
        return (), (
            _row_issue(
                profile,
                summary_rows[0].path_name,
                summary_rows[0].raw_row_ref,
                "summary_timestamp_unresolved",
                "Ronin summary rows require a companion raw export to infer authoritative UTC timestamps.",
            ),
        )
    action_types = {row.action_type for row in summary_rows}
    if len(action_types) != 1:
        return (), (
            _row_issue(
                profile,
                summary_rows[0].path_name,
                summary_rows[0].raw_row_ref,
                "ambiguous_summary_group",
                f"Ronin summary rows disagree on action type for tx {summary_rows[0].tx_hash}.",
            ),
        )
    action_type = next(iter(action_types))
    if action_type == "transfer" and len(summary_rows) == 1:
        row = summary_rows[0]
        if row.quantity > Decimal("0") and row.to_address in owned_addresses:
            return (
                _summary_transfer_draft(
                    profile,
                    row,
                    SummaryDraftContext(
                        timestamp=timestamp,
                        location_id=_ronin_location_id(row.to_address),
                        quantity=row.quantity,
                        semantics=_transfer_in_semantics(),
                    ),
                ),
            ), ()
        if row.quantity < Decimal("0") and row.from_address in owned_addresses:
            return (
                _summary_transfer_draft(
                    profile,
                    row,
                    SummaryDraftContext(
                        timestamp=timestamp,
                        location_id=_ronin_location_id(row.from_address),
                        quantity=row.quantity,
                        semantics=_transfer_out_semantics(),
                    ),
                ),
            ), ()
    if action_type == "stakeaxs" and len(summary_rows) == 1:
        row = summary_rows[0]
        if row.quantity < Decimal("0") and row.from_address in owned_addresses:
            return (
                _summary_transfer_draft(
                    profile,
                    row,
                    SummaryDraftContext(
                        timestamp=timestamp,
                        location_id=_ronin_location_id(row.from_address),
                        quantity=row.quantity,
                        semantics=_staking_out_semantics(),
                    ),
                ),
            ), ()
    if action_type == "restakeaxs" and len(summary_rows) == 2:
        positive_row = next((row for row in summary_rows if row.quantity > Decimal("0")), None)
        negative_row = next((row for row in summary_rows if row.quantity < Decimal("0")), None)
        if _is_supported_restake_pair(positive_row, negative_row, owned_addresses):
            assert positive_row is not None
            assert negative_row is not None
            return (
                _summary_transfer_draft(
                    profile,
                    positive_row,
                    SummaryDraftContext(
                        timestamp=timestamp,
                        location_id=_ronin_location_id(positive_row.to_address),
                        quantity=positive_row.quantity,
                        semantics=_staking_reward_semantics(),
                    ),
                ),
                _summary_transfer_draft(
                    profile,
                    negative_row,
                    SummaryDraftContext(
                        timestamp=timestamp,
                        location_id=_ronin_location_id(negative_row.from_address),
                        quantity=negative_row.quantity,
                        semantics=_staking_out_semantics(),
                    ),
                ),
            ), ()
    return (), (
        _row_issue(
            profile,
            summary_rows[0].path_name,
            summary_rows[0].raw_row_ref,
            "unsupported_summary_group",
            f"Ronin summary rows do not match a supported {action_type} pattern.",
        ),
    )


def _simple_transfer_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
) -> EconomicActivityDraft | None:
    if (
        row.inbound_quantity > Decimal("0")
        and row.outbound_quantity == Decimal("0")
        and row.to_address in owned_addresses
    ):
        return _transfer_draft(
            profile,
            row=row,
            location_id=_ronin_location_id(row.to_address),
            quantity=row.inbound_quantity,
            semantics=_transfer_in_semantics(),
        )
    if (
        row.outbound_quantity > Decimal("0")
        and row.inbound_quantity == Decimal("0")
        and row.from_address in owned_addresses
    ):
        return _transfer_draft(
            profile,
            row=row,
            location_id=_ronin_location_id(row.from_address),
            quantity=-row.outbound_quantity,
            semantics=_transfer_out_semantics(),
        )
    return None


def _transfer_draft(
    profile: SourceProfile,
    *,
    row: RoninRawRow,
    location_id: LocationId,
    quantity: Decimal,
    semantics: ActivitySemantics,
) -> EconomicActivityDraft:
    primary_leg_id = "primary_in" if quantity > Decimal("0") else "primary_out"
    return EconomicActivityDraft(
        activity_id=f"ronin:{row.path_name}:{row.tx_hash}",
        source=str(profile.source),
        adapter_id="ronin",
        location_id=location_id,
        timestamp=row.timestamp,
        classification=semantics.to_classification(),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=f"Ronin {row.method} - {row.tx_hash}",
        raw_file=row.path_name,
        raw_row_ref=row.raw_row_ref,
        tx_hash=row.tx_hash,
        provider_operation_key=row.method,
        legs=(
            economic_leg(
                leg_id=primary_leg_id,
                kind=LegKind.PRIMARY,
                quantity=quantity,
                instrument=symbol_claim(row.asset_symbol, venue="ronin"),
            ),
        ),
    )


def _staking_transfer_out_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
) -> EconomicActivityDraft:
    return _transfer_draft(
        profile,
        row=row,
        location_id=location_id,
        quantity=-row.outbound_quantity,
        semantics=_staking_out_semantics(),
    )


def _staking_reward_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
) -> EconomicActivityDraft:
    return _transfer_draft(
        profile,
        row=row,
        location_id=location_id,
        quantity=row.inbound_quantity,
        semantics=_staking_reward_semantics(),
    )


def _staking_transfer_in_draft(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    location_id: LocationId,
) -> EconomicActivityDraft:
    return _transfer_draft(
        profile,
        row=row,
        location_id=location_id,
        quantity=row.inbound_quantity,
        semantics=_staking_in_semantics(),
    )


def _summary_transfer_draft(
    profile: SourceProfile,
    row: RoninSummaryRow,
    context: SummaryDraftContext,
) -> EconomicActivityDraft:
    primary_leg_id = "primary_in" if context.quantity > Decimal("0") else "primary_out"
    return EconomicActivityDraft(
        activity_id=f"ronin:{row.path_name}:{row.tx_hash}:{row.row_index}",
        source=str(profile.source),
        adapter_id="ronin",
        location_id=context.location_id,
        timestamp=context.timestamp,
        classification=context.semantics.to_classification(),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=f"Ronin {row.action_type} - {row.tx_hash}",
        raw_file=row.path_name,
        raw_row_ref=row.raw_row_ref,
        tx_hash=row.tx_hash,
        provider_operation_key=row.action_type,
        legs=(
            economic_leg(
                leg_id=primary_leg_id,
                kind=LegKind.PRIMARY,
                quantity=context.quantity,
                instrument=symbol_claim(row.asset_symbol, venue="ronin"),
            ),
        ),
    )


def _parse_raw_row(path_name: str, row_index: int, row: dict[str, str]) -> RoninRawRow | None:
    tx_hash = (row.get("Txhash") or "").strip()
    timestamp = _parse_utc_timestamp((row.get("DateTime") or "").strip())
    from_address = _ronin_address((row.get("From") or "").strip())
    to_address = _ronin_address((row.get("To") or "").strip())
    method = (row.get("Method") or "").strip().lower()
    asset_symbol = _asset_symbol((row.get("Token / Collectibles") or "").strip())
    inbound_quantity = parse_decimal((row.get("Value in") or "").strip()) or Decimal("0")
    outbound_quantity = parse_decimal((row.get("Value out") or "").strip()) or Decimal("0")
    fee = parse_decimal((row.get("TxnFee(RON)") or "").strip()) or Decimal("0")
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
        fee=fee,
        status=status,
    )


def _raw_signature(row: RoninRawRow) -> tuple[object, ...]:
    return (
        row.tx_hash,
        row.timestamp,
        row.from_address,
        row.to_address,
        row.method,
        row.asset_symbol,
        row.inbound_quantity,
        row.outbound_quantity,
        row.fee,
        row.status,
    )


def _parse_summary_row(path_name: str, row_index: int, row: dict[str, str]) -> RoninSummaryRow | None:
    tx_hash = (row.get("TxnHash") or "").strip()
    local_timestamp = _parse_summary_local_timestamp((row.get("Timestamp") or "").strip())
    action_type = (row.get("ActionType") or "").strip().lower()
    ronin_address = _ronin_address((row.get("RoninAddress") or "").strip())
    from_address = _ronin_address((row.get("From") or "").strip())
    to_address = _ronin_address((row.get("To") or "").strip())
    asset_symbol, quantity = _summary_asset_quantity(row)
    if not tx_hash or local_timestamp is None or not asset_symbol or quantity == Decimal("0"):
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


def _transfer_in_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
        projection_hint=ProjectionHint.DEPOSIT,
        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
    )


def _transfer_out_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
        projection_hint=ProjectionHint.WITHDRAWAL,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
    )


def _staking_out_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
        projection_hint=ProjectionHint.WITHDRAWAL,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
    )


def _staking_reward_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_REWARD,
        projection_hint=ProjectionHint.STAKING,
        accounting_intent_hint=AccountingIntentHint.INCOME_RECOGNITION,
        tax_treatment_hint=TaxTreatmentHint.STAKING_INCOME,
    )


def _staking_in_semantics() -> ActivitySemantics:
    return ActivitySemantics(
        economic_kind=EconomicKind.STAKING_TRANSFER_IN,
        projection_hint=ProjectionHint.DEPOSIT,
        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
    )


def _is_supported_restake_pair(
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


def _summary_time_calibrations(
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


def _infer_summary_utc_timestamp(
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


def _raw_restake_pair_drafts(
    profile: SourceProfile,
    raw_rows: tuple[RoninRawRow, ...],
    *,
    owned_addresses: set[str],
) -> tuple[EconomicActivityDraft, ...] | None:
    if len(raw_rows) != 2:
        return None
    reward_row = next(
        (
            row
            for row in raw_rows
            if row.inbound_quantity > Decimal("0")
            and row.outbound_quantity == Decimal("0")
            and row.to_address in owned_addresses
        ),
        None,
    )
    stake_row = next(
        (
            row
            for row in raw_rows
            if row.outbound_quantity > Decimal("0")
            and row.inbound_quantity == Decimal("0")
            and row.from_address in owned_addresses
        ),
        None,
    )
    if reward_row is None or stake_row is None:
        return None
    if reward_row.asset_symbol != stake_row.asset_symbol:
        return None
    return (
        _staking_reward_draft(
            profile,
            reward_row,
            location_id=_ronin_location_id(reward_row.to_address),
        ),
        _staking_transfer_out_draft(
            profile,
            stake_row,
            location_id=_ronin_location_id(stake_row.from_address),
        ),
    )


def _fee_reviews(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    draft_count: int,
) -> tuple[NormalizationReviewRecord, ...]:
    if draft_count == 0 or row.fee <= Decimal("0"):
        return ()
    return (
        review_record(
            ReviewSpec(
                review_id=f"ronin:{row.path_name}:{row.raw_row_ref}:non_authoritative_fee",
                source=str(profile.source),
                adapter_id="ronin",
                scope="row",
                kind="non_authoritative_fee",
                message=(
                    "Ronin explorer TxnFee(RON) is a display-rounded export value and was omitted from "
                    "the normalized fact until authoritative fee evidence is available."
                ),
                context_timestamp=format_timestamp(row.timestamp),
                raw_file=row.path_name,
                raw_row_ref=row.raw_row_ref,
                field_name="TxnFee(RON)",
                original_value=format_decimal(row.fee),
                normalized_value="",
            )
        ),
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


def _ronin_location_id(address: str) -> LocationId:
    return canonical_location_id_from_identifier("evm_address", address, network_scope="ronin")


def _row_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    issue_id_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"ronin:{raw_file}:{raw_row_ref}:{issue_id_suffix}",
            source=str(profile.source),
            adapter_id="ronin",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )
