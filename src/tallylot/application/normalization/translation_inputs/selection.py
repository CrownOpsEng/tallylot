"""Translation input group selection rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.translation_inputs import (
    TranslationInputCandidate,
    TranslationPlanDecision,
    TranslationPlanDecisionStatus,
    TranslationSelectionMode,
)

from .freshness import (
    all_identical_candidates,
    deterministic_duplicate_winner,
    freshest_candidates,
)
from .models import CandidateContext
from .overlap import overlap_components, winner_contains_all_candidates


@dataclass(frozen=True)
class PlannedGroup:
    decisions: tuple[TranslationPlanDecision, ...]
    issues: tuple[IssueRecord, ...]


def plan_group(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
    selection_mode: TranslationSelectionMode,
) -> PlannedGroup:
    if selection_mode is TranslationSelectionMode.EXCLUSIVE_SNAPSHOT:
        return plan_exclusive_group(profile=profile, candidates=candidates)

    decisions: list[TranslationPlanDecision] = []
    issues: list[IssueRecord] = []
    for component in overlap_components(candidates):
        planned_component = plan_overlap_component(
            profile=profile,
            candidates=component,
            selection_mode=selection_mode,
        )
        decisions.extend(planned_component.decisions)
        issues.extend(planned_component.issues)
    return PlannedGroup(decisions=tuple(decisions), issues=tuple(issues))


def plan_exclusive_group(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
) -> PlannedGroup:
    if len(candidates) == 1:
        candidate = candidates[0]
        return PlannedGroup(
            decisions=(
                TranslationPlanDecision(
                    candidate_id=candidate.candidate_id,
                    status="selected",
                    reason="exclusive snapshot group contains one candidate",
                ),
            ),
            issues=(),
        )

    freshest = freshest_candidates(candidates)
    if len(freshest) != 1 and not all_identical_candidates(candidates):
        return blocked_group(
            profile=profile,
            candidates=candidates,
            status="blocked_ambiguous_freshness",
            reason="exclusive snapshot candidates do not have a unique freshest winner",
        )
    winner = deterministic_duplicate_winner(freshest or candidates)
    return build_supersession_plan(
        profile=profile,
        candidates=candidates,
        winner=winner,
    )


def plan_overlap_component(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
    selection_mode: TranslationSelectionMode,
) -> PlannedGroup:
    if len(candidates) == 1:
        candidate = candidates[0]
        return PlannedGroup(
            decisions=(
                TranslationPlanDecision(
                    candidate_id=candidate.candidate_id,
                    status="selected",
                    reason="candidate is disjoint within its selection group",
                ),
            ),
            issues=(),
        )
    if any(not candidate.comparable for candidate in candidates):
        return blocked_group(
            profile=profile,
            candidates=candidates,
            status="blocked_incomparable_candidates",
            reason="overlapping candidates are marked incomparable by the adapter",
        )
    if len({candidate.comparison_key for candidate in candidates}) != 1:
        return blocked_group(
            profile=profile,
            candidates=candidates,
            status="blocked_incomparable_candidates",
            reason="overlapping candidates do not share a comparison key",
        )
    if selection_mode is TranslationSelectionMode.APPENDABLE_RANGE:
        if not all_identical_candidates(candidates):
            return blocked_group(
                profile=profile,
                candidates=candidates,
                status="blocked_partial_overlap",
                reason=(
                    "appendable range candidates overlap and cannot be merged without "
                    "an exact identical replacement"
                ),
            )
        winner = deterministic_duplicate_winner(
            freshest_candidates(candidates) or candidates
        )
        return build_supersession_plan(
            profile=profile,
            candidates=candidates,
            winner=winner,
        )

    freshest = freshest_candidates(candidates)
    if len(freshest) != 1 and not all_identical_candidates(candidates):
        return blocked_group(
            profile=profile,
            candidates=candidates,
            status="blocked_ambiguous_freshness",
            reason="replaceable range candidates do not have a unique freshest winner",
        )
    winner = deterministic_duplicate_winner(freshest or candidates)
    if not winner_contains_all_candidates(winner=winner, candidates=candidates):
        return blocked_group(
            profile=profile,
            candidates=candidates,
            status="blocked_partial_overlap",
            reason=(
                "replaceable range candidates overlap, but the freshest winner does "
                "not fully supersede the overlapping set"
            ),
        )
    return build_supersession_plan(
        profile=profile,
        candidates=candidates,
        winner=winner,
    )


def invalid_group_issues(
    *,
    profile: SourceProfile,
    group_contexts_value: tuple[CandidateContext, ...],
    reason: str,
) -> tuple[IssueRecord, ...]:
    candidate_ids = tuple(
        sorted(context.candidate.candidate_id for context in group_contexts_value)
    )
    return tuple(
        issue_for_candidate(
            profile=profile,
            candidate=context.candidate,
            status="blocked_invalid_candidate",
            reason=reason,
            conflicts_with_candidate_ids=tuple(
                candidate_id
                for candidate_id in candidate_ids
                if candidate_id != context.candidate.candidate_id
            ),
        )
        for context in group_contexts_value
    )


def blocked_group(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
    status: TranslationPlanDecisionStatus,
    reason: str,
) -> PlannedGroup:
    return PlannedGroup(
        decisions=tuple(
            TranslationPlanDecision(
                candidate_id=candidate.candidate_id,
                status=status,
                reason=reason,
                conflicts_with_candidate_ids=tuple(
                    sorted(
                        other.candidate_id
                        for other in candidates
                        if other.candidate_id != candidate.candidate_id
                    )
                ),
            )
            for candidate in candidates
        ),
        issues=tuple(
            issue_for_candidate(
                profile=profile,
                candidate=candidate,
                status=status,
                reason=reason,
                conflicts_with_candidate_ids=tuple(
                    sorted(
                        other.candidate_id
                        for other in candidates
                        if other.candidate_id != candidate.candidate_id
                    )
                ),
            )
            for candidate in candidates
        ),
    )


def issue_for_candidate(
    *,
    profile: SourceProfile,
    candidate: TranslationInputCandidate,
    status: TranslationPlanDecisionStatus,
    reason: str,
    conflicts_with_candidate_ids: tuple[str, ...] = (),
    replaces_candidate_ids: tuple[str, ...] = (),
) -> IssueRecord:
    candidate_path = (
        candidate.member_relative_paths[0] if candidate.member_relative_paths else ""
    )
    conflict_text = ""
    if conflicts_with_candidate_ids:
        conflict_text = f" Conflicts: {', '.join(conflicts_with_candidate_ids)}."
    replace_text = ""
    if replaces_candidate_ids:
        replace_text = f" Replaces: {', '.join(replaces_candidate_ids)}."
    return IssueRecord(
        issue_id=f"{profile.adapter_id}:{candidate.candidate_id}:{status}",
        source=str(profile.source),
        adapter_id=str(profile.adapter_id),
        severity="high",
        kind=status,
        message=f"{reason}{replace_text}{conflict_text}",
        raw_file=candidate_path,
        status="needs_review",
    )


def build_supersession_plan(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
    winner: TranslationInputCandidate,
) -> PlannedGroup:
    replaced_candidate_ids = tuple(
        sorted(
            candidate.candidate_id
            for candidate in candidates
            if candidate.candidate_id != winner.candidate_id
        )
    )
    decisions: list[TranslationPlanDecision] = [
        TranslationPlanDecision(
            candidate_id=winner.candidate_id,
            status="selected",
            reason="winner selected for deterministic translation input planning",
            replaces_candidate_ids=replaced_candidate_ids,
        )
    ]
    for candidate in candidates:
        if candidate.candidate_id == winner.candidate_id:
            continue
        decisions.append(
            TranslationPlanDecision(
                candidate_id=candidate.candidate_id,
                status=superseded_status(candidate, winner),
                reason="superseded by the selected translation input candidate",
                conflicts_with_candidate_ids=(winner.candidate_id,),
            )
        )
    return PlannedGroup(decisions=tuple(decisions), issues=())


def superseded_status(
    candidate: TranslationInputCandidate,
    winner: TranslationInputCandidate,
) -> Literal["superseded_identical", "superseded_replaced"]:
    if (
        candidate.coverage == winner.coverage
        and candidate.content_fingerprint == winner.content_fingerprint
    ):
        return "superseded_identical"
    return "superseded_replaced"
