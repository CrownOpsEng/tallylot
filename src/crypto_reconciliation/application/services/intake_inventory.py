"""Inventory-backed source routing for intake."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.services.intake_file_facts import IntakeFileFacts
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


@dataclass(frozen=True)
class InventoryRouteDecision:
    source_folder: str
    inventory_match_status: str
    review_required: str = "no"
    review_codes: str = ""
    review_reason: str = ""


def resolve_inventory_route(
    *,
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    source_folder: str,
    facts: IntakeFileFacts,
) -> InventoryRouteDecision:
    if source_folder not in {"evm_explorer", "evm_wallet"}:
        return InventoryRouteDecision(
            source_folder=source_folder,
            inventory_match_status="unmatched",
        )

    evidence_rows = _read_rows(artifacts, workspace_root / "analysis" / "inventory" / "wallet_inventory_evidence.csv")
    source_rows = _read_rows(artifacts, workspace_root / "analysis" / "issues" / "source_inventory.csv")
    if not evidence_rows or not source_rows:
        return InventoryRouteDecision(
            source_folder=source_folder,
            inventory_match_status="unmatched",
        )

    identifiers = {token.split(":", 1)[1] for token in facts.scope_tokens if token.startswith("evm:")}
    if not identifiers:
        return InventoryRouteDecision(
            source_folder=source_folder,
            inventory_match_status="unmatched",
        )

    candidate_rows = [
        row for row in evidence_rows if (row.get("normalized_identifier") or "").strip().lower() in identifiers
    ]
    distinct_sources = sorted(
        {(row.get("source") or "").strip() for row in candidate_rows if (row.get("source") or "").strip()}
    )
    if len(distinct_sources) == 1 and any(
        (row.get("source") or "").strip() == distinct_sources[0] for row in source_rows
    ):
        return InventoryRouteDecision(
            source_folder=distinct_sources[0],
            inventory_match_status="inventory_source_match",
        )
    if len(distinct_sources) > 1:
        return InventoryRouteDecision(
            source_folder=source_folder,
            inventory_match_status="inventory_source_ambiguous",
            review_required="yes",
            review_codes="inventory_source_ambiguous",
            review_reason=f"Wallet evidence matched multiple existing sources: {', '.join(distinct_sources)}",
        )
    return InventoryRouteDecision(
        source_folder=source_folder,
        inventory_match_status="unmatched",
    )


def _read_rows(artifacts: ArtifactStorePort, path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return artifacts.read_rows(path)
