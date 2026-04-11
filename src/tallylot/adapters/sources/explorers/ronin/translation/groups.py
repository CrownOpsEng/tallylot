"""Ronin explorer translation grouping rules."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.ronin.families import classified_csv_paths
from tallylot.adapters.support import read_csv_rows
from tallylot.adapters.support.drafts import EconomicActivityDraft
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import SourceProfile

from .issues import row_issue
from .raw import translate_raw_group
from .rows import (
    RoninRawRow,
    RoninSummaryRow,
    parse_raw_row,
    parse_summary_row,
    raw_signature,
    summary_time_calibrations,
)
from .summary import translate_summary_group


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    owned_addresses: set[str],
) -> tuple[
    tuple[EconomicActivityDraft, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    raw_groups, raw_issues = _collect_raw_groups(profile, raw_dir)
    summary_rows, summary_issues = _collect_summary_rows(profile, raw_dir)
    drafts: list[EconomicActivityDraft] = []
    issues = [*raw_issues, *summary_issues]
    reviews: list[NormalizationReviewRecord] = []
    raw_groups_by_hash = {group[0].tx_hash: group for group in raw_groups}
    summary_by_hash: dict[str, list[RoninSummaryRow]] = {}
    for row in summary_rows:
        summary_by_hash.setdefault(row.tx_hash, []).append(row)
    summary_calibrations = summary_time_calibrations(raw_groups_by_hash, summary_rows)
    for tx_hash in sorted(set(raw_groups_by_hash) | set(summary_by_hash)):
        raw_group = raw_groups_by_hash.get(tx_hash)
        summary_group = tuple(summary_by_hash.get(tx_hash, ()))
        if raw_group is not None:
            raw_drafts, raw_group_issues, raw_group_reviews = translate_raw_group(
                profile,
                raw_group,
                owned_addresses=owned_addresses,
                summary_rows=summary_group,
            )
            drafts.extend(raw_drafts)
            issues.extend(raw_group_issues)
            reviews.extend(raw_group_reviews)
            continue
        summary_drafts, summary_group_issues = translate_summary_group(
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
            parsed = parse_raw_row(path.name, index, row)
            if parsed is None:
                issues.append(
                    row_issue(
                        profile,
                        path.name,
                        f"row:{index}",
                        "invalid_row",
                        "Ronin explorer row is missing a supported tx hash, timestamp, or asset amount.",
                    )
                )
                continue
            rows_by_hash.setdefault(parsed.tx_hash, {})[raw_signature(parsed)] = parsed
    groups = tuple(
        sorted(
            (
                tuple(
                    sorted(
                        group.values(),
                        key=lambda row: (row.timestamp, row.path_name, row.row_index),
                    )
                )
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
            parsed = parse_summary_row(path.name, index, row)
            if parsed is None:
                issues.append(
                    row_issue(
                        profile,
                        path.name,
                        f"row:{index}",
                        "invalid_row",
                        "Ronin summary row is missing a supported tx hash, timestamp, or asset amount.",
                    )
                )
                continue
            signature = (
                parsed.tx_hash,
                parsed.action_type,
                parsed.asset_symbol,
                str(parsed.quantity),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            parsed_rows.append(parsed)
    return tuple(
        sorted(
            parsed_rows,
            key=lambda row: (row.local_timestamp, row.tx_hash, row.row_index),
        )
    ), tuple(issues)
