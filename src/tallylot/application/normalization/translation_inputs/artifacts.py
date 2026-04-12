"""Translation input planning artifact writers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from tallylot.application.normalization.translation_inputs.models import (
    PLANNER_VERSION,
    TranslationInputPlanningResult,
)
from tallylot.domain.value_objects import format_timestamp
from tallylot.domain.types import JsonValue
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.translation_inputs import (
    TranslationInputCandidate,
    TranslationPlanDecision,
)


@dataclass(frozen=True)
class TranslationArtifactContext:
    output_dir: Path
    profile: SourceProfile
    capture_metadata: CaptureMetadata | None


def write_translation_input_artifacts(
    *,
    artifacts: ArtifactStorePort,
    evidence: EvidenceRepositoryPort,
    context: TranslationArtifactContext,
    result: TranslationInputPlanningResult,
) -> None:
    artifacts.write_json(
        context.output_dir / "translation_input_candidates.json",
        cast(
            JsonValue,
            {
                "planner_version": PLANNER_VERSION,
                "adapter_id": str(context.profile.adapter_id),
                "capture_uid": _capture_uid(
                    context.profile,
                    context.capture_metadata,
                ),
                "candidates": [
                    _candidate_to_json(candidate) for candidate in result.candidates
                ],
            },
        ),
    )
    artifacts.write_json(
        context.output_dir / "translation_input_plan.json",
        cast(
            JsonValue,
            {
                "planner_version": PLANNER_VERSION,
                "adapter_id": str(context.profile.adapter_id),
                "capture_uid": _capture_uid(
                    context.profile,
                    context.capture_metadata,
                ),
                "selected_candidate_ids": list(result.plan.selected_candidate_ids),
                "decisions": [
                    _decision_to_json(decision) for decision in result.plan.decisions
                ],
                "blocked": result.plan.blocked,
            },
        ),
    )
    evidence.write_issue_records(
        context.output_dir / "translation_input_issues.csv",
        result.issues,
    )


def _candidate_to_json(candidate: TranslationInputCandidate) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "selection_group": candidate.selection_group,
        "family_id": candidate.family_id,
        "member_relative_paths": list(candidate.member_relative_paths),
        "selection_mode": candidate.selection_mode.value,
        "coverage": {
            "start_at": _optional_timestamp(candidate.coverage.start_at),
            "start_precision": _optional_text(candidate.coverage.start_precision),
            "end_at": _optional_timestamp(candidate.coverage.end_at),
            "end_precision": _optional_text(candidate.coverage.end_precision),
            "mode": candidate.coverage.mode.value,
        },
        "freshness": {
            "kind": candidate.freshness.kind.value,
            "timestamp": _optional_timestamp(candidate.freshness.timestamp),
            "rank": candidate.freshness.rank,
        },
        "content_fingerprint": candidate.content_fingerprint,
        "comparison_key": candidate.comparison_key,
        "description": candidate.description,
        "comparable": candidate.comparable,
        "notes": list(candidate.notes),
    }


def _decision_to_json(decision: TranslationPlanDecision) -> dict[str, object]:
    return {
        "candidate_id": decision.candidate_id,
        "status": decision.status,
        "reason": decision.reason,
        "replaces_candidate_ids": list(decision.replaces_candidate_ids),
        "conflicts_with_candidate_ids": list(decision.conflicts_with_candidate_ids),
    }


def _capture_uid(
    profile: SourceProfile,
    capture_metadata: CaptureMetadata | None,
) -> str:
    if capture_metadata is not None:
        return str(capture_metadata.capture_uid)
    return profile.metadata.get("capture_uid", "")


def _optional_timestamp(value: object) -> str:
    if value is None:
        return ""
    return format_timestamp(cast(datetime, value))


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)
