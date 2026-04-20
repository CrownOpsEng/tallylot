"""Normalization summary assembly."""

# pylint: disable=too-many-arguments

from __future__ import annotations

from collections import Counter
from typing import cast

from tallylot.application.normalization.contracts import NormalizeRequest
from tallylot.application.normalization.models import (
    NormalizationTranslationMetrics,
)
from tallylot.domain.issues import NormalizationReviewRecord
from tallylot.domain.types import JsonValue
from tallylot.ports.source_profiles import SourceProfile

from .models import NormalizationOutputs, NormalizationWindowStats


def build_normalization_summary(
    *,
    request: NormalizeRequest,
    profile: SourceProfile,
    outputs: NormalizationOutputs,
    window_stats: NormalizationWindowStats,
    translation_metrics: NormalizationTranslationMetrics,
    evidence_set_id: str,
    evidence_set_ref: str,
) -> JsonValue:  # pylint: disable=too-many-arguments
    return cast(
        JsonValue,
        {
            "source": request.source,
            "adapter_id": str(profile.adapter_id),
            "evidence_set_id": evidence_set_id,
            "evidence_set_ref": evidence_set_ref,
            "fact_count": len(outputs.facts),
            "snapshot_count": len(outputs.balance_snapshots),
            "reference_count": len(outputs.balance_references),
            "reference_issue_count": len(outputs.balance_reference_issues),
            "issue_count": len(outputs.issues),
            "review_count": len(outputs.reviews),
            "review_summary": _review_summary(outputs.reviews),
            "location_count": len(outputs.location_inventory),
            "facts_outside_normalization_window": window_stats.facts_outside_window,
            "issues_outside_normalization_window": window_stats.issues_outside_window,
            "reviews_outside_normalization_window": window_stats.reviews_outside_window,
            "normalization_window_start": request.window_start or "",
            "normalization_window_end": request.window_end or "",
            "translation_candidate_count": translation_metrics.translation_candidate_count,
            "translation_selected_count": translation_metrics.translation_selected_count,
            "translation_superseded_count": translation_metrics.translation_superseded_count,
            "translation_blocked_count": translation_metrics.translation_blocked_count,
            "translation_planner_used": translation_metrics.translation_planner_used,
        },
    )


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
                        if review.scope == scope
                        and review.kind == kind
                        and review.field_name
                    }
                ),
            ),
            "messages": cast(
                list[object],
                sorted(
                    {
                        review.message
                        for review in reviews
                        if review.scope == scope and review.kind == kind
                    }
                ),
            ),
        }
        for (scope, kind), count in sorted(counts.items())
    ]
