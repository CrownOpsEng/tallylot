"""Translation input planning boundary types and shared helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_timestamp, require_utc_datetime
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


class TranslationCoverageMode(StrEnum):
    BOUNDED = "bounded"
    UNBOUNDED_START = "unbounded_start"
    UNBOUNDED_END = "unbounded_end"
    UNKNOWN = "unknown"


class TranslationSelectionMode(StrEnum):
    APPENDABLE_RANGE = "appendable_range"
    REPLACEABLE_RANGE = "replaceable_range"
    EXCLUSIVE_SNAPSHOT = "exclusive_snapshot"


class TranslationFreshnessKind(StrEnum):
    EXPORT_TIMESTAMP = "export_timestamp"
    CAPTURE_COMPLETED_AT = "capture_completed_at"
    ADAPTER_RANK = "adapter_rank"
    UNKNOWN = "unknown"


TranslationPlanDecisionStatus = Literal[
    "selected",
    "superseded_identical",
    "superseded_replaced",
    "blocked_partial_overlap",
    "blocked_ambiguous_freshness",
    "blocked_unknown_coverage",
    "blocked_incomparable_candidates",
    "blocked_invalid_candidate",
]


@dataclass(frozen=True)
class TranslationCoverageWindow:
    start_at: datetime | None
    start_precision: TemporalPrecision | None
    end_at: datetime | None
    end_precision: TemporalPrecision | None
    mode: TranslationCoverageMode


@dataclass(frozen=True)
class TranslationFreshness:
    kind: TranslationFreshnessKind
    timestamp: datetime | None
    rank: int | None


@dataclass(frozen=True)
class TranslationInputCandidate:
    candidate_id: str
    selection_group: str
    family_id: str
    member_relative_paths: tuple[str, ...]
    selection_mode: TranslationSelectionMode
    coverage: TranslationCoverageWindow
    freshness: TranslationFreshness
    content_fingerprint: str
    comparison_key: str
    description: str
    comparable: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranslationPlanDecision:
    candidate_id: str
    status: TranslationPlanDecisionStatus
    reason: str
    replaces_candidate_ids: tuple[str, ...] = ()
    conflicts_with_candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranslationInputPlan:
    selected_candidate_ids: tuple[str, ...]
    decisions: tuple[TranslationPlanDecision, ...]
    blocked: bool


@runtime_checkable
class TranslationInputPlanningAdapter(Protocol):
    def describe_translation_inputs(
        self, profile: SourceProfile, raw_dir: Path
    ) -> tuple[TranslationInputCandidate, ...]: ...

    def translate_selected_inputs(
        self,
        profile: SourceProfile,
        raw_dir: Path,
        plan: TranslationInputPlan,
    ) -> SourceTranslationBatch: ...


def translation_input_coverage_from_inventory_entry(
    entry: FileInventoryEntry,
) -> TranslationCoverageWindow:
    start_at, end_at, precision = _coverage_bounds_from_inventory_entry(entry)
    if start_at is None and end_at is None:
        return TranslationCoverageWindow(
            start_at=None,
            start_precision=None,
            end_at=None,
            end_precision=None,
            mode=TranslationCoverageMode.UNKNOWN,
        )
    if start_at is None:
        return TranslationCoverageWindow(
            start_at=None,
            start_precision=None,
            end_at=end_at,
            end_precision=precision,
            mode=TranslationCoverageMode.UNBOUNDED_START,
        )
    if end_at is None:
        return TranslationCoverageWindow(
            start_at=start_at,
            start_precision=precision,
            end_at=None,
            end_precision=None,
            mode=TranslationCoverageMode.UNBOUNDED_END,
        )
    return TranslationCoverageWindow(
        start_at=start_at,
        start_precision=precision,
        end_at=end_at,
        end_precision=precision,
        mode=TranslationCoverageMode.BOUNDED,
    )


def translation_input_content_fingerprint(
    *,
    member_sha256s: tuple[str, ...],
    family_id: str,
    selection_group: str,
    selection_mode: TranslationSelectionMode,
) -> str:
    payload = {
        "family_id": family_id,
        "member_sha256s": sorted(member_sha256s),
        "selection_group": selection_group,
        "selection_mode": selection_mode.value,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _coverage_bounds_from_inventory_entry(
    entry: FileInventoryEntry,
) -> tuple[datetime | None, datetime | None, TemporalPrecision | None]:
    precision = (
        TemporalPrecision.DATE
        if entry.timestamp_resolution == "date_only"
        else TemporalPrecision.TIMESTAMP
        if entry.min_timestamp or entry.max_timestamp
        else None
    )
    start_at = _parse_inventory_timestamp(entry.min_timestamp)
    end_at = _parse_inventory_timestamp(entry.max_timestamp)
    return start_at, end_at, precision


def _parse_inventory_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        return require_utc_datetime(parse_timestamp(text), label="inventory timestamp")
    except ValueError:
        return None
