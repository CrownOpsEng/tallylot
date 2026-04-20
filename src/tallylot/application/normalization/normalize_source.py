"""Normalization workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace

from tallylot.application.facts.compiler import compile_activity_drafts_with_feedback
from tallylot.application.balances import (
    derive_balance_snapshots,
    latest_balance_targets,
)
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.capture_paths import require_capture_root
from tallylot.application.intake.captures.persistence import (
    append_capture_status_record,
    update_source_inventory_summary,
)
from tallylot.application.normalization.contracts import (
    NormalizeRequest,
    NormalizeResponse,
)
from tallylot.application.normalization.issue_context import (
    enrich_issue_context_timestamps,
    enrich_review_context_timestamps,
)
from tallylot.application.profiling.build_profile import BuildProfileUseCase
from tallylot.application.profiling.families import has_family_for_adapter
from tallylot.application.resource_refs import path_from_ref
from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
)
from tallylot.domain.issues import IssueRecord
from tallylot.ports.adapter_contracts import AdapterCapability
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.captures import CaptureMetadata
from tallylot.ports.claim_sets import ClaimSetRepositoryPort
from tallylot.ports.evidence import EvidenceRepositoryPort, LocationInventoryRecord
from tallylot.ports.evidence_sets import EvidenceSetRepositoryPort
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.source_adapters import SourceAdapter, SourceAdapterRegistryPort
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch

from .annotations import annotation_records_from_drafts, location_annotation_records
from .artifacts import write_normalization_artifacts
from .models import (
    NormalizationOutputs,
    NormalizationWindowStats,
)
from .summary import build_normalization_summary
from .translation import execute_translation
from .translation import TranslationExecutionContext
from .window import (
    filter_drafts_by_window,
    filter_issues_by_window,
    filter_reviews_by_window,
)


@dataclass(frozen=True)
class NormalizationDependencies:
    source_registry: SourceAdapterRegistryPort
    profile_use_case: BuildProfileUseCase
    facts: FactRepositoryPort
    evidence: EvidenceRepositoryPort
    evidence_sets: EvidenceSetRepositoryPort
    claim_sets: ClaimSetRepositoryPort
    artifacts: ArtifactStorePort
    statement_extraction: StatementExtractionService | None = None


class NormalizeSourceUseCase:
    def __init__(self, dependencies: NormalizationDependencies) -> None:
        self._source_registry = dependencies.source_registry
        self._profile_use_case = dependencies.profile_use_case
        self._facts = dependencies.facts
        self._evidence = dependencies.evidence
        self._evidence_sets = dependencies.evidence_sets
        self._claim_sets = dependencies.claim_sets
        self._artifacts = dependencies.artifacts
        self._statement_extraction = (
            dependencies.statement_extraction
            or StatementExtractionService(self._source_registry)
        )

    def execute(self, request: NormalizeRequest) -> NormalizeResponse:
        raw_dir = path_from_ref(request.raw_capture_ref)
        output_dir = path_from_ref(request.normalized_output_ref)
        capture_context = require_capture_root(raw_dir, expected_source=request.source)
        capture_metadata = capture_context.metadata
        workspace_root = capture_context.workspace_root
        ensure_output_not_within_input_tree(
            raw_dir,
            output_dir,
            input_label="raw source directory",
            output_label="normalization output directory",
        )
        ensure_directory(output_dir)
        profile = self._profile_use_case.create_profile(
            request.source,
            raw_dir,
            capture_metadata=capture_metadata,
            inspect_archives=request.inspect_archives,
        )
        profile = _profile_with_window_hints(profile, request)
        if profile.timezone_issues:
            raise ValueError(
                "source profile contains timezone issues that must be reviewed before normalization"
            )
        if _blocking_profile_scan_issues(profile):
            raise ValueError(
                "source profile contains blocking scan issues that must be resolved before normalization"
            )
        self._profile_use_case.write_profile_artifacts(profile, output_dir)
        adapter = self._source_registry.source_adapter(str(profile.adapter_id))
        if not profile.supported:
            raise ValueError(
                f"source adapter {profile.adapter_id} is not supported for normalization in this phase"
            )
        translation_result = execute_translation(
            adapter=adapter,
            profile=profile,
            raw_dir=raw_dir,
            context=TranslationExecutionContext(
                output_dir=output_dir,
                workspace_root=workspace_root,
                capture_metadata=capture_metadata,
                artifacts=self._artifacts,
                evidence=self._evidence,
                evidence_sets=self._evidence_sets,
                claim_sets=self._claim_sets,
                statement_extraction=self._statement_extraction,
            ),
        )
        result = translation_result.batch
        statement_result = (
            self._statement_extraction.extract_balance_references_from_collection(
                profile,
                translation_result.statement_documents,
            )
        )
        result = SourceTranslationBatch(
            drafts=result.drafts,
            balance_references=(
                *result.balance_references,
                *statement_result.balance_references,
            ),
            balance_reference_issues=(
                *result.balance_reference_issues,
                *statement_result.reference_issues,
            ),
            issues=(*result.issues, *statement_result.issues),
            reviews=(*result.reviews, *statement_result.reviews),
            location_inventory=_with_capture_context(
                result.location_inventory,
                capture_metadata=capture_metadata,
                capture_root_ref=capture_context.capture_root_ref,
            ),
        )
        result = _with_no_supported_activity_issue(profile, adapter, result)
        drafts, facts_outside_window = filter_drafts_by_window(
            result.drafts,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        compiled = compile_activity_drafts_with_feedback(drafts)
        facts = compiled.facts
        emitted_fact_ids = {str(fact.fact_id) for fact in facts}
        enriched_issues = enrich_issue_context_timestamps(
            result.issues + compiled.issues,
            raw_dir=raw_dir,
            inventory=profile.file_inventory,
        )
        issue_records, issues_outside_window = filter_issues_by_window(
            enriched_issues,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        enriched_reviews = enrich_review_context_timestamps(
            result.reviews + compiled.reviews,
            raw_dir=raw_dir,
            inventory=profile.file_inventory,
        )
        review_records, reviews_outside_window = filter_reviews_by_window(
            enriched_reviews,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        balance_targets = latest_balance_targets(facts)
        balance_snapshots, balance_snapshot_issues = derive_balance_snapshots(
            facts,
            balance_targets,
        )
        outputs = NormalizationOutputs(
            facts=facts,
            fact_annotations=annotation_records_from_drafts(
                tuple(
                    draft for draft in drafts if draft.activity_id in emitted_fact_ids
                )
            ),
            location_annotations=location_annotation_records(result.location_inventory),
            balance_snapshots=balance_snapshots,
            balance_references=result.balance_references,
            balance_reference_issues=result.balance_reference_issues,
            issues=(*issue_records, *balance_snapshot_issues),
            reviews=review_records,
            location_inventory=result.location_inventory,
        )
        write_normalization_artifacts(
            output_dir,
            facts=self._facts,
            evidence=self._evidence,
            artifacts=self._artifacts,
            outputs=outputs,
        )
        self._artifacts.write_json(
            output_dir / "normalization_summary.json",
            build_normalization_summary(
                request=request,
                profile=profile,
                outputs=outputs,
                window_stats=NormalizationWindowStats(
                    facts_outside_window=facts_outside_window,
                    issues_outside_window=issues_outside_window,
                    reviews_outside_window=reviews_outside_window,
                ),
                translation_metrics=translation_result.metrics,
                evidence_set_id=translation_result.evidence_set_id,
                evidence_set_ref=translation_result.evidence_set_ref,
                claim_set_id=translation_result.claim_set_id,
                claim_set_ref=translation_result.claim_set_ref,
            ),
        )
        append_capture_status_record(
            artifacts=self._artifacts,
            workspace_root=workspace_root,
            capture_uid=str(capture_metadata.capture_uid),
            status="normalized",
        )
        update_source_inventory_summary(
            artifacts=self._artifacts,
            workspace_root=workspace_root,
            source=str(capture_metadata.source),
            status="normalized",
        )
        return NormalizeResponse(
            normalized_output_ref=request.normalized_output_ref,
            adapter_id=str(profile.adapter_id),
            evidence_set_id=translation_result.evidence_set_id,
            evidence_set_ref=translation_result.evidence_set_ref,
            claim_set_id=translation_result.claim_set_id,
            claim_set_ref=translation_result.claim_set_ref,
            fact_count=len(facts),
            balance_count=len(balance_snapshots),
            issue_count=len(outputs.issues),
            review_count=len(review_records),
            translation_candidate_count=translation_result.metrics.translation_candidate_count,
            translation_selected_count=translation_result.metrics.translation_selected_count,
            translation_superseded_count=translation_result.metrics.translation_superseded_count,
            translation_blocked_count=translation_result.metrics.translation_blocked_count,
            translation_planner_used=translation_result.metrics.translation_planner_used,
        )


def _with_capture_context(
    records: tuple[LocationInventoryRecord, ...],
    *,
    capture_metadata: CaptureMetadata | None,
    capture_root_ref: str,
) -> tuple[LocationInventoryRecord, ...]:
    if capture_metadata is None:
        return records
    return tuple(
        replace(
            record,
            capture_uid=str(capture_metadata.capture_uid),
            capture_label=capture_metadata.capture_label,
            capture_root_ref=capture_root_ref,
        )
        for record in records
    )


def _profile_with_window_hints(
    profile: SourceProfile, request: NormalizeRequest
) -> SourceProfile:
    if request.window_start is None and request.window_end is None:
        return profile
    return replace(
        profile,
        normalization_hints={
            **profile.normalization_hints,
            **(
                {"normalization_window_start": request.window_start}
                if request.window_start is not None
                else {}
            ),
            **(
                {"normalization_window_end": request.window_end}
                if request.window_end is not None
                else {}
            ),
        },
    )


def _blocking_profile_scan_issues(profile: SourceProfile) -> bool:
    return any(
        issue.kind == "mixed_source_capture" or issue.severity == "high"
        for issue in profile.scan_issues
    )


def _with_no_supported_activity_issue(
    profile: SourceProfile,
    adapter: SourceAdapter,
    result: SourceTranslationBatch,
) -> SourceTranslationBatch:
    if AdapterCapability.SOURCE_TRANSLATE not in adapter.manifest.capabilities:
        return result
    if result.drafts or result.issues or result.reviews:
        return result
    if not has_family_for_adapter(profile.file_inventory, str(profile.adapter_id)):
        return result
    return SourceTranslationBatch(
        drafts=result.drafts,
        balance_references=result.balance_references,
        balance_reference_issues=result.balance_reference_issues,
        issues=(
            IssueRecord(
                issue_id=f"{profile.source}:no_supported_activity",
                source=str(profile.source),
                adapter_id=str(profile.adapter_id),
                severity="high",
                kind="no_supported_activity",
                message=(
                    "The source matched a supported translation family but emitted no facts or explicit "
                    "unsupported issues."
                ),
            ),
        ),
        reviews=result.reviews,
        location_inventory=result.location_inventory,
    )
