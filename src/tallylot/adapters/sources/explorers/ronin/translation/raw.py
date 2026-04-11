"""Ronin explorer raw-row translation rules."""

from __future__ import annotations

from decimal import Decimal

from tallylot.adapters.support.drafts import EconomicActivityDraft
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import SourceProfile

from .drafts import (
    raw_restake_pair_drafts,
    simple_transfer_draft,
    staking_reward_draft,
    staking_transfer_in_draft,
    staking_transfer_out_draft,
)
from .issues import row_issue, supported_fee_reviews
from .rows import RoninRawRow, RoninSummaryRow, resolve_fee, ronin_location_id
from .summary import translate_summary_group


def translate_raw_group(
    profile: SourceProfile,
    raw_rows: tuple[RoninRawRow, ...],
    *,
    owned_addresses: set[str],
    summary_rows: tuple[RoninSummaryRow, ...],
) -> tuple[
    tuple[EconomicActivityDraft, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    methods = {row.method for row in raw_rows}
    if len(methods) != 1:
        return (
            (),
            (
                row_issue(
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
    fee_resolution = resolve_fee(profile, raw_rows)
    if method == "restakerewards":
        if summary_rows:
            summary_drafts, summary_issues = translate_summary_group(
                profile,
                summary_rows,
                owned_addresses=owned_addresses,
                timestamp_override=raw_rows[0].timestamp,
            )
            if summary_drafts:
                return (
                    summary_drafts,
                    summary_issues,
                    supported_fee_reviews(
                        fee_resolution, draft_count=len(summary_drafts)
                    ),
                )
        raw_pair_drafts = raw_restake_pair_drafts(
            profile,
            raw_rows,
            owned_addresses=owned_addresses,
            authoritative_fee=fee_resolution.authoritative_fee,
        )
        if raw_pair_drafts is not None:
            return (
                raw_pair_drafts,
                (),
                supported_fee_reviews(fee_resolution, draft_count=len(raw_pair_drafts)),
            )
        return (
            (),
            (
                row_issue(
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
                row_issue(
                    profile,
                    raw_rows[0].path_name,
                    raw_rows[0].raw_row_ref,
                    "unsupported_raw_group",
                    f"Ronin emitted {len(raw_rows)} raw rows for {method}, which is not a supported grouped shape.",
                ),
            ),
            (),
        )
    drafts, issues = _translate_raw_row(
        profile,
        raw_rows[0],
        owned_addresses=owned_addresses,
        authoritative_fee=fee_resolution.authoritative_fee,
    )
    return (
        drafts,
        issues,
        supported_fee_reviews(fee_resolution, draft_count=len(drafts)),
    )


def _translate_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.status != "success":
        return (), (
            row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_status",
                "Ronin row is not successful.",
            ),
        )
    return _translate_supported_raw_row(
        profile,
        row,
        owned_addresses=owned_addresses,
        authoritative_fee=authoritative_fee,
    )


def _translate_supported_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.method == "transfer":
        return _translate_transfer_raw_row(
            profile,
            row,
            owned_addresses=owned_addresses,
            authoritative_fee=authoritative_fee,
        )
    if row.method == "stake":
        return _translate_stake_raw_row(
            profile,
            row,
            owned_addresses=owned_addresses,
            authoritative_fee=authoritative_fee,
        )
    if row.method == "unstake":
        return _translate_unstake_raw_row(
            profile,
            row,
            owned_addresses=owned_addresses,
            authoritative_fee=authoritative_fee,
        )
    if row.method == "claimpendingrewards":
        return _translate_reward_raw_row(
            profile,
            row,
            owned_addresses=owned_addresses,
            authoritative_fee=authoritative_fee,
        )
    if row.method == "approve":
        return (), (
            row_issue(
                profile,
                row.path_name,
                row.raw_row_ref,
                "unsupported_method:approve",
                "Ronin approve rows are recognized but not normalized automatically.",
            ),
        )
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            f"unsupported_method:{row.method}",
            f"Unsupported Ronin explorer method: {row.method}",
        ),
    )


def _translate_transfer_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    draft = simple_transfer_draft(
        profile,
        row,
        owned_addresses=owned_addresses,
        authoritative_fee=authoritative_fee,
    )
    if draft is not None:
        return (draft,), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_shape",
            "Ronin transfer row does not match a supported wallet direction.",
        ),
    )


def _translate_stake_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.from_address in owned_addresses and row.outbound_quantity > Decimal("0"):
        return (
            staking_transfer_out_draft(
                profile,
                row,
                location_id=ronin_location_id(row.from_address),
                fee=authoritative_fee,
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_shape",
            "Ronin stake row does not match a supported wallet outflow.",
        ),
    )


def _translate_unstake_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.to_address in owned_addresses and row.inbound_quantity > Decimal("0"):
        return (
            staking_transfer_in_draft(
                profile,
                row,
                location_id=ronin_location_id(row.to_address),
                fee=authoritative_fee,
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_shape",
            "Ronin unstake row does not match a supported wallet inflow.",
        ),
    )


def _translate_reward_raw_row(
    profile: SourceProfile,
    row: RoninRawRow,
    *,
    owned_addresses: set[str],
    authoritative_fee: Decimal,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.to_address in owned_addresses and row.inbound_quantity > Decimal("0"):
        return (
            staking_reward_draft(
                profile,
                row,
                location_id=ronin_location_id(row.to_address),
                fee=authoritative_fee,
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_shape",
            "Ronin reward row does not match a supported wallet inflow.",
        ),
    )
