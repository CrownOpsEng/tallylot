"""NEAR transaction translation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.near.families import (
    classified_csv_paths,
    near_account_for_path,
)
from tallylot.adapters.support import (
    IssueSpec,
    issue_record,
    near_native_asset_claim,
    location_id_from_identifier,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    ActivitySemantics,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft


@dataclass(frozen=True)
class NearTransferDraftContext:
    path_name: str
    raw_row_ref: str
    tx_hash: str
    timestamp: datetime
    account_id: str
    from_account: str
    to_account: str
    amount: Decimal
    fee: Decimal


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "base_transactions":
            issues.append(_unsupported_family_issue(profile, path.name, family_id))
            continue
        account_id = near_account_for_path(path)
        for index, row in enumerate(read_csv_rows(path), start=2):
            raw_row_ref = f"row:{index}"
            timestamp = _parse_timestamp(_row_value(row, "Time", "Block Time"))
            tx_hash = _row_value(row, "Txn Hash")
            method = _row_value(row, "Method").lower()
            amount = parse_decimal(_row_value(row, "Deposit Value"))
            fee = parse_decimal(_row_value(row, "Txn Fee", default="0")) or Decimal("0")
            from_account = _row_value(row, "From")
            to_account = _row_value(row, "To")
            if timestamp is None:
                issues.append(
                    _row_issue(
                        profile,
                        path.name,
                        raw_row_ref,
                        issue_id_suffix="invalid_timestamp",
                        message="NEAR transaction row is missing a supported block timestamp.",
                    )
                )
                continue
            if not account_id:
                issues.append(
                    _row_issue(
                        profile,
                        path.name,
                        raw_row_ref,
                        issue_id_suffix="missing_identifier",
                        message="NEAR base transaction rows could not be tied to a NEAR account identifier.",
                    )
                )
                continue
            if amount is None or amount <= Decimal("0"):
                issues.append(
                    _row_issue(
                        profile,
                        path.name,
                        raw_row_ref,
                        issue_id_suffix="invalid_amount",
                        message="NEAR transaction row is missing a positive deposit value.",
                    )
                )
                continue
            if method == "transfer":
                transfer_draft = _transfer_draft(
                    profile,
                    NearTransferDraftContext(
                        path_name=path.name,
                        raw_row_ref=raw_row_ref,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        account_id=account_id,
                        from_account=from_account,
                        to_account=to_account,
                        amount=amount,
                        fee=fee,
                    ),
                )
                if transfer_draft is None:
                    issues.append(
                        _row_issue(
                            profile,
                            path.name,
                            raw_row_ref,
                            issue_id_suffix="unsupported_transfer_shape",
                            message="NEAR transfer row does not match the owned account direction.",
                        )
                    )
                    continue
                drafts.append(transfer_draft)
                continue
            if method == "deposit_and_stake":
                description = f"Stake NEAR - {tx_hash}"
                drafts.extend(
                    (
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:wallet",
                            source=str(profile.source),
                            adapter_id="near",
                            location_id=_near_location_id(account_id),
                            timestamp=timestamp,
                            classification=classification(
                                economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
                                projection_hint=ProjectionHint.WITHDRAWAL,
                                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                            ),
                            leg_policy=_single_primary_with_optional_charge_policy(fee),
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(
                                economic_leg(
                                    leg_id="primary_out",
                                    kind=LegKind.PRIMARY,
                                    quantity=-amount,
                                    instrument=near_native_asset_claim(),
                                ),
                                *_charge_legs(fee, attributed_to_leg_id="primary_out"),
                            ),
                        ),
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:staking",
                            source=str(profile.source),
                            adapter_id="near",
                            location_id=_near_location_id(
                                account_id, suffix=("staking",)
                            ),
                            timestamp=timestamp,
                            classification=classification(
                                economic_kind=EconomicKind.STAKING_TRANSFER_IN,
                                projection_hint=ProjectionHint.DEPOSIT,
                                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                            ),
                            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(
                                economic_leg(
                                    leg_id="primary_in",
                                    kind=LegKind.PRIMARY,
                                    quantity=amount,
                                    instrument=near_native_asset_claim(),
                                ),
                            ),
                        ),
                    )
                )
                continue
            issues.append(
                _row_issue(
                    profile,
                    path.name,
                    raw_row_ref,
                    issue_id_suffix=f"unsupported:{method or 'unknown'}",
                    message=f"Unsupported NEAR transaction method: {method or '<missing>'}",
                )
            )
    return tuple(drafts), tuple(issues)


def _transfer_draft(
    profile: SourceProfile,
    context: NearTransferDraftContext,
) -> EconomicActivityDraft | None:
    if context.to_account == context.account_id:
        semantics = ActivitySemantics(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        )
        quantity = context.amount
        primary_leg_id = "primary_in"
        description = f"Transfer into {profile.source} - {context.tx_hash}"
    elif context.from_account == context.account_id:
        semantics = ActivitySemantics(
            economic_kind=EconomicKind.ASSET_WITHDRAWAL,
            projection_hint=ProjectionHint.WITHDRAWAL,
            accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
        )
        quantity = -context.amount
        primary_leg_id = "primary_out"
        description = f"Transfer out of {profile.source} - {context.tx_hash}"
    elif not context.from_account and not context.to_account:
        semantics = ActivitySemantics(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        )
        quantity = context.amount
        primary_leg_id = "primary_in"
        description = f"Transfer into {profile.source} - {context.tx_hash}"
    else:
        return None
    return EconomicActivityDraft(
        activity_id=f"near:{context.path_name}:{context.raw_row_ref}",
        source=str(profile.source),
        adapter_id="near",
        location_id=_near_location_id(context.account_id),
        timestamp=context.timestamp,
        classification=semantics.to_classification(),
        leg_policy=_single_primary_with_optional_charge_policy(context.fee),
        description=description,
        raw_file=context.path_name,
        raw_row_ref=context.raw_row_ref,
        tx_hash=context.tx_hash,
        provider_operation_key="transfer",
        legs=(
            economic_leg(
                leg_id=primary_leg_id,
                kind=LegKind.PRIMARY,
                quantity=quantity,
                instrument=near_native_asset_claim(),
            ),
            *_charge_legs(context.fee, attributed_to_leg_id=primary_leg_id),
        ),
    )


def _single_primary_with_optional_charge_policy(fee: Decimal) -> FactLegPolicy:
    if fee <= Decimal("0"):
        return SINGLE_PRIMARY_ACTIVITY_POLICY
    return FactLegPolicy(
        limits=(
            LegShapeLimit(
                kind=LegKind.PRIMARY,
                max_count=1,
                max_positive_count=1,
                max_negative_count=1,
            ),
            LegShapeLimit(
                kind=LegKind.CHARGE,
                max_count=1,
                max_positive_count=0,
                max_negative_count=1,
            ),
        )
    )


def _charge_legs(
    fee: Decimal, *, attributed_to_leg_id: str
) -> tuple[EconomicLegDraft, ...]:
    if fee <= Decimal("0"):
        return ()
    return (
        economic_leg(
            leg_id="charge",
            kind=LegKind.CHARGE,
            quantity=-fee,
            instrument=near_native_asset_claim(),
            subtype="network_fee",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )


def _row_value(
    row: dict[str, str], key: str, fallback: str = "", *, default: str = ""
) -> str:
    value = row.get(key, "")
    if value:
        return value.strip()
    if fallback:
        fallback_value = row.get(fallback, "")
        if fallback_value:
            return fallback_value.strip()
    return default


def _row_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    *,
    issue_id_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"near:{raw_file}:{raw_row_ref}:{issue_id_suffix}",
            source=str(profile.source),
            adapter_id="near",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )


def _unsupported_family_issue(
    profile: SourceProfile, raw_file: str, family_id: str
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"near:{raw_file}:unsupported_family:{family_id}",
            source=str(profile.source),
            adapter_id="near",
            kind="unsupported_file_family",
            message=(
                "NEAR auxiliary export families are recognized but not normalized automatically in this phase: "
                f"{family_id}"
            ),
            raw_file=raw_file,
        )
    )


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _near_location_id(account_id: str, *, suffix: tuple[str, ...] = ()) -> LocationId:
    return location_id_from_identifier("near_account", account_id, suffix=suffix)
