"""Translation execution for normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from tallylot.application.capture_paths import (
    claim_set_compatibility_draft_projection_fields_file,
    claim_set_gap_explanations_file,
    claim_set_gap_records_file,
    claim_set_product_file,
    claim_set_ref,
    claim_set_review_explanations_file,
    claim_set_review_records_file,
    evidence_set_compatibility_plan_file,
    evidence_set_product_file,
    evidence_set_ref,
)
from tallylot.application.compatibility import (
    build_translation_input_plan_payload,
    project_translation_batch_from_claim_set,
    reconstruct_translation_input_plan,
)
from tallylot.application.claim.coinbase_builder import build_coinbase_claim_set
from tallylot.application.evidence.evidence_sets import build_evidence_set_for_profile
from tallylot.application.evidence.statement_extraction import (
    StatementDocumentCollectionResult,
    StatementExtractionService,
)
from tallylot.application.normalization.models import NormalizationTranslationMetrics
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
    translation_metrics_from_result,
)
from tallylot.application.normalization.translation_inputs.artifacts import (
    TranslationArtifactContext,
    write_translation_input_candidates,
    write_translation_input_issues,
)
from tallylot.ports.evidence_sets import EvidenceSetRepositoryPort
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.claim_sets import ClaimSetRepositoryPort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch
from tallylot.ports.translation_inputs import TranslationInputPlanningAdapter
from tallylot.domain.types import JsonValue


@dataclass(frozen=True)
class TranslationExecutionResult:
    batch: SourceTranslationBatch
    metrics: NormalizationTranslationMetrics
    statement_documents: StatementDocumentCollectionResult
    evidence_set_id: str = ""
    evidence_set_ref: str = ""
    claim_set_id: str = ""
    claim_set_ref: str = ""


@dataclass(frozen=True)
class TranslationExecutionContext:
    output_dir: Path
    workspace_root: Path
    capture_metadata: CaptureMetadata | None
    artifacts: ArtifactStorePort
    evidence: EvidenceRepositoryPort
    evidence_sets: EvidenceSetRepositoryPort
    claim_sets: ClaimSetRepositoryPort
    statement_extraction: StatementExtractionService


def execute_translation(
    *,
    adapter: SourceAdapter,
    profile: SourceProfile,
    raw_dir: Path,
    context: TranslationExecutionContext,
) -> TranslationExecutionResult:
    statement_documents = (
        context.statement_extraction.collect_source_statement_documents(
            profile, raw_dir
        )
    )
    if not isinstance(adapter, TranslationInputPlanningAdapter):
        return TranslationExecutionResult(
            batch=adapter.translate(profile, raw_dir),
            statement_documents=statement_documents,
            metrics=NormalizationTranslationMetrics(
                translation_candidate_count=0,
                translation_selected_count=0,
                translation_superseded_count=0,
                translation_blocked_count=0,
                translation_planner_used=False,
            ),
        )

    candidates = adapter.describe_translation_inputs(profile, raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=candidates,
        capture_metadata=context.capture_metadata,
    )
    capture_uid = (
        ""
        if context.capture_metadata is None
        else str(context.capture_metadata.capture_uid)
    )
    capture_manifest_fingerprint = (
        ""
        if context.capture_metadata is None
        else context.capture_metadata.manifest_fingerprint
    )
    artifact_context = TranslationArtifactContext(
        output_dir=context.output_dir,
        profile=profile,
        capture_metadata=context.capture_metadata,
    )
    write_translation_input_candidates(
        artifacts=context.artifacts,
        context=artifact_context,
        candidates=planning_result.candidates,
    )
    evidence_set = build_evidence_set_for_profile(
        profile=profile,
        capture_uid=capture_uid,
        capture_manifest_fingerprint=capture_manifest_fingerprint,
        planner_result=planning_result,
        statement_documents=statement_documents,
    )
    evidence_set_id = ""
    evidence_set_path_ref = ""
    execution_plan = planning_result.plan
    compatibility_plan = planning_result.plan
    if evidence_set is not None:
        evidence_set_id = evidence_set.evidence_set_id
        evidence_set_path = evidence_set_product_file(
            context.workspace_root, evidence_set_id
        )
        context.evidence_sets.write_evidence_set(evidence_set_path, evidence_set)
        compatibility_plan = reconstruct_translation_input_plan(
            evidence_set=evidence_set,
            planning_result=planning_result,
        )
        compatibility_payload = build_translation_input_plan_payload(
            adapter_id=str(profile.adapter_id),
            capture_uid=capture_uid,
            plan=compatibility_plan,
        )
        context.artifacts.write_json(
            evidence_set_compatibility_plan_file(
                context.workspace_root, evidence_set_id
            ),
            compatibility_payload,
        )
        context.artifacts.write_json(
            context.output_dir / "translation_input_plan.json",
            compatibility_payload,
        )
        evidence_set_path_ref = evidence_set_ref(
            context.workspace_root, evidence_set_id
        )
    else:
        context.artifacts.write_json(
            context.output_dir / "translation_input_plan.json",
            build_translation_input_plan_payload(
                adapter_id=str(profile.adapter_id),
                capture_uid=capture_uid,
                plan=planning_result.plan,
            ),
        )
    write_translation_input_issues(
        evidence=context.evidence,
        context=artifact_context,
        issues=planning_result.issues,
    )
    metrics = translation_metrics_from_result(planning_result, planner_used=True)
    if compatibility_plan.blocked:
        raise ValueError(
            "translation input planning blocked normalization; inspect "
            f"{context.output_dir / 'translation_input_plan.json'} and "
            f"{context.output_dir / 'translation_input_issues.csv'}"
        )
    selected_batch = adapter.translate_selected_inputs(
        profile,
        raw_dir,
        execution_plan,
    )
    claim_set_id = ""
    claim_set_path_ref = ""
    if str(profile.adapter_id) == "coinbase" and evidence_set is not None:
        claim_build = build_coinbase_claim_set(
            profile=profile,
            evidence_set=evidence_set,
            evidence_set_ref=evidence_set_path_ref,
            planning_result=planning_result,
            batch=selected_batch,
        )
        if claim_build is not None:
            claim_set_id = claim_build.claim_set.claim_set_id
            claim_set_path = claim_set_product_file(
                context.workspace_root, claim_set_id
            )
            context.claim_sets.write_claim_set(claim_set_path, claim_build.claim_set)
            context.artifacts.write_json(
                claim_set_gap_records_file(context.workspace_root, claim_set_id),
                [record.to_payload() for record in claim_build.gap_records],
            )
            context.artifacts.write_json(
                claim_set_gap_explanations_file(context.workspace_root, claim_set_id),
                [record.to_payload() for record in claim_build.gap_explanations],
            )
            context.artifacts.write_json(
                claim_set_review_records_file(context.workspace_root, claim_set_id),
                [record.to_payload() for record in claim_build.review_records],
            )
            context.artifacts.write_json(
                claim_set_review_explanations_file(
                    context.workspace_root, claim_set_id
                ),
                [record.to_payload() for record in claim_build.review_explanations],
            )
            context.artifacts.write_json(
                claim_set_compatibility_draft_projection_fields_file(
                    context.workspace_root,
                    claim_set_id,
                ),
                cast(
                    JsonValue,
                    [
                        record.to_payload()
                        for record in claim_build.draft_projection_field_records
                    ],
                ),
            )
            persisted_claim_set = context.claim_sets.read_claim_set(claim_set_path)
            selected_batch = project_translation_batch_from_claim_set(
                claim_set=persisted_claim_set,
                evidence_set=evidence_set,
                draft_projection_field_records=claim_build.draft_projection_field_records,
                gap_records=claim_build.gap_records,
                gap_explanations=claim_build.gap_explanations,
                review_records=claim_build.review_records,
                review_explanations=claim_build.review_explanations,
                compatibility_issue_records=claim_build.compatibility_issue_records,
                compatibility_review_records=claim_build.compatibility_review_records,
            )
            claim_set_path_ref = claim_set_ref(context.workspace_root, claim_set_id)
    return TranslationExecutionResult(
        batch=selected_batch,
        statement_documents=statement_documents,
        metrics=metrics,
        evidence_set_id=evidence_set_id,
        evidence_set_ref=evidence_set_path_ref,
        claim_set_id=claim_set_id,
        claim_set_ref=claim_set_path_ref,
    )
