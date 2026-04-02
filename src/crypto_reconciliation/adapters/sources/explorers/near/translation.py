"""NEAR transaction translation rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import IssueSpec, issue_record, matching_file_paths, read_csv_rows
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    fee_leg,
)
from crypto_reconciliation.domain.models import IssueRecord, SourceProfile
from crypto_reconciliation.domain.value_objects import parse_decimal


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
                net_amount = amount - fee
                if net_amount <= Decimal("0"):
                    issues.append(
                        _row_issue(
                            profile,
                            path.name,
                            raw_row_ref,
                            issue_id_suffix="non_positive_net_transfer",
                            message="NEAR transfer row has a non-positive net amount after fees.",
                        )
                    )
                    continue
                drafts.append(
                    EconomicActivityDraft(
                        activity_id=f"near:{path.name}:{raw_row_ref}",
                        source=str(profile.source),
                        adapter_id="near",
                        account=str(profile.source),
                        wallet=str(profile.source),
                        timestamp=timestamp,
                        classification=classification(
                            economic_kind="chain_transfer_in",
                            projection_type="Deposit",
                            journal_intent="funding_inflow",
                            tax_treatment_code="non_taxable_transfer_in",
                        ),
                        description=f"Transfer into {profile.source} - {tx_hash}",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        tx_hash=tx_hash,
                        provider_operation_key=method,
                        legs=(economic_leg(direction="in", asset="NEAR", amount=net_amount),),
                    )
                )
                continue
            if method == "deposit_and_stake":
                description = f"Stake NEAR - {tx_hash}"
                fee_legs = (fee_leg(asset="NEAR", amount=fee),) if fee > Decimal("0") else ()
                drafts.extend(
                    (
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:wallet",
                            source=str(profile.source),
                            adapter_id="near",
                            account=str(profile.source),
                            wallet=str(profile.source),
                            timestamp=timestamp,
                            classification=classification(
                                economic_kind="staking_transfer_out",
                                projection_type="Withdrawal",
                                journal_intent="funding_outflow",
                                tax_treatment_code="non_taxable_transfer_out",
                            ),
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(economic_leg(direction="out", asset="NEAR", amount=amount),),
                            fee_legs=fee_legs,
                        ),
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:staking",
                            source=f"{profile.source} - Staking",
                            adapter_id="near",
                            account=f"{profile.source} - Staking",
                            wallet=f"{profile.source} - Staking",
                            timestamp=timestamp,
                            classification=classification(
                                economic_kind="staking_transfer_in",
                                projection_type="Deposit",
                                journal_intent="funding_inflow",
                                tax_treatment_code="non_taxable_transfer_in",
                            ),
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(economic_leg(direction="in", asset="NEAR", amount=amount),),
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
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)
    except ValueError:
        return None
