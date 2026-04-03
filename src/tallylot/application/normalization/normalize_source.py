"""Normalization workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace

from tallylot.application.normalization.contracts import NormalizeRequest, NormalizeResponse
from tallylot.application.normalization.issue_context import enrich_issue_context_timestamps
from tallylot.application.profiling.build_profile import BuildProfileUseCase
from tallylot.infrastructure.filesystem import ensure_directory, ensure_output_not_within_input_tree
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort
from tallylot.ports.facts import FactRepositoryPort
from tallylot.ports.source_adapters import SourceAdapterRegistryPort
from tallylot.ports.source_profiles import SourceProfile

from .artifacts import write_normalization_artifacts
from .balances import derive_balance_snapshots
from .models import NormalizationOutputs, NormalizationWindowStats
from .summary import build_normalization_summary
from .window import filter_facts_by_window, filter_issues_by_window


@dataclass(frozen=True)
class NormalizationDependencies:
    source_registry: SourceAdapterRegistryPort
    profile_use_case: BuildProfileUseCase
    facts: FactRepositoryPort
    evidence: EvidenceRepositoryPort
    artifacts: ArtifactStorePort


class NormalizeSourceUseCase:
    def __init__(self, dependencies: NormalizationDependencies) -> None:
        self._source_registry = dependencies.source_registry
        self._profile_use_case = dependencies.profile_use_case
        self._facts = dependencies.facts
        self._evidence = dependencies.evidence
        self._artifacts = dependencies.artifacts

    def execute(self, request: NormalizeRequest) -> NormalizeResponse:
        ensure_output_not_within_input_tree(
            request.raw_dir,
            request.output_dir,
            input_label="raw source directory",
            output_label="normalization output directory",
        )
        ensure_directory(request.output_dir)
        profile = self._profile_use_case.create_profile(
            request.source,
            request.raw_dir,
            inspect_archives=request.inspect_archives,
        )
        profile = _profile_with_window_hints(profile, request)
        if profile.timezone_issues:
            raise ValueError("source profile contains timezone issues that must be reviewed before normalization")
        self._profile_use_case.write_profile_artifacts(profile, request.output_dir)
        adapter = self._source_registry.source_adapter(str(profile.adapter_id))
        if not profile.supported:
            raise ValueError(f"source adapter {profile.adapter_id} is not supported for normalization in this phase")
        result = adapter.translate(profile, request.raw_dir)
        facts, facts_outside_window = filter_facts_by_window(
            result.facts,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        enriched_issues = enrich_issue_context_timestamps(
            result.issues,
            raw_dir=request.raw_dir,
            inventory=profile.file_inventory,
        )
        issue_records, issues_outside_window = filter_issues_by_window(
            enriched_issues,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        derived_balances = derive_balance_snapshots(facts)
        outputs = NormalizationOutputs(
            facts=facts,
            derived_balances=derived_balances,
            balance_evidence=result.balance_evidence,
            issues=issue_records,
            reviews=result.reviews,
            wallet_inventory=result.wallet_inventory,
        )
        write_normalization_artifacts(
            request.output_dir,
            facts=self._facts,
            evidence=self._evidence,
            outputs=outputs,
        )
        self._artifacts.write_json(
            request.output_dir / "normalization_summary.json",
            build_normalization_summary(
                request=request,
                profile=profile,
                outputs=outputs,
                window_stats=NormalizationWindowStats(
                    facts_outside_window=facts_outside_window,
                    issues_outside_window=issues_outside_window,
                ),
            ),
        )
        return NormalizeResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            fact_count=len(facts),
            balance_count=len(derived_balances),
            issue_count=len(issue_records),
            review_count=len(result.reviews),
        )


def _profile_with_window_hints(profile: SourceProfile, request: NormalizeRequest) -> SourceProfile:
    if request.window_start is None and request.window_end is None:
        return profile
    return replace(
        profile,
        normalization_hints={
            **profile.normalization_hints,
            **({"normalization_window_start": request.window_start} if request.window_start is not None else {}),
            **({"normalization_window_end": request.window_end} if request.window_end is not None else {}),
        },
    )
