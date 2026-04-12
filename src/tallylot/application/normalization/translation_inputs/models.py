"""Translation input planning result models."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.application.normalization.models import (
    NormalizationTranslationMetrics,
)
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import FileInventoryEntry
from tallylot.ports.translation_inputs import (
    TranslationInputCandidate,
    TranslationInputPlan,
    TranslationPlanDecision,
)

from .freshness import freshness_precedence, freshness_sort_numeric_value
from .overlap import MAX_COVERAGE_BOUND, MIN_COVERAGE_BOUND

PLANNER_VERSION = "translation-input-planner-v1"


@dataclass(frozen=True)
class TranslationInputPlanningResult:
    candidates: tuple[TranslationInputCandidate, ...]
    plan: TranslationInputPlan
    issues: tuple[IssueRecord, ...]


@dataclass(frozen=True)
class CandidateContext:
    candidate: TranslationInputCandidate
    member_entries: tuple[FileInventoryEntry, ...]
    validation_errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.validation_errors


def translation_metrics_from_result(
    result: TranslationInputPlanningResult,
    *,
    planner_used: bool,
) -> NormalizationTranslationMetrics:
    return NormalizationTranslationMetrics(
        translation_candidate_count=len(result.candidates),
        translation_selected_count=len(result.plan.selected_candidate_ids),
        translation_superseded_count=sum(
            1
            for decision in result.plan.decisions
            if decision.status in {"superseded_identical", "superseded_replaced"}
        ),
        translation_blocked_count=sum(
            1
            for decision in result.plan.decisions
            if decision.status.startswith("blocked")
        ),
        translation_planner_used=planner_used,
    )


def build_translation_plan(
    *,
    contexts: dict[str, CandidateContext],
    decisions: dict[str, TranslationPlanDecision],
) -> TranslationInputPlan:
    return TranslationInputPlan(
        selected_candidate_ids=tuple(
            candidate_id
            for candidate_id, decision in sorted(
                decisions.items(),
                key=lambda item: selected_candidate_sort_key(
                    contexts[item[0]].candidate
                ),
            )
            if decision.status == "selected"
        ),
        decisions=tuple(decisions[candidate_id] for candidate_id in sorted(decisions)),
        blocked=any(
            decision.status.startswith("blocked") for decision in decisions.values()
        ),
    )


def selected_candidate_sort_key(
    candidate: TranslationInputCandidate,
) -> tuple[object, ...]:
    return (
        candidate.coverage.start_at or MIN_COVERAGE_BOUND,
        candidate.coverage.end_at or MAX_COVERAGE_BOUND,
        -freshness_precedence(candidate.freshness.kind),
        -freshness_sort_numeric_value(candidate.freshness),
        candidate.candidate_id,
    )
