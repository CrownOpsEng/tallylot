"""Helpers for explicit normalization windows."""

from __future__ import annotations

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.value_objects import parse_timestamp
from tallylot.ports.source_translation import EconomicActivityDraft


def filter_drafts_by_window(
    drafts: tuple[EconomicActivityDraft, ...],
    *,
    window_start: str | None,
    window_end: str | None,
) -> tuple[tuple[EconomicActivityDraft, ...], int]:
    if not window_start and not window_end:
        return drafts, 0
    start_dt = parse_timestamp(window_start) if window_start else None
    end_dt = parse_timestamp(window_end) if window_end else None
    filtered: list[EconomicActivityDraft] = []
    excluded_count = 0
    for draft in drafts:
        if start_dt is not None and draft.timestamp < start_dt:
            excluded_count += 1
            continue
        if end_dt is not None and draft.timestamp > end_dt:
            excluded_count += 1
            continue
        filtered.append(draft)
    return tuple(filtered), excluded_count


def _filter_facts_by_window(
    facts: tuple[TransactionFact, ...],
    *,
    window_start: str | None,
    window_end: str | None,
) -> tuple[tuple[TransactionFact, ...], int]:
    if not window_start and not window_end:
        return facts, 0
    start_dt = parse_timestamp(window_start) if window_start else None
    end_dt = parse_timestamp(window_end) if window_end else None
    filtered: list[TransactionFact] = []
    excluded_count = 0
    for fact in facts:
        if start_dt is not None and fact.timestamp < start_dt:
            excluded_count += 1
            continue
        if end_dt is not None and fact.timestamp > end_dt:
            excluded_count += 1
            continue
        filtered.append(fact)
    return tuple(filtered), excluded_count


def filter_issues_by_window(
    issues: tuple[IssueRecord, ...],
    *,
    window_start: str | None,
    window_end: str | None,
) -> tuple[tuple[IssueRecord, ...], int]:
    if not window_start and not window_end:
        return issues, 0
    start_dt = parse_timestamp(window_start) if window_start else None
    end_dt = parse_timestamp(window_end) if window_end else None
    filtered: list[IssueRecord] = []
    excluded_count = 0
    for issue in issues:
        if not issue.context_timestamp:
            if _is_activity_scoped_issue(issue):
                excluded_count += 1
                continue
            filtered.append(issue)
            continue
        issue_dt = parse_timestamp(issue.context_timestamp)
        if start_dt is not None and issue_dt < start_dt:
            excluded_count += 1
            continue
        if end_dt is not None and issue_dt > end_dt:
            excluded_count += 1
            continue
        filtered.append(issue)
    return tuple(filtered), excluded_count


def filter_reviews_by_window(
    reviews: tuple[NormalizationReviewRecord, ...],
    *,
    window_start: str | None,
    window_end: str | None,
) -> tuple[tuple[NormalizationReviewRecord, ...], int]:
    if not window_start and not window_end:
        return reviews, 0
    start_dt = parse_timestamp(window_start) if window_start else None
    end_dt = parse_timestamp(window_end) if window_end else None
    filtered: list[NormalizationReviewRecord] = []
    excluded_count = 0
    for review in reviews:
        if review.scope == "dataset":
            filtered.append(review)
            continue
        if not review.context_timestamp:
            excluded_count += 1
            continue
        review_dt = parse_timestamp(review.context_timestamp)
        if start_dt is not None and review_dt < start_dt:
            excluded_count += 1
            continue
        if end_dt is not None and review_dt > end_dt:
            excluded_count += 1
            continue
        filtered.append(review)
    return tuple(filtered), excluded_count


def _is_activity_scoped_issue(issue: IssueRecord) -> bool:
    return bool(issue.raw_file or issue.raw_row_ref)
