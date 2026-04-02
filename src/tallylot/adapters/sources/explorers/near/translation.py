"""NEAR transaction translation rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import (
    IssueSpec,
    issue_record,
    location_id_from_parts,
    matching_file_paths,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    EconomicActivityDraft,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    classification,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import EconomicLegDraft


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for path in matching_file_paths(raw_dir, pattern="*_transactions.csv"):
        for index, row in enumerate(read_csv_rows(path), start=2):
            raw_row_ref = f"row:{index}"
            timestamp = _parse_timestamp(_row_value(row, "Time", "Block Time"))
            tx_hash = _row_value(row, "Txn Hash")
            method = _row_value(row, "Method").lower()
            amount = parse_decimal(_row_value(row, "Deposit Value"))
            fee = parse_decimal(_row_value(row, "Txn Fee", default="0")) or Decimal("0")
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
                drafts.append(
                    EconomicActivityDraft(
                        activity_id=f"near:{path.name}:{raw_row_ref}",
                        source=str(profile.source),
                        adapter_id="near",
                        location_id=location_id_from_parts(str(profile.source)),
                        timestamp=timestamp,
                        classification=classification(
                            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                            projection_hint=ProjectionHint.DEPOSIT,
                            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                        ),
                        leg_policy=_transfer_in_policy(fee),
                        description=f"Transfer into {profile.source} - {tx_hash}",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        tx_hash=tx_hash,
                        provider_operation_key=method,
                        legs=(
                            economic_leg(
                                leg_id="primary_in",
                                kind=LegKind.PRIMARY,
                                quantity=amount,
                                instrument=symbol_claim("NEAR", venue="near"),
                            ),
                            *_charge_legs(fee, attributed_to_leg_id="primary_in"),
                        ),
                    )
                )
                continue
            if method == "deposit_and_stake":
                description = f"Stake NEAR - {tx_hash}"
                drafts.extend(
                    (
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:wallet",
                            source=str(profile.source),
                            adapter_id="near",
                            location_id=location_id_from_parts(str(profile.source)),
                            timestamp=timestamp,
                            classification=classification(
                                economic_kind=EconomicKind.STAKING_TRANSFER_OUT,
                                projection_hint=ProjectionHint.WITHDRAWAL,
                                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                            ),
                            leg_policy=_staking_out_policy(fee),
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
                                    instrument=symbol_claim("NEAR", venue="near"),
                                ),
                                *_charge_legs(fee, attributed_to_leg_id="primary_out"),
                            ),
                        ),
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:staking",
                            source=f"{profile.source} - Staking",
                            adapter_id="near",
                            location_id=location_id_from_parts(f"{profile.source} - Staking"),
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
                                    instrument=symbol_claim("NEAR", venue="near"),
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


def _staking_out_policy(fee: Decimal) -> FactLegPolicy:
    return _single_primary_with_optional_charge_policy(fee)


def _transfer_in_policy(fee: Decimal) -> FactLegPolicy:
    return _single_primary_with_optional_charge_policy(fee)


def _single_primary_with_optional_charge_policy(fee: Decimal) -> FactLegPolicy:
    if fee <= Decimal("0"):
        return SINGLE_PRIMARY_ACTIVITY_POLICY
    return FactLegPolicy(
        limits=(
            LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, max_positive_count=1, max_negative_count=1),
            LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_positive_count=0, max_negative_count=1),
        )
    )


def _charge_legs(fee: Decimal, *, attributed_to_leg_id: str) -> tuple[EconomicLegDraft, ...]:
    if fee <= Decimal("0"):
        return ()
    return (
        economic_leg(
            leg_id="charge",
            kind=LegKind.CHARGE,
            quantity=-fee,
            instrument=symbol_claim("NEAR", venue="near"),
            subtype="network_fee",
            attributed_to_leg_id=attributed_to_leg_id,
        ),
    )


def _row_value(row: dict[str, str], key: str, fallback: str = "", *, default: str = "") -> str:
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


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None
