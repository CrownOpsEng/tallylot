"""Normalization summary assembly."""

from __future__ import annotations

from collections import Counter
from typing import cast

from crypto_reconciliation.application.models.source import NormalizeRequest
from crypto_reconciliation.domain.models import NormalizationReviewRecord, SourceProfile
from crypto_reconciliation.domain.types import JsonValue

from .models import NormalizationOutputs, NormalizationWindowStats


def build_normalization_summary(
    *,
    request: NormalizeRequest,
    profile: SourceProfile,
    outputs: NormalizationOutputs,
    window_stats: NormalizationWindowStats,
) -> JsonValue:
    return cast(
        JsonValue,
        {
            "source": request.source,
            "adapter_id": str(profile.adapter_id),
            "transaction_count": len(outputs.transactions),
            "balance_count": len(outputs.derived_balances),
            "balance_evidence_count": len(outputs.balance_evidence),
            "issue_count": len(outputs.issues),
            "review_count": len(outputs.reviews),
            "review_summary": _review_summary(outputs.reviews),
            "wallet_count": len(outputs.wallet_inventory),
            "transactions_outside_normalization_window": window_stats.transactions_outside_window,
            "issues_outside_normalization_window": window_stats.issues_outside_window,
            "normalization_window_start": request.window_start or "",
            "normalization_window_end": request.window_end or "",
        },
    )


def _review_summary(reviews: tuple[NormalizationReviewRecord, ...]) -> list[dict[str, object]]:
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
