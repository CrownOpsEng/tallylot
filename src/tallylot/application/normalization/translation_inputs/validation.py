"""Translation input candidate validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations

from tallylot.domain.value_objects import require_utc_datetime
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.source_profiles import FileInventoryEntry
from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
    TranslationPlanDecisionStatus,
    TranslationSelectionMode,
    translation_input_content_fingerprint,
)

from .models import CandidateContext


@dataclass(frozen=True)
class GroupFailure:
    status: TranslationPlanDecisionStatus
    reason: str


def validate_candidates(
    *,
    candidates: tuple[TranslationInputCandidate, ...],
    inventory_by_path: dict[str, FileInventoryEntry],
    capture_metadata: CaptureMetadata | None,
) -> dict[str, CandidateContext]:
    duplicate_candidate_ids = duplicated_candidate_ids(candidates)
    return {
        candidate.candidate_id: validate_candidate(
            candidate,
            inventory_by_path=inventory_by_path,
            capture_metadata=capture_metadata,
            duplicate_candidate_ids=duplicate_candidate_ids,
        )
        for candidate in candidates
    }


def group_contexts(
    contexts: dict[str, CandidateContext],
) -> dict[str, tuple[CandidateContext, ...]]:
    grouped: dict[str, list[CandidateContext]] = defaultdict(list)
    for context in contexts.values():
        grouped[context.candidate.selection_group].append(context)
    return {
        group_id: tuple(
            sorted(group_candidates, key=lambda item: item.candidate.candidate_id)
        )
        for group_id, group_candidates in grouped.items()
    }


def group_failures(
    contexts: dict[str, CandidateContext],
) -> dict[str, GroupFailure]:
    failures: dict[str, GroupFailure] = {}
    for group_id, group_candidates in group_contexts(contexts).items():
        if any(not context.valid for context in group_candidates):
            failures[group_id] = GroupFailure(
                status="blocked_invalid_candidate",
                reason="candidate validation errors prevent deterministic planning",
            )
            continue
        if len(group_candidates) > 1 and any(
            context.candidate.coverage.mode is TranslationCoverageMode.UNKNOWN
            for context in group_candidates
        ):
            failures[group_id] = GroupFailure(
                status="blocked_unknown_coverage",
                reason=(
                    "translation input planning cannot compare multiple candidates "
                    "when any candidate has unknown event-time coverage"
                ),
            )
            continue
        if has_invalid_member_overlap(group_candidates):
            failures[group_id] = GroupFailure(
                status="blocked_invalid_candidate",
                reason=(
                    "candidate members overlap inside one selection group without "
                    "an exact alternative candidate definition"
                ),
            )
    return failures


def group_policy(
    candidates: tuple[TranslationInputCandidate, ...],
) -> TranslationSelectionMode | None:
    modes = {candidate.selection_mode for candidate in candidates}
    if TranslationSelectionMode.EXCLUSIVE_SNAPSHOT in modes:
        return TranslationSelectionMode.EXCLUSIVE_SNAPSHOT
    if len(modes) == 1:
        return next(iter(modes))
    return None


def group_block_reason(group_contexts_value: tuple[CandidateContext, ...]) -> str:
    candidate_ids = ", ".join(
        context.candidate.candidate_id for context in group_contexts_value
    )
    return f"translation input group is invalid: {candidate_ids}"


def validate_candidate(
    candidate: TranslationInputCandidate,
    *,
    inventory_by_path: dict[str, FileInventoryEntry],
    capture_metadata: CaptureMetadata | None,
    duplicate_candidate_ids: set[str],
) -> CandidateContext:
    member_entries: list[FileInventoryEntry] = []
    errors: list[str] = []
    if candidate.candidate_id in duplicate_candidate_ids:
        errors.append(f"candidate id {candidate.candidate_id!r} is duplicated")
    if not candidate.selection_group.strip():
        errors.append("selection_group must be a non-empty string")
    if not candidate.family_id.strip():
        errors.append("family_id must be a non-empty string")
    if not candidate.comparison_key.strip():
        errors.append("comparison_key must be a non-empty string")
    if not candidate.description.strip():
        errors.append("description must be a non-empty string")
    if not candidate.member_relative_paths:
        errors.append("candidate must include at least one member path")
    if len(set(candidate.member_relative_paths)) != len(
        candidate.member_relative_paths
    ):
        errors.append("candidate member paths must be unique")
    for member_path in candidate.member_relative_paths:
        entry = inventory_by_path.get(member_path)
        if entry is None:
            errors.append(
                f"member path {member_path!r} was not found in profile inventory"
            )
            continue
        member_entries.append(entry)
    if candidate.content_fingerprint.strip() == "":
        errors.append("content_fingerprint must be non-empty")
    elif member_entries:
        expected_fingerprint = translation_input_content_fingerprint(
            member_sha256s=tuple(sorted(entry.sha256 for entry in member_entries)),
            family_id=candidate.family_id,
            selection_group=candidate.selection_group,
            selection_mode=candidate.selection_mode,
        )
        if candidate.content_fingerprint != expected_fingerprint:
            errors.append(
                "content_fingerprint does not match candidate member inventory"
            )
    errors.extend(validate_coverage(candidate.coverage))
    errors.extend(
        validate_freshness(
            candidate.freshness,
            capture_metadata=capture_metadata,
        )
    )
    return CandidateContext(
        candidate=candidate,
        member_entries=tuple(member_entries),
        validation_errors=tuple(errors),
    )


def validate_coverage(coverage: TranslationCoverageWindow) -> tuple[str, ...]:
    errors: list[str] = []
    if coverage.mode is TranslationCoverageMode.UNKNOWN:
        errors.extend(_validate_unknown_coverage(coverage))
        return tuple(errors)
    errors.extend(_validate_known_coverage_mode(coverage))
    if coverage.start_at is not None:
        validate_utc_datetime(coverage.start_at, errors, label="coverage start_at")
    if coverage.end_at is not None:
        validate_utc_datetime(coverage.end_at, errors, label="coverage end_at")
    if (
        coverage.start_at is not None
        and coverage.end_at is not None
        and coverage.start_at > coverage.end_at
    ):
        errors.append("coverage start_at must not be after end_at")
    return tuple(errors)


def _validate_unknown_coverage(
    coverage: TranslationCoverageWindow,
) -> tuple[str, ...]:
    if any(
        value is not None
        for value in (
            coverage.start_at,
            coverage.start_precision,
            coverage.end_at,
            coverage.end_precision,
        )
    ):
        return ("unknown coverage cannot carry bounds or precisions",)
    return ()


def _validate_known_coverage_mode(
    coverage: TranslationCoverageWindow,
) -> tuple[str, ...]:
    if coverage.mode is TranslationCoverageMode.BOUNDED:
        return _validate_bounded_coverage(coverage)
    if coverage.mode is TranslationCoverageMode.UNBOUNDED_START:
        return _validate_unbounded_start_coverage(coverage)
    if coverage.mode is TranslationCoverageMode.UNBOUNDED_END:
        return _validate_unbounded_end_coverage(coverage)
    return ()


def _validate_bounded_coverage(
    coverage: TranslationCoverageWindow,
) -> tuple[str, ...]:
    errors: list[str] = []
    if coverage.start_at is None or coverage.end_at is None:
        errors.append("bounded coverage requires start_at and end_at")
    if coverage.start_precision is None or coverage.end_precision is None:
        errors.append("bounded coverage requires start_precision and end_precision")
    return tuple(errors)


def _validate_unbounded_start_coverage(
    coverage: TranslationCoverageWindow,
) -> tuple[str, ...]:
    errors: list[str] = []
    if coverage.start_at is not None or coverage.start_precision is not None:
        errors.append("unbounded_start coverage cannot carry a start bound")
    if coverage.end_at is None or coverage.end_precision is None:
        errors.append("unbounded_start coverage requires an end bound")
    return tuple(errors)


def _validate_unbounded_end_coverage(
    coverage: TranslationCoverageWindow,
) -> tuple[str, ...]:
    errors: list[str] = []
    if coverage.end_at is not None or coverage.end_precision is not None:
        errors.append("unbounded_end coverage cannot carry an end bound")
    if coverage.start_at is None or coverage.start_precision is None:
        errors.append("unbounded_end coverage requires a start bound")
    return tuple(errors)


def validate_freshness(
    freshness: TranslationFreshness,
    *,
    capture_metadata: CaptureMetadata | None,
) -> tuple[str, ...]:
    errors: list[str] = []
    if freshness.kind is TranslationFreshnessKind.UNKNOWN:
        if freshness.timestamp is not None or freshness.rank is not None:
            errors.append("unknown freshness cannot carry timestamp or rank")
        return tuple(errors)
    if freshness.kind in {
        TranslationFreshnessKind.EXPORT_TIMESTAMP,
        TranslationFreshnessKind.CAPTURE_COMPLETED_AT,
    }:
        if freshness.timestamp is None:
            errors.append(f"{freshness.kind.value} freshness requires timestamp")
        if freshness.rank is not None:
            errors.append(f"{freshness.kind.value} freshness cannot carry rank")
        if freshness.timestamp is not None:
            validate_utc_datetime(
                freshness.timestamp,
                errors,
                label=f"{freshness.kind.value} freshness timestamp",
            )
    elif freshness.kind is TranslationFreshnessKind.ADAPTER_RANK:
        if freshness.rank is None:
            errors.append("adapter_rank freshness requires rank")
        if freshness.timestamp is not None:
            errors.append("adapter_rank freshness cannot carry timestamp")
    if (
        freshness.kind is TranslationFreshnessKind.CAPTURE_COMPLETED_AT
        and capture_metadata is not None
        and freshness.timestamp is not None
        and freshness.timestamp != capture_metadata.intake_completed_at
    ):
        errors.append(
            "capture_completed_at freshness must match the capture metadata completion time"
        )
    return tuple(errors)


def validate_utc_datetime(
    value: datetime,
    errors: list[str],
    *,
    label: str,
) -> None:
    try:
        require_utc_datetime(value, label=label)
    except ValueError as error:
        errors.append(str(error))


def duplicated_candidate_ids(
    candidates: tuple[TranslationInputCandidate, ...],
) -> set[str]:
    counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        counts[candidate.candidate_id] += 1
    return {candidate_id for candidate_id, count in counts.items() if count > 1}


def has_invalid_member_overlap(
    group_contexts_value: tuple[CandidateContext, ...],
) -> bool:
    member_signatures = {
        context.candidate.candidate_id: tuple(
            sorted(context.candidate.member_relative_paths)
        )
        for context in group_contexts_value
    }
    for left, right in combinations(group_contexts_value, 2):
        left_members = set(left.candidate.member_relative_paths)
        right_members = set(right.candidate.member_relative_paths)
        if not left_members.intersection(right_members):
            continue
        if (
            member_signatures[left.candidate.candidate_id]
            != member_signatures[right.candidate.candidate_id]
        ):
            return True
    return False
