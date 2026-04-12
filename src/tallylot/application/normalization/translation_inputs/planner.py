"""Deterministic translation input planning."""

from __future__ import annotations

from tallylot.domain.issues import IssueRecord
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.translation_inputs import (
    TranslationInputCandidate,
    TranslationPlanDecision,
)

from .models import (
    TranslationInputPlanningResult,
    build_translation_plan,
)
from .selection import invalid_group_issues, plan_group
from .validation import (
    group_contexts,
    group_failures,
    group_policy,
    validate_candidates,
)


def plan_translation_inputs(
    *,
    profile: SourceProfile,
    candidates: tuple[TranslationInputCandidate, ...],
    capture_metadata: CaptureMetadata | None = None,
) -> TranslationInputPlanningResult:
    ordered_candidates = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    contexts = validate_candidates(
        candidates=ordered_candidates,
        inventory_by_path={
            entry.relative_path: entry for entry in profile.file_inventory
        },
        capture_metadata=capture_metadata,
    )

    issues: list[IssueRecord] = []
    decisions: dict[str, TranslationPlanDecision] = {}
    failures = group_failures(contexts)
    for context in contexts.values():
        if context.valid:
            continue
        issues.append(
            IssueRecord(
                issue_id=(
                    f"{profile.adapter_id}:{context.candidate.candidate_id}:"
                    "blocked_invalid_candidate"
                ),
                source=str(profile.source),
                adapter_id=str(profile.adapter_id),
                severity="high",
                kind="blocked_invalid_candidate",
                message="; ".join(context.validation_errors),
                raw_file=(
                    context.candidate.member_relative_paths[0]
                    if context.candidate.member_relative_paths
                    else ""
                ),
                status="needs_review",
            )
        )

    for group_id, group_contexts_value in group_contexts(contexts).items():
        group_candidates = tuple(context.candidate for context in group_contexts_value)
        failure = failures.get(group_id)
        if failure is not None:
            issues.extend(
                invalid_group_issues(
                    profile=profile,
                    group_contexts_value=group_contexts_value,
                    status=failure.status,
                    reason=failure.reason,
                )
            )
            for context in group_contexts_value:
                reason = (
                    "; ".join(context.validation_errors)
                    if context.validation_errors
                    else failure.reason
                )
                decisions[context.candidate.candidate_id] = TranslationPlanDecision(
                    candidate_id=context.candidate.candidate_id,
                    status=failure.status,
                    reason=reason,
                    conflicts_with_candidate_ids=tuple(
                        sorted(
                            candidate.candidate_id
                            for candidate in group_candidates
                            if candidate.candidate_id != context.candidate.candidate_id
                        )
                    ),
                )
            continue

        policy = group_policy(group_candidates)
        if policy is None:
            reason = (
                "translation input candidates in the same selection group must share "
                "appendable_range or replaceable_range semantics, unless the group "
                "contains exclusive_snapshot candidates"
            )
            issues.extend(
                invalid_group_issues(
                    profile=profile,
                    group_contexts_value=group_contexts_value,
                    status="blocked_invalid_candidate",
                    reason=reason,
                )
            )
            for context in group_contexts_value:
                decisions[context.candidate.candidate_id] = TranslationPlanDecision(
                    candidate_id=context.candidate.candidate_id,
                    status="blocked_invalid_candidate",
                    reason=reason,
                    conflicts_with_candidate_ids=tuple(
                        sorted(
                            candidate.candidate_id
                            for candidate in group_candidates
                            if candidate.candidate_id != context.candidate.candidate_id
                        )
                    ),
                )
            continue

        planned_group = plan_group(
            profile=profile,
            candidates=group_candidates,
            selection_mode=policy,
        )
        issues.extend(planned_group.issues)
        decisions.update(
            {decision.candidate_id: decision for decision in planned_group.decisions}
        )

    return TranslationInputPlanningResult(
        candidates=ordered_candidates,
        plan=build_translation_plan(contexts=contexts, decisions=decisions),
        issues=tuple(issues),
    )
