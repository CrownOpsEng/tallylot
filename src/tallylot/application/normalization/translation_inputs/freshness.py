"""Freshness ordering helpers for translation input planning."""

from __future__ import annotations

from datetime import UTC

from tallylot.ports.translation_inputs import (
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
)

_FRESHNESS_KIND_PRECEDENCE = {
    TranslationFreshnessKind.EXPORT_TIMESTAMP: 3,
    TranslationFreshnessKind.CAPTURE_COMPLETED_AT: 2,
    TranslationFreshnessKind.ADAPTER_RANK: 1,
    TranslationFreshnessKind.UNKNOWN: 0,
}


def all_identical_candidates(
    candidates: tuple[TranslationInputCandidate, ...],
) -> bool:
    first = candidates[0]
    return all(
        candidate.coverage == first.coverage
        and candidate.content_fingerprint == first.content_fingerprint
        for candidate in candidates[1:]
    )


def freshest_candidates(
    candidates: tuple[TranslationInputCandidate, ...],
) -> tuple[TranslationInputCandidate, ...]:
    if not candidates:
        return ()
    highest_key = max(
        freshness_sort_key(candidate.freshness) for candidate in candidates
    )
    return tuple(
        candidate
        for candidate in candidates
        if freshness_sort_key(candidate.freshness) == highest_key
    )


def deterministic_duplicate_winner(
    candidates: tuple[TranslationInputCandidate, ...],
) -> TranslationInputCandidate:
    return sorted(
        candidates,
        key=lambda candidate: (
            -freshness_precedence(candidate.freshness.kind),
            -freshness_sort_numeric_value(candidate.freshness),
            candidate.candidate_id,
        ),
    )[0]


def freshness_precedence(kind: TranslationFreshnessKind) -> int:
    return _FRESHNESS_KIND_PRECEDENCE[kind]


def freshness_sort_key(
    freshness: TranslationFreshness,
) -> tuple[int, float]:
    return (
        freshness_precedence(freshness.kind),
        freshness_sort_numeric_value(freshness),
    )


def freshness_sort_numeric_value(freshness: TranslationFreshness) -> float:
    if freshness.kind in {
        TranslationFreshnessKind.EXPORT_TIMESTAMP,
        TranslationFreshnessKind.CAPTURE_COMPLETED_AT,
    }:
        if freshness.timestamp is None:
            return float("-inf")
        return freshness.timestamp.astimezone(UTC).timestamp()
    if freshness.kind is TranslationFreshnessKind.ADAPTER_RANK:
        return float("-inf") if freshness.rank is None else float(freshness.rank)
    return float("-inf")
