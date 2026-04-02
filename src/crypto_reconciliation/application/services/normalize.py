"""Normalization service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import cast

from crypto_reconciliation.application.dtos import NormalizeRequest, NormalizeResponse
from crypto_reconciliation.application.services.common import ensure_directory
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.scan import ensure_output_not_within_input_tree
from crypto_reconciliation.domain.models import NormalizationReviewRecord
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.adapters import OutputAdapterRegistryPort, SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.storage import StoragePort


@dataclass(frozen=True)
class NormalizationDependencies:
    source_registry: SourceAdapterRegistryPort
    output_registry: OutputAdapterRegistryPort
    profile_service: ProfileService
    storage: StoragePort
    artifacts: ArtifactStorePort


class NormalizationService:
    def __init__(self, dependencies: NormalizationDependencies) -> None:
        self._source_registry = dependencies.source_registry
        self._output_registry = dependencies.output_registry
        self._profile_service = dependencies.profile_service
        self._storage = dependencies.storage
        self._artifacts = dependencies.artifacts

    def execute(self, request: NormalizeRequest) -> NormalizeResponse:
        ensure_output_not_within_input_tree(
            request.raw_dir,
            request.output_dir,
            input_label="raw source directory",
            output_label="normalization output directory",
        )
        ensure_directory(request.output_dir)
        profile = self._profile_service.create_profile(
            request.source,
            request.raw_dir,
            inspect_archives=request.inspect_archives,
        )
        if profile.timezone_issues:
            raise ValueError("source profile contains timezone issues that must be reviewed before normalization")
        self._profile_service.write_profile_artifacts(profile, request.output_dir)
        adapter = self._source_registry.source_adapter(str(profile.adapter_id))
        if not profile.supported:
            raise ValueError(f"source adapter {profile.adapter_id} is not supported for normalization in this phase")
        result = adapter.normalize(profile, request.raw_dir)
        self._storage.write_canonical_events(
            request.output_dir / "canonical_events.csv",
            result.canonical_events,
        )
        self._storage.write_canonical_balances(
            request.output_dir / "canonical_balances.csv",
            result.canonical_balances,
        )
        self._storage.write_issue_records(request.output_dir / "exceptions.csv", result.issues)
        self._storage.write_review_records(
            request.output_dir / "normalization_reviews.csv",
            result.reviews,
        )
        self._artifacts.write_rows(
            request.output_dir / "wallet_inventory.csv",
            (
                "wallet_id",
                "source",
                "account",
                "wallet",
                "evidence_path",
                "identifier_kind",
                "identifier_value",
                "notes",
            ),
            (record.to_row() for record in result.wallet_inventory),
        )
        output_adapter = self._output_registry.output_adapter("cointracking_csv")
        output_adapter.render(result.canonical_events, request.output_dir / "cointracking_candidate.csv")
        self._artifacts.write_json(
            request.output_dir / "normalization_summary.json",
            cast(
                JsonValue,
                {
                    "source": request.source,
                    "adapter_id": str(profile.adapter_id),
                    "event_count": len(result.canonical_events),
                    "balance_count": len(result.canonical_balances),
                    "issue_count": len(result.issues),
                    "review_count": len(result.reviews),
                    "review_summary": self._review_summary(result.reviews),
                    "wallet_count": len(result.wallet_inventory),
                },
            ),
        )
        return NormalizeResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            event_count=len(result.canonical_events),
            balance_count=len(result.canonical_balances),
            issue_count=len(result.issues),
            review_count=len(result.reviews),
        )

    @staticmethod
    def _review_summary(
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> list[dict[str, object]]:
        counts = Counter((review.scope, review.kind) for review in reviews)
        return [
            {
                "scope": scope,
                "kind": kind,
                "count": count,
                "field_names": cast(
                    list[object],
                    sorted(
                        {
                            review.field_name
                            for review in reviews
                            if review.scope == scope and review.kind == kind and review.field_name
                        }
                    ),
                ),
                "messages": cast(
                    list[object],
                    sorted({review.message for review in reviews if review.scope == scope and review.kind == kind}),
                ),
            }
            for (scope, kind), count in sorted(counts.items())
        ]
