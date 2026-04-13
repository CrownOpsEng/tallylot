"""Coverage overlap helpers for translation input planning."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import combinations
from typing import Literal

from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationInputCandidate,
)

MIN_COVERAGE_BOUND = datetime.min.replace(tzinfo=UTC)
MAX_COVERAGE_BOUND = datetime.max.replace(tzinfo=UTC)

CoverageRelation = Literal[
    "disjoint", "equal", "contains", "within", "partial", "unknown"
]


def coverage_bounds(
    coverage: TranslationCoverageWindow,
) -> tuple[datetime, datetime] | None:
    if coverage.mode is TranslationCoverageMode.UNKNOWN:
        return None
    return (
        coverage.start_at or MIN_COVERAGE_BOUND,
        coverage.end_at or MAX_COVERAGE_BOUND,
    )


def coverage_relation(
    left: TranslationCoverageWindow,
    right: TranslationCoverageWindow,
) -> CoverageRelation:
    left_bounds = coverage_bounds(left)
    right_bounds = coverage_bounds(right)
    if left_bounds is None or right_bounds is None:
        return "unknown"
    left_start, left_end = left_bounds
    right_start, right_end = right_bounds
    if left_end < right_start or right_end < left_start:
        return "disjoint"
    if left_bounds == right_bounds and left.mode is right.mode:
        return "equal"
    if left_start <= right_start and left_end >= right_end:
        return "contains"
    if right_start <= left_start and right_end >= left_end:
        return "within"
    return "partial"


def overlap_components(
    candidates: tuple[TranslationInputCandidate, ...],
) -> tuple[tuple[TranslationInputCandidate, ...], ...]:
    adjacency: dict[str, set[str]] = {
        candidate.candidate_id: set() for candidate in candidates
    }
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    for left, right in combinations(candidates, 2):
        if coverage_relation(left.coverage, right.coverage) == "disjoint":
            continue
        adjacency[left.candidate_id].add(right.candidate_id)
        adjacency[right.candidate_id].add(left.candidate_id)

    components: list[tuple[TranslationInputCandidate, ...]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.candidate_id in seen:
            continue
        stack = [candidate.candidate_id]
        component_ids: list[str] = []
        while stack:
            candidate_id = stack.pop()
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            component_ids.append(candidate_id)
            stack.extend(sorted(adjacency[candidate_id] - seen))
        components.append(
            tuple(
                sorted(
                    (candidate_by_id[candidate_id] for candidate_id in component_ids),
                    key=lambda item: item.candidate_id,
                )
            )
        )
    return tuple(components)


def winner_contains_all_candidates(
    *,
    winner: TranslationInputCandidate,
    candidates: tuple[TranslationInputCandidate, ...],
) -> bool:
    winner_bounds = coverage_bounds(winner.coverage)
    if winner_bounds is None:
        return False
    winner_start, winner_end = winner_bounds
    for candidate in candidates:
        candidate_bounds = coverage_bounds(candidate.coverage)
        if candidate_bounds is None:
            return False
        candidate_start, candidate_end = candidate_bounds
        if winner_start > candidate_start or winner_end < candidate_end:
            return False
    return True
