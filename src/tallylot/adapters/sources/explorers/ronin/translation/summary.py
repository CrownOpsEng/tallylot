"""Ronin explorer summary-row translation rules."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from tallylot.adapters.support.drafts import EconomicActivityDraft
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile

from .drafts import summary_transfer_draft
from .issues import row_issue
from .rows import (
    RoninSummaryRow,
    SummaryDraftContext,
    infer_summary_utc_timestamp,
    is_supported_restake_pair,
    ronin_location_id,
    staking_out_semantics,
    staking_reward_semantics,
    transfer_in_semantics,
    transfer_out_semantics,
)


def translate_summary_group(
    profile: SourceProfile,
    summary_rows: tuple[RoninSummaryRow, ...],
    *,
    owned_addresses: set[str],
    calibrations: tuple[tuple[datetime, timedelta], ...] = (),
    timestamp_override: datetime | None = None,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if not summary_rows:
        return (), ()
    local_timestamps = {row.local_timestamp for row in summary_rows}
    if len(local_timestamps) != 1:
        return (), (
            row_issue(
                profile,
                summary_rows[0].path_name,
                summary_rows[0].raw_row_ref,
                "ambiguous_summary_timestamp",
                f"Ronin summary rows disagree on timestamp for tx {summary_rows[0].tx_hash}.",
            ),
        )
    timestamp = timestamp_override or infer_summary_utc_timestamp(
        summary_rows[0].local_timestamp, calibrations
    )
    if timestamp is None:
        return (), (
            row_issue(
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
            row_issue(
                profile,
                summary_rows[0].path_name,
                summary_rows[0].raw_row_ref,
                "ambiguous_summary_group",
                f"Ronin summary rows disagree on action type for tx {summary_rows[0].tx_hash}.",
            ),
        )
    action_type = next(iter(action_types))
    return _translate_supported_summary_group(
        profile,
        summary_rows,
        action_type=action_type,
        timestamp=timestamp,
        owned_addresses=owned_addresses,
    )


def _translate_supported_summary_group(
    profile: SourceProfile,
    summary_rows: tuple[RoninSummaryRow, ...],
    *,
    action_type: str,
    timestamp: datetime,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if action_type == "transfer" and len(summary_rows) == 1:
        return _translate_summary_transfer_row(
            profile,
            summary_rows[0],
            timestamp=timestamp,
            owned_addresses=owned_addresses,
        )
    if action_type == "stakeaxs" and len(summary_rows) == 1:
        return _translate_summary_stake_row(
            profile,
            summary_rows[0],
            timestamp=timestamp,
            owned_addresses=owned_addresses,
        )
    if action_type == "restakeaxs" and len(summary_rows) == 2:
        return _translate_summary_restake_rows(
            profile,
            summary_rows,
            timestamp=timestamp,
            owned_addresses=owned_addresses,
        )
    return (), (
        row_issue(
            profile,
            summary_rows[0].path_name,
            summary_rows[0].raw_row_ref,
            "unsupported_summary_group",
            f"Ronin summary rows do not match a supported {action_type} pattern.",
        ),
    )


def _translate_summary_transfer_row(
    profile: SourceProfile,
    row: RoninSummaryRow,
    *,
    timestamp: datetime,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.quantity > Decimal("0") and row.to_address in owned_addresses:
        return (
            summary_transfer_draft(
                profile,
                row,
                SummaryDraftContext(
                    timestamp=timestamp,
                    location_id=ronin_location_id(row.to_address),
                    quantity=row.quantity,
                    semantics=transfer_in_semantics(),
                ),
            ),
        ), ()
    if row.quantity < Decimal("0") and row.from_address in owned_addresses:
        return (
            summary_transfer_draft(
                profile,
                row,
                SummaryDraftContext(
                    timestamp=timestamp,
                    location_id=ronin_location_id(row.from_address),
                    quantity=row.quantity,
                    semantics=transfer_out_semantics(),
                ),
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_summary_group",
            "Ronin transfer summary row does not match a supported wallet direction.",
        ),
    )


def _translate_summary_stake_row(
    profile: SourceProfile,
    row: RoninSummaryRow,
    *,
    timestamp: datetime,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    if row.quantity < Decimal("0") and row.from_address in owned_addresses:
        return (
            summary_transfer_draft(
                profile,
                row,
                SummaryDraftContext(
                    timestamp=timestamp,
                    location_id=ronin_location_id(row.from_address),
                    quantity=row.quantity,
                    semantics=staking_out_semantics(),
                ),
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            row.path_name,
            row.raw_row_ref,
            "unsupported_summary_group",
            "Ronin stake summary row does not match a supported wallet outflow.",
        ),
    )


def _translate_summary_restake_rows(
    profile: SourceProfile,
    summary_rows: tuple[RoninSummaryRow, ...],
    *,
    timestamp: datetime,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    positive_row = next(
        (row for row in summary_rows if row.quantity > Decimal("0")), None
    )
    negative_row = next(
        (row for row in summary_rows if row.quantity < Decimal("0")), None
    )
    if is_supported_restake_pair(positive_row, negative_row, owned_addresses):
        assert positive_row is not None
        assert negative_row is not None
        return (
            summary_transfer_draft(
                profile,
                positive_row,
                SummaryDraftContext(
                    timestamp=timestamp,
                    location_id=ronin_location_id(positive_row.to_address),
                    quantity=positive_row.quantity,
                    semantics=staking_reward_semantics(),
                ),
            ),
            summary_transfer_draft(
                profile,
                negative_row,
                SummaryDraftContext(
                    timestamp=timestamp,
                    location_id=ronin_location_id(negative_row.from_address),
                    quantity=negative_row.quantity,
                    semantics=staking_out_semantics(),
                ),
            ),
        ), ()
    return (), (
        row_issue(
            profile,
            summary_rows[0].path_name,
            summary_rows[0].raw_row_ref,
            "unsupported_summary_group",
            "Ronin restake summary rows do not match a supported pair.",
        ),
    )
