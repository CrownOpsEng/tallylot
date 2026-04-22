"""Normalization capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tallylot.domain.types import ResourceRef


class NormalizeUpdateMode(StrEnum):
    AUTO = "auto"
    FULL_UPDATE = "full-update"
    REBUILD = "rebuild"


@dataclass(frozen=True)
class NormalizeRequest:
    source: str
    raw_capture_ref: ResourceRef
    normalized_output_ref: ResourceRef
    update_mode: NormalizeUpdateMode = NormalizeUpdateMode.AUTO
    window_start: str | None = None
    window_end: str | None = None
    inspect_archives: bool = True


@dataclass(frozen=True)
class NormalizeResponse:
    normalized_output_ref: ResourceRef
    adapter_id: str
    evidence_set_id: str
    evidence_set_ref: str
    claim_set_id: str
    claim_set_ref: str
    fact_count: int
    balance_count: int
    issue_count: int
    review_count: int
    economic_facts_id: str = ""
    economic_facts_ref: str = ""
    reconciliation_state_ids: tuple[str, ...] = ()
    reconciliation_state_refs: tuple[str, ...] = ()
    checkpoint_ids: tuple[str, ...] = ()
    checkpoint_refs: tuple[str, ...] = ()
    update_mode_requested: str = NormalizeUpdateMode.AUTO.value
    update_mode_effective: str = NormalizeUpdateMode.AUTO.value
    reused_target_product_count: int = 0
    rebuilt_target_product_count: int = 0
    pruned_target_product_count: int = 0
    refreshed_detail_output_count: int = 0
    translation_candidate_count: int = 0
    translation_selected_count: int = 0
    translation_superseded_count: int = 0
    translation_blocked_count: int = 0
    translation_planner_used: bool = False


@dataclass(frozen=True)
class AssembleSourceRequest:
    source: str
    workspace_root_ref: ResourceRef
    assembled_output_ref: ResourceRef | None = None


@dataclass(frozen=True)
class AssembleSourceResponse:
    assembled_output_ref: ResourceRef
    included_capture_count: int
    excluded_capture_count: int
    fact_count: int
    balance_snapshot_count: int
    balance_reference_count: int
    issue_count: int
    review_count: int
