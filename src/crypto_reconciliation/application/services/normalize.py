"""Normalization service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import cast

from crypto_reconciliation.application.models.source import NormalizeRequest, NormalizeResponse
from crypto_reconciliation.application.services.balance_snapshots import derive_balance_snapshots
from crypto_reconciliation.application.services.common import ensure_directory
from crypto_reconciliation.application.services.issue_context import enrich_issue_context_timestamps
from crypto_reconciliation.application.services.normalization_window import (
    filter_issues_by_window,
    filter_transactions_by_window,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.application.services.scan import ensure_output_not_within_input_tree
from crypto_reconciliation.domain.models import NormalizationReviewRecord, SourceProfile
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.adapters import SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.storage import StoragePort


@dataclass(frozen=True)
class NormalizationDependencies:
    source_registry: SourceAdapterRegistryPort
    profile_service: ProfileService
    storage: StoragePort
    artifacts: ArtifactStorePort


class NormalizationService:
    def __init__(self, dependencies: NormalizationDependencies) -> None:
        self._source_registry = dependencies.source_registry
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
        profile = _profile_with_window_hints(profile, request)
        if profile.timezone_issues:
            raise ValueError("source profile contains timezone issues that must be reviewed before normalization")
        self._profile_service.write_profile_artifacts(profile, request.output_dir)
        adapter = self._source_registry.source_adapter(str(profile.adapter_id))
        if not profile.supported:
            raise ValueError(f"source adapter {profile.adapter_id} is not supported for normalization in this phase")
        result = adapter.normalize(profile, request.raw_dir)
        transactions, transactions_outside_window = filter_transactions_by_window(
            result.transactions,
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
        derived_balances = derive_balance_snapshots(transactions)
        self._storage.write_transactions(
            request.output_dir / "transactions.csv",
            transactions,
        )
        self._storage.write_balances(
            request.output_dir / "balances.csv",
            derived_balances,
        )
        self._storage.write_issue_records(request.output_dir / "exceptions.csv", issue_records)
        self._storage.write_review_records(
            request.output_dir / "normalization_reviews.csv",
            result.reviews,
        )
        self._artifacts.write_rows(
            request.output_dir / "wallet_inventory.csv",
            (
                "source",
                "capture_path",
                "wallet_id",
                "identifier_kind",
                "normalized_identifier",
                "display_identifier",
                "network_scope",
                "controller",
                "account_label",
                "evidence_kind",
                "evidence_path",
                "confidence",
                "account",
                "wallet",
                "identifier_value",
                "notes",
            ),
            (record.to_row() for record in result.wallet_inventory),
        )
        self._artifacts.write_json(
            request.output_dir / "normalization_summary.json",
            cast(
                JsonValue,
                {
                    "source": request.source,
                    "adapter_id": str(profile.adapter_id),
                    "transaction_count": len(transactions),
                    "balance_count": len(derived_balances),
                    "balance_evidence_count": len(result.balance_evidence),
                    "issue_count": len(issue_records),
                    "review_count": len(result.reviews),
                    "review_summary": self._review_summary(result.reviews),
                    "wallet_count": len(result.wallet_inventory),
                    "transactions_outside_normalization_window": transactions_outside_window,
                    "issues_outside_normalization_window": issues_outside_window,
                    "normalization_window_start": request.window_start or "",
                    "normalization_window_end": request.window_end or "",
                },
            ),
        )
        return NormalizeResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            transaction_count=len(transactions),
            balance_count=len(derived_balances),
            issue_count=len(issue_records),
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
