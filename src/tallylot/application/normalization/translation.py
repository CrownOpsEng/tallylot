"""Translation execution for normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.normalization.models import NormalizationTranslationMetrics
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
    translation_metrics_from_result,
    write_translation_input_artifacts,
)
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch
from tallylot.ports.translation_inputs import TranslationInputPlanningAdapter


@dataclass(frozen=True)
class TranslationExecutionResult:
    batch: SourceTranslationBatch
    metrics: NormalizationTranslationMetrics


def execute_translation(
    *,
    adapter: SourceAdapter,
    profile: SourceProfile,
    raw_dir: Path,
    output_dir: Path,
    capture_metadata: CaptureMetadata | None,
    artifacts: ArtifactStorePort,
    evidence: EvidenceRepositoryPort,
) -> TranslationExecutionResult:
    if not isinstance(adapter, TranslationInputPlanningAdapter):
        return TranslationExecutionResult(
            batch=adapter.translate(profile, raw_dir),
            metrics=NormalizationTranslationMetrics(
                translation_candidate_count=0,
                translation_selected_count=0,
                translation_superseded_count=0,
                translation_blocked_count=0,
                translation_planner_used=False,
            ),
        )

    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
        capture_metadata=capture_metadata,
    )
    write_translation_input_artifacts(
        artifacts,
        evidence,
        output_dir,
        profile=profile,
        capture_metadata=capture_metadata,
        result=planning_result,
    )
    metrics = translation_metrics_from_result(planning_result, planner_used=True)
    if planning_result.plan.blocked:
        raise ValueError(
            "translation input planning blocked normalization; inspect "
            f"{output_dir / 'translation_input_plan.json'} and "
            f"{output_dir / 'translation_input_issues.csv'}"
        )
    return TranslationExecutionResult(
        batch=adapter.translate_selected_inputs(
            profile,
            raw_dir,
            planning_result.plan,
        ),
        metrics=metrics,
    )
