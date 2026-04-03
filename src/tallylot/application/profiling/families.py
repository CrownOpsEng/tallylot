"""Profile-time file-family classification support."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_adapters import SourceAdapter
from tallylot.ports.source_profiles import (
    FileFamilyClaim,
    FileInventoryEntry,
    family_claim_token,
    parse_family_claim_tokens,
)


@dataclass(frozen=True)
class ProfileFamilyAnalysis:
    inventory: tuple[FileInventoryEntry, ...]
    issues: tuple[IssueRecord, ...]
    supported: bool
    selected_adapter_id: str | None
    recognized_adapter_ids: tuple[str, ...]


def analyze_profile_families(
    *,
    source: str,
    raw_dir: Path,
    inventory: tuple[FileInventoryEntry, ...],
    adapters: tuple[SourceAdapter, ...],
) -> ProfileFamilyAnalysis:
    claims = tuple(
        claim for adapter in adapters for claim in adapter.classify_profile_families(source, raw_dir, inventory)
    )
    inventory_with_families = _apply_family_claims(inventory, claims)
    recognized_adapter_ids = tuple(sorted({str(claim.adapter_id) for claim in claims}))
    if len(recognized_adapter_ids) <= 1:
        return ProfileFamilyAnalysis(
            inventory=inventory_with_families,
            issues=(),
            supported=True,
            selected_adapter_id=recognized_adapter_ids[0] if recognized_adapter_ids else None,
            recognized_adapter_ids=recognized_adapter_ids,
        )
    return ProfileFamilyAnalysis(
        inventory=inventory_with_families,
        issues=(
            IssueRecord(
                issue_id=f"{source}:mixed_source_capture",
                source=source,
                adapter_id=_selected_adapter_id(recognized_adapter_ids, claims),
                severity="high",
                kind="mixed_source_capture",
                message=_mixed_capture_message(claims),
                status="needs_review",
            ),
        ),
        supported=False,
        selected_adapter_id=_selected_adapter_id(recognized_adapter_ids, claims),
        recognized_adapter_ids=recognized_adapter_ids,
    )


def has_family_for_adapter(inventory: tuple[FileInventoryEntry, ...], adapter_id: str) -> bool:
    return any(claim_adapter_id == adapter_id for entry in inventory for claim_adapter_id, _ in family_claims(entry))


def family_claims(entry: FileInventoryEntry) -> tuple[tuple[str, str], ...]:
    return parse_family_claim_tokens(entry.family)


def _apply_family_claims(
    inventory: tuple[FileInventoryEntry, ...],
    claims: tuple[FileFamilyClaim, ...],
) -> tuple[FileInventoryEntry, ...]:
    claims_by_path: dict[str, set[str]] = defaultdict(set)
    for claim in claims:
        claims_by_path[claim.relative_path].add(family_claim_token(str(claim.adapter_id), claim.family_id))
    return tuple(
        replace(entry, family="; ".join(sorted(claims_by_path.get(entry.relative_path, ())))) for entry in inventory
    )


def _selected_adapter_id(recognized_adapter_ids: tuple[str, ...], claims: tuple[FileFamilyClaim, ...]) -> str:
    counts = Counter(str(claim.adapter_id) for claim in claims)
    return sorted(recognized_adapter_ids, key=lambda item: (-counts[item], item))[0]


def _mixed_capture_message(claims: tuple[FileFamilyClaim, ...]) -> str:
    families_by_adapter: dict[str, set[str]] = defaultdict(set)
    counts = Counter(str(claim.adapter_id) for claim in claims)
    for claim in claims:
        families_by_adapter[str(claim.adapter_id)].add(claim.family_id)
    parts = [
        f"{adapter_id} ({counts[adapter_id]} files: {', '.join(sorted(families_by_adapter[adapter_id]))})"
        for adapter_id in sorted(families_by_adapter)
    ]
    return (
        "Raw capture mixes incompatible source families across adapters; split or reroute the capture before "
        f"normalization: {'; '.join(parts)}"
    )
