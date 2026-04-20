"""EvidenceSet to legacy translation-input compatibility helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
    EvidenceSet,
)
from tallylot.domain.types import JsonValue
from tallylot.ports.translation_inputs import (
    TRANSLATION_INPUT_PLANNER_VERSION,
    TranslationInputPlan,
    TranslationPlanDecision,
    TranslationPlanDecisionStatus,
    TranslationInputCandidate,
)

if TYPE_CHECKING:
    from tallylot.application.normalization.translation_inputs.models import (
        TranslationInputPlanningResult,
    )


def reconstruct_translation_input_plan(
    *,
    evidence_set: EvidenceSet,
    planning_result: TranslationInputPlanningResult | None = None,
) -> TranslationInputPlan:
    retail_members = [
        member
        for member in evidence_set.evidence_member_records
        if member.kind is EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE
    ]
    retail_selection = _retail_selection_record(evidence_set)
    planner_decisions = _planner_decisions_by_candidate(planning_result)
    selected_candidate_ids = tuple(
        _selected_candidate_ids(
            retail_members=retail_members,
            planning_result=planning_result,
        )
    )
    all_candidate_ids = tuple(
        sorted(_candidate_id_from_locator(member.locator) for member in retail_members)
    )
    blocked_status = _blocked_decision_status(retail_selection)
    blocked_reason = _blocked_decision_reason(blocked_status)
    superseded_status = _superseded_decision_status(retail_selection)
    decisions: list[TranslationPlanDecision] = []
    for member in sorted(retail_members, key=lambda item: item.locator):
        candidate_id = _candidate_id_from_locator(member.locator)
        planner_decision = planner_decisions.get(candidate_id)
        if planner_decision is not None and _planner_status_matches_member(
            member_status=member.status,
            planner_status=planner_decision.status,
        ):
            decisions.append(planner_decision)
            continue
        status: TranslationPlanDecisionStatus = "selected"
        reason = _selected_decision_reason(
            total_candidates=len(all_candidate_ids),
            selected_candidate_ids=selected_candidate_ids,
        )
        replaces_candidate_ids: tuple[str, ...] = ()
        conflicts_with_candidate_ids: tuple[str, ...] = ()
        if member.status is EvidenceMemberStatus.SUPERSEDED:
            status = superseded_status
            reason = "superseded by the selected translation input candidate"
        elif member.status is EvidenceMemberStatus.BLOCKED:
            status = blocked_status
            reason = blocked_reason
        decisions.append(
            TranslationPlanDecision(
                candidate_id=candidate_id,
                status=status,
                reason=reason,
                replaces_candidate_ids=replaces_candidate_ids,
                conflicts_with_candidate_ids=conflicts_with_candidate_ids,
            )
        )
    return TranslationInputPlan(
        selected_candidate_ids=selected_candidate_ids,
        decisions=tuple(sorted(decisions, key=lambda item: item.candidate_id)),
        blocked=any(decision.status.startswith("blocked") for decision in decisions),
    )


def _selected_candidate_ids(
    *,
    retail_members: list[EvidenceMemberRecord],
    planning_result: TranslationInputPlanningResult | None,
) -> tuple[str, ...]:
    selected_candidate_ids = {
        _candidate_id_from_locator(member.locator)
        for member in retail_members
        if member.status is EvidenceMemberStatus.SELECTED
    }
    if not selected_candidate_ids:
        return ()
    if planning_result is not None:
        ordered_ids = tuple(
            candidate_id
            for candidate_id in planning_result.plan.selected_candidate_ids
            if candidate_id in selected_candidate_ids
        )
        if set(ordered_ids) == selected_candidate_ids:
            return ordered_ids
        candidates_by_id = {
            candidate.candidate_id: candidate
            for candidate in planning_result.candidates
        }
        sortable_ids = selected_candidate_ids & set(candidates_by_id)
        if sortable_ids:
            ordered_sortable_ids = tuple(
                candidate_id
                for candidate_id, _candidate in sorted(
                    (
                        (candidate_id, candidates_by_id[candidate_id])
                        for candidate_id in sortable_ids
                    ),
                    key=lambda item: _selected_candidate_sort_key(item[1]),
                )
            )
            remaining_ids = tuple(
                sorted(selected_candidate_ids - set(ordered_sortable_ids))
            )
            return (*ordered_sortable_ids, *remaining_ids)
    return tuple(sorted(selected_candidate_ids))


def build_translation_input_plan_payload(
    *,
    adapter_id: str,
    capture_uid: str,
    plan: TranslationInputPlan,
) -> JsonValue:
    return cast(
        JsonValue,
        {
            "planner_version": TRANSLATION_INPUT_PLANNER_VERSION,
            "adapter_id": adapter_id,
            "capture_uid": capture_uid,
            "selected_candidate_ids": list(plan.selected_candidate_ids),
            "decisions": [
                {
                    "candidate_id": decision.candidate_id,
                    "status": decision.status,
                    "reason": decision.reason,
                    "replaces_candidate_ids": list(decision.replaces_candidate_ids),
                    "conflicts_with_candidate_ids": list(
                        decision.conflicts_with_candidate_ids
                    ),
                }
                for decision in plan.decisions
            ],
            "blocked": plan.blocked,
        },
    )


def _planner_decisions_by_candidate(
    planning_result: TranslationInputPlanningResult | None,
) -> dict[str, TranslationPlanDecision]:
    if planning_result is None:
        return {}
    return {
        decision.candidate_id: decision for decision in planning_result.plan.decisions
    }


def _planner_status_matches_member(
    *,
    member_status: EvidenceMemberStatus,
    planner_status: TranslationPlanDecisionStatus,
) -> bool:
    if member_status is EvidenceMemberStatus.SELECTED:
        return planner_status == "selected"
    if member_status is EvidenceMemberStatus.SUPERSEDED:
        return planner_status in {"superseded_identical", "superseded_replaced"}
    return planner_status.startswith("blocked")


def _candidate_id_from_locator(locator: tuple[str, ...]) -> str:
    return f"coinbase:retail_export:{locator[0]}"


def _selected_candidate_sort_key(
    candidate: TranslationInputCandidate,
) -> tuple[object, ...]:
    return (
        candidate.coverage.start_at or datetime.min.replace(tzinfo=UTC),
        candidate.coverage.end_at or datetime.max.replace(tzinfo=UTC),
        -_freshness_precedence(candidate.freshness.kind.value),
        -_freshness_sort_numeric_value(candidate),
        candidate.candidate_id,
    )


def _freshness_precedence(kind: str) -> int:
    return {
        "export_timestamp": 3,
        "capture_completed_at": 2,
        "adapter_rank": 1,
        "unknown": 0,
    }[kind]


def _freshness_sort_numeric_value(candidate: TranslationInputCandidate) -> float:
    if candidate.freshness.kind.value in {
        "export_timestamp",
        "capture_completed_at",
    }:
        if candidate.freshness.timestamp is None:
            return float("-inf")
        return candidate.freshness.timestamp.astimezone(UTC).timestamp()
    if candidate.freshness.kind.value == "adapter_rank":
        return (
            float("-inf")
            if candidate.freshness.rank is None
            else float(candidate.freshness.rank)
        )
    return float("-inf")


def _retail_selection_record(evidence_set: EvidenceSet) -> EvidenceSelectionRecord:
    for selection in evidence_set.evidence_selection_records:
        if selection.key == ("retail_activity_export_file",):
            return selection
    return EvidenceSelectionRecord(
        evidence_set_id=evidence_set.evidence_set_id,
        selection_id=f"{evidence_set.evidence_set_id}:retail_activity_export_file",
        key=("retail_activity_export_file",),
        fingerprint="",
        basis=EvidenceSelectionBasis.SINGLE_MEMBER,
        blocking_gap_refs=(),
    )


def _selected_decision_reason(
    *,
    total_candidates: int,
    selected_candidate_ids: tuple[str, ...],
) -> str:
    if total_candidates == 1 or len(selected_candidate_ids) > 1:
        return "candidate is disjoint within its selection group"
    return "winner selected for deterministic translation input planning"


def _superseded_decision_status(
    selection: EvidenceSelectionRecord,
) -> TranslationPlanDecisionStatus:
    if selection.basis is EvidenceSelectionBasis.DUPLICATE:
        return "superseded_identical"
    return "superseded_replaced"


def _blocked_decision_status(
    selection: EvidenceSelectionRecord,
) -> TranslationPlanDecisionStatus:
    refs = set(selection.blocking_gap_refs)
    for status in (
        "blocked_unknown_coverage",
        "blocked_incomparable_candidates",
        "blocked_invalid_candidate",
        "blocked_partial_overlap",
        "blocked_ambiguous_freshness",
    ):
        if f"translation_input_plan:{status}" in refs:
            return status
    if selection.basis is EvidenceSelectionBasis.AMBIGUOUS_OVERLAP:
        return "blocked_ambiguous_freshness"
    return "blocked_incomparable_candidates"


def _blocked_decision_reason(status: str) -> str:
    if status == "blocked_unknown_coverage":
        return (
            "translation input planning cannot compare multiple candidates when "
            "any candidate has unknown event-time coverage"
        )
    if status == "blocked_incomparable_candidates":
        return "overlapping candidates are marked incomparable by the adapter"
    if status == "blocked_invalid_candidate":
        return "candidate validation errors prevent deterministic planning"
    if status == "blocked_partial_overlap":
        return (
            "replaceable range candidates overlap, but the freshest winner does "
            "not fully supersede the overlapping set"
        )
    return "replaceable range candidates do not have a unique freshest winner"
