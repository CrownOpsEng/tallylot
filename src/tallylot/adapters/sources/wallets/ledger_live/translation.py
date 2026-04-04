"""Ledger Live grouped operation translation helpers."""

from __future__ import annotations

from collections import defaultdict
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
        rows_by_type: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        for raw_ref, row in grouped_rows:
            rows_by_type[(row.get("Operation Type", "") or "").strip().upper()].append(
                (raw_ref, row)
            )
        inbound_rows = rows_by_type.get("IN", [])
        outbound_rows = rows_by_type.get("OUT", [])
        fee_rows = rows_by_type.get("FEES", [])
        delegate_rows = rows_by_type.get("DELEGATE", [])
        raw_file = grouped_rows[0][0].split(":row:", maxsplit=1)[0]
        raw_row_ref = ";".join(
            f"{raw_file}:{ref.split(':', maxsplit=1)[1]}" for ref, _ in grouped_rows
        )
        operation_types = {
            operation_type for operation_type, rows in rows_by_type.items() if rows
        }
        if len(fee_rows) > 1:
            issues.append(
                _unsupported_group_issue(profile, raw_file, raw_row_ref, operation_hash)
            )
            continue
        if operation_types == {"IN"} and len(inbound_rows) == 1:
            draft = _single_primary_draft(
                profile,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                operation_hash=operation_hash,
                row=inbound_rows[0][1],
                operation_key="ledger_live_in",
                economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                leg_id="primary_in",
                quantity_sign=Decimal("1"),
            )
            if draft is None:
                issues.append(
                    _unsupported_group_issue(
                        profile, raw_file, raw_row_ref, operation_hash
                    )
                )
                continue
            drafts.append(draft)
            continue
        if operation_types == {"OUT"} and len(outbound_rows) == 1:
            draft = _single_primary_draft(
                profile,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                operation_hash=operation_hash,
                row=outbound_rows[0][1],
                operation_key="ledger_live_out",
                economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                projection_hint=ProjectionHint.WITHDRAWAL,
                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                leg_id="primary_out",
                quantity_sign=Decimal("-1"),
            )
            if draft is None:
                issues.append(
                    _unsupported_group_issue(
                        profile, raw_file, raw_row_ref, operation_hash
                    )
                )
                continue
            drafts.append(draft)
            continue
        if operation_types == {"FEES"} and len(fee_rows) == 1:
            draft = _single_primary_draft(
                profile,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                operation_hash=operation_hash,
                row=fee_rows[0][1],
                operation_key="ledger_live_fee",
                economic_kind=EconomicKind.CASH_EXPENSE,
                projection_hint=ProjectionHint.EXPENSE_NON_TAXABLE,
                accounting_intent_hint=AccountingIntentHint.EXPENSE_RECOGNITION,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_EXPENSE,
                leg_id="primary_fee",
                quantity_sign=Decimal("-1"),
            )
            if draft is None:
                issues.append(
                    _unsupported_group_issue(
                        profile, raw_file, raw_row_ref, operation_hash
                    )
                )
                continue
            drafts.append(draft)
            continue
        if operation_types == {"DELEGATE"} and len(delegate_rows) == 1:
            draft = _single_primary_draft(
                profile,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                operation_hash=operation_hash,
                row=delegate_rows[0][1],
                operation_key="ledger_live_delegate",
                economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
                projection_hint=ProjectionHint.STAKING,
                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                leg_id="primary_delegate",
                quantity_sign=Decimal("-1"),
            )
            if draft is None:
                issues.append(
                    _unsupported_group_issue(
                        profile, raw_file, raw_row_ref, operation_hash
                    )
                )
                continue
            drafts.append(draft)
            reviews.append(
                review_record(
                    ReviewSpec(
                        review_id=f"ledger_live:{raw_file}:{operation_hash}:delegate_incomplete",
                        source=str(profile.source),
                        adapter_id="ledger_live",
                        scope="activity",
                        kind="staking_delegate_incomplete",
                        message=(
                            "Ledger Live delegate export proves the debited asset movement but not the external "
                            "staking-side state or validator position."
                        ),
                        raw_file=raw_file,
                        raw_row_ref=raw_row_ref,
                        field_name="operation_type",
                        original_value="DELEGATE",
                    )
                )
            )
            continue
        if (
            operation_types in ({"IN", "OUT"}, {"IN", "OUT", "FEES"})
            and len(inbound_rows) == 1
            and len(outbound_rows) == 1
        ):
            _, inbound = inbound_rows[0]
            _, outbound = outbound_rows[0]
            fee_row = fee_rows[0][1] if fee_rows else None
            timestamp = parse_timestamp((inbound.get("Operation Date") or "").strip())
            account_label = (
                inbound.get("Account Name") or outbound.get("Account Name") or ""
            ).strip()
            fee_amount = Decimal((fee_row or {}).get("Operation Amount") or "0")
            fee_asset = (fee_row or {}).get("Currency Ticker") or ""
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"ledger_live:{raw_file}:{operation_hash}",
                    source=str(profile.source),
                    adapter_id="ledger_live",
                    location_id=location_id_from_parts(
                        str(profile.source), account_label or operation_hash
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
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    tx_hash=operation_hash,
                    provider_operation_key="ledger_live_swap",
                    operation_group_id=operation_hash,
                    legs=(
                        economic_leg(
                            leg_id="primary_in",
                            kind=LegKind.PRIMARY,
                            quantity=Decimal(
                                (inbound.get("Operation Amount") or "0").strip()
                            ),
                            instrument=symbol_claim(
                                (inbound.get("Currency Ticker") or "").strip().upper(),
                                venue="ledger_live",
                            ),
                        ),
                        economic_leg(
                            leg_id="primary_out",
                            kind=LegKind.PRIMARY,
                            quantity=-Decimal(
                                (outbound.get("Operation Amount") or "0").strip()
                            ),
                            instrument=symbol_claim(
                                (outbound.get("Currency Ticker") or "").strip().upper(),
                                venue="ledger_live",
                            ),
                        ),
                        *_charge_legs(
                            fee_amount, fee_asset, attributed_to_leg_id="primary_out"
                        ),
                    ),
                )
            )
            continue
        issues.append(
            _unsupported_group_issue(profile, raw_file, raw_row_ref, operation_hash)
        )
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
