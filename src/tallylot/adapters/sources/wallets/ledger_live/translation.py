"""Ledger Live grouped operation translation helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import IssueSpec, ReviewSpec, issue_record, review_record
from tallylot.adapters.support import (
    location_id_from_parts,
    matching_file_paths,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    EconomicActivityDraft,
    EconomicLegDraft,
    FactLegPolicy,
    LegKind,
    classification,
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
from tallylot.ports.source_profiles import SourceProfile


@dataclass(frozen=True)
class _SingleTypeTranslationSpec:
    operation_key: str
    economic_kind: EconomicKind
    projection_hint: ProjectionHint | None
    accounting_intent_hint: AccountingIntentHint
    tax_treatment_hint: TaxTreatmentHint
    leg_id: str
    quantity_sign: Decimal
    review_kind: str = ""
    review_message: str = ""
    review_original_value: str = ""


@dataclass(frozen=True)
class _OperationGroup:
    operation_hash: str
    raw_file: str
    raw_row_ref: str
    operation_types: frozenset[str]
    rows_by_type: dict[str, tuple[tuple[str, dict[str, str]], ...]]

    def rows(self, operation_type: str) -> tuple[tuple[str, dict[str, str]], ...]:
        return self.rows_by_type.get(operation_type, ())


_SINGLE_TYPE_TRANSLATIONS = {
    "IN": _SingleTypeTranslationSpec(
        operation_key="ledger_live_in",
        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
        projection_hint=ProjectionHint.DEPOSIT,
        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        leg_id="primary_in",
        quantity_sign=Decimal("1"),
    ),
    "OUT": _SingleTypeTranslationSpec(
        operation_key="ledger_live_out",
        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
        projection_hint=ProjectionHint.WITHDRAWAL,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        leg_id="primary_out",
        quantity_sign=Decimal("-1"),
    ),
    "FEES": _SingleTypeTranslationSpec(
        operation_key="ledger_live_fee",
        economic_kind=EconomicKind.CASH_EXPENSE,
        projection_hint=ProjectionHint.EXPENSE_NON_TAXABLE,
        accounting_intent_hint=AccountingIntentHint.EXPENSE_RECOGNITION,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_EXPENSE,
        leg_id="primary_fee",
        quantity_sign=Decimal("-1"),
    ),
    "DELEGATE": _SingleTypeTranslationSpec(
        operation_key="ledger_live_delegate",
        economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
        projection_hint=ProjectionHint.STAKING,
        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        leg_id="primary_delegate",
        quantity_sign=Decimal("-1"),
        review_kind="staking_delegate_incomplete",
        review_message=(
            "Ledger Live delegate export proves the debited asset movement but "
            "not the external staking-side state or validator position."
        ),
        review_original_value="DELEGATE",
    ),
}


def translate_operations(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[
    tuple[EconomicActivityDraft, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    operations_by_hash: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for path in matching_file_paths(raw_dir):
        for index, row in enumerate(read_csv_rows(path), start=2):
            operation_hash = (
                row.get("Operation Hash") or row.get("Transaction ID") or ""
            ).strip()
            if not operation_hash:
                continue
            operations_by_hash[operation_hash].append((f"{path.name}:row:{index}", row))

    for operation_hash, grouped_rows in sorted(operations_by_hash.items()):
        operation_group = _build_operation_group(operation_hash, tuple(grouped_rows))
        group_drafts, group_issues, group_reviews = _translate_operation_group(
            profile, operation_group
        )
        drafts.extend(group_drafts)
        issues.extend(group_issues)
        reviews.extend(group_reviews)
    return tuple(drafts), tuple(issues), tuple(reviews)


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def _swap_policy(fee_amount: Decimal, fee_asset: str) -> FactLegPolicy:
    if fee_amount > 0 and fee_asset:
        return TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY
    return TWO_SIDED_PRIMARY_EXCHANGE_POLICY


def _charge_legs(
    fee_amount: Decimal, fee_asset: str, *, attributed_to_leg_id: str
) -> tuple[EconomicLegDraft, ...]:
    if fee_amount <= Decimal("0") or not fee_asset:
        return ()
    return (
        economic_leg(
            leg_id="charge",
            kind=LegKind.CHARGE,
            quantity=-fee_amount,
            instrument=symbol_claim(fee_asset.strip().upper(), venue="ledger_live"),
            subtype="network_fee",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )


def _build_operation_group(
    operation_hash: str,
    grouped_rows: tuple[tuple[str, dict[str, str]], ...],
) -> _OperationGroup:
    grouped: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for raw_ref, row in grouped_rows:
        grouped[(row.get("Operation Type", "") or "").strip().upper()].append(
            (raw_ref, row)
        )
    raw_file = grouped_rows[0][0].split(":row:", maxsplit=1)[0]
    raw_row_ref = ";".join(
        f"{raw_file}:{ref.split(':', maxsplit=1)[1]}" for ref, _ in grouped_rows
    )
    rows_by_type = {
        operation_type: tuple(rows) for operation_type, rows in grouped.items() if rows
    }
    return _OperationGroup(
        operation_hash=operation_hash,
        raw_file=raw_file,
        raw_row_ref=raw_row_ref,
        operation_types=frozenset(rows_by_type),
        rows_by_type=rows_by_type,
    )


def _translate_operation_group(
    profile: SourceProfile,
    group: _OperationGroup,
) -> tuple[
    tuple[EconomicActivityDraft, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    if len(group.rows("FEES")) > 1:
        return (), (_unsupported_group_issue_for_group(profile, group),), ()
    single_type_result = _translate_single_type_group(profile, group)
    if single_type_result is not None:
        return single_type_result
    swap_draft = _translate_swap_group(profile, group)
    if swap_draft is not None:
        return (swap_draft,), (), ()
    return (), (_unsupported_group_issue_for_group(profile, group),), ()


def _translate_single_type_group(
    profile: SourceProfile,
    group: _OperationGroup,
) -> (
    tuple[
        tuple[EconomicActivityDraft, ...],
        tuple[IssueRecord, ...],
        tuple[NormalizationReviewRecord, ...],
    ]
    | None
):
    if len(group.operation_types) != 1:
        return None
    operation_type = next(iter(group.operation_types))
    spec = _SINGLE_TYPE_TRANSLATIONS.get(operation_type)
    if spec is None:
        return None
    rows = group.rows(operation_type)
    if len(rows) != 1:
        return (), (_unsupported_group_issue_for_group(profile, group),), ()
    draft = _single_primary_draft(
        profile,
        raw_file=group.raw_file,
        raw_row_ref=group.raw_row_ref,
        operation_hash=group.operation_hash,
        row=rows[0][1],
        operation_key=spec.operation_key,
        economic_kind=spec.economic_kind,
        projection_hint=spec.projection_hint,
        accounting_intent_hint=spec.accounting_intent_hint,
        tax_treatment_hint=spec.tax_treatment_hint,
        leg_id=spec.leg_id,
        quantity_sign=spec.quantity_sign,
    )
    if draft is None:
        return (), (_unsupported_group_issue_for_group(profile, group),), ()
    reviews = () if not spec.review_kind else (_delegate_review(profile, group, spec),)
    return (draft,), (), reviews


def _translate_swap_group(
    profile: SourceProfile,
    group: _OperationGroup,
) -> EconomicActivityDraft | None:
    if group.operation_types not in (
        frozenset({"IN", "OUT"}),
        frozenset({"IN", "OUT", "FEES"}),
    ):
        return None
    inbound_rows = group.rows("IN")
    outbound_rows = group.rows("OUT")
    if len(inbound_rows) != 1 or len(outbound_rows) != 1:
        return None
    _, inbound = inbound_rows[0]
    _, outbound = outbound_rows[0]
    fee_rows = group.rows("FEES")
    fee_row = fee_rows[0][1] if fee_rows else None
    timestamp = parse_timestamp((inbound.get("Operation Date") or "").strip())
    account_label = (
        inbound.get("Account Name") or outbound.get("Account Name") or ""
    ).strip()
    fee_amount = Decimal((fee_row or {}).get("Operation Amount") or "0")
    fee_asset = (fee_row or {}).get("Currency Ticker") or ""
    return EconomicActivityDraft(
        activity_id=f"ledger_live:{group.raw_file}:{group.operation_hash}",
        source=str(profile.source),
        adapter_id="ledger_live",
        location_id=location_id_from_parts(
            str(profile.source), account_label or group.operation_hash
        ),
        timestamp=timestamp,
        classification=classification(
            economic_kind=EconomicKind.ASSET_SWAP,
            projection_hint=ProjectionHint.TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
        ),
        leg_policy=_swap_policy(fee_amount, fee_asset),
        description=account_label,
        raw_file=group.raw_file,
        raw_row_ref=group.raw_row_ref,
        tx_hash=group.operation_hash,
        provider_operation_key="ledger_live_swap",
        operation_group_id=group.operation_hash,
        legs=(
            economic_leg(
                leg_id="primary_in",
                kind=LegKind.PRIMARY,
                quantity=Decimal((inbound.get("Operation Amount") or "0").strip()),
                instrument=symbol_claim(
                    (inbound.get("Currency Ticker") or "").strip().upper(),
                    venue="ledger_live",
                ),
            ),
            economic_leg(
                leg_id="primary_out",
                kind=LegKind.PRIMARY,
                quantity=-Decimal((outbound.get("Operation Amount") or "0").strip()),
                instrument=symbol_claim(
                    (outbound.get("Currency Ticker") or "").strip().upper(),
                    venue="ledger_live",
                ),
            ),
            *_charge_legs(fee_amount, fee_asset, attributed_to_leg_id="primary_out"),
        ),
    )


def _single_primary_draft(  # pylint: disable=too-many-arguments
    profile: SourceProfile,
    *,
    raw_file: str,
    raw_row_ref: str,
    operation_hash: str,
    row: dict[str, str],
    operation_key: str,
    economic_kind: EconomicKind,
    projection_hint: ProjectionHint | None,
    accounting_intent_hint: AccountingIntentHint,
    tax_treatment_hint: TaxTreatmentHint,
    leg_id: str,
    quantity_sign: Decimal,
) -> EconomicActivityDraft | None:
    amount_text = (row.get("Operation Amount") or "").strip()
    asset_symbol = (row.get("Currency Ticker") or "").strip().upper()
    account_label = (row.get("Account Name") or "").strip()
    if not amount_text or not asset_symbol:
        return None
    amount = Decimal(amount_text)
    if amount <= Decimal("0"):
        return None
    return EconomicActivityDraft(
        activity_id=f"ledger_live:{raw_file}:{operation_hash}",
        source=str(profile.source),
        adapter_id="ledger_live",
        location_id=location_id_from_parts(
            str(profile.source), account_label or operation_hash
        ),
        timestamp=parse_timestamp((row.get("Operation Date") or "").strip()),
        classification=classification(
            economic_kind=economic_kind,
            projection_hint=projection_hint,
            accounting_intent_hint=accounting_intent_hint,
            tax_treatment_hint=tax_treatment_hint,
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=account_label,
        raw_file=raw_file,
        raw_row_ref=raw_row_ref,
        tx_hash=operation_hash,
        provider_operation_key=operation_key,
        operation_group_id=operation_hash,
        legs=(
            economic_leg(
                leg_id=leg_id,
                kind=LegKind.PRIMARY,
                quantity=amount * quantity_sign,
                instrument=symbol_claim(asset_symbol, venue="ledger_live"),
            ),
        ),
    )


def _delegate_review(
    profile: SourceProfile,
    group: _OperationGroup,
    spec: _SingleTypeTranslationSpec,
) -> NormalizationReviewRecord:
    return review_record(
        ReviewSpec(
            review_id=(
                f"ledger_live:{group.raw_file}:{group.operation_hash}:"
                "delegate_incomplete"
            ),
            source=str(profile.source),
            adapter_id="ledger_live",
            scope="activity",
            kind=spec.review_kind,
            message=spec.review_message,
            raw_file=group.raw_file,
            raw_row_ref=group.raw_row_ref,
            field_name="operation_type",
            original_value=spec.review_original_value,
        )
    )


def _unsupported_group_issue_for_group(
    profile: SourceProfile,
    group: _OperationGroup,
) -> IssueRecord:
    return _unsupported_group_issue(
        profile,
        group.raw_file,
        group.raw_row_ref,
        group.operation_hash,
    )


def _unsupported_group_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    operation_hash: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"ledger_live:{raw_file}:{operation_hash}:unsupported_group",
            source=str(profile.source),
            adapter_id="ledger_live",
            severity="medium",
            kind="unsupported_group",
            message="Ledger Live grouped operation has an unsupported or ambiguous leg shape.",
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )
