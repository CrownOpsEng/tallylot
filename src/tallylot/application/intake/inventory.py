"""Inventory-backed source routing for intake."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.ports.artifacts import ArtifactStorePort

from .file_facts import IntakeFileFacts


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
    identifiers = _inventory_identifiers(facts.scope_tokens)
    if not identifiers:
        return InventoryRouteDecision(
            source_folder=source_folder,
            inventory_match_status="unmatched",
        )

    evidence_rows = _read_rows(artifacts, workspace_root / "analysis" / "inventory" / "location_inventory_evidence.csv")
    source_rows = _read_rows(artifacts, workspace_root / "analysis" / "issues" / "source_inventory.csv")
    inventory_match = _inventory_match_decision(
        identifiers=identifiers,
        evidence_rows=evidence_rows,
        source_rows=source_rows,
    )
    if inventory_match is not None:
        return inventory_match

    generic_source_folder = _generic_wallet_source_folder(identifiers, facts.network_hints)
    if generic_source_folder:
        return InventoryRouteDecision(
            source_folder=generic_source_folder,
            inventory_match_status="generic_scope_routing",
        )
    return InventoryRouteDecision(
        source_folder=source_folder,
        inventory_match_status="unmatched",
    )


def _inventory_match_decision(
    *,
    identifiers: set[str],
    evidence_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
) -> InventoryRouteDecision | None:
    if not evidence_rows or not source_rows:
        return None

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
            source_folder="wallet-export-unassigned",
            inventory_match_status="inventory_source_ambiguous",
            review_required="yes",
            review_codes="inventory_source_ambiguous",
            review_reason=f"Wallet evidence matched multiple existing sources: {', '.join(distinct_sources)}",
        )
    return None


def _read_rows(artifacts: ArtifactStorePort, path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return artifacts.read_rows(path)


def _inventory_identifiers(scope_tokens: tuple[str, ...]) -> set[str]:
    return {
        value
        for token in scope_tokens
        if ":" in token
        for kind, value in (token.split(":", 1),)
        if kind != "label" and value
    }


def _generic_wallet_source_folder(identifiers: set[str], network_hints: tuple[str, ...]) -> str:
    if not identifiers or not network_hints:
        return ""
    identifier = sorted(identifiers)[0]
    network = network_hints[0].strip().lower()
    if not network:
        return ""
    return f"{network}-wallet-{identifier[:10]}"
