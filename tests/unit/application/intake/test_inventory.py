from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.intake.inventory import resolve_inventory_route
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts


def test_resolve_inventory_route_returns_unmatched_without_identifiers(tmp_path: Path) -> None:
    decision = resolve_inventory_route(
        artifacts=FilesystemArtifactStore(),
        workspace_root=tmp_path,
        source_folder="wallet-candidate",
        facts=IntakeFileFacts(scope_tokens=("label:metamask",)),
    )

    assert decision.source_folder == "wallet-candidate"
    assert decision.inventory_match_status == "unmatched"


def test_resolve_inventory_route_uses_unique_inventory_source_match(tmp_path: Path) -> None:
    artifacts = FilesystemArtifactStore()
    workspace_root = tmp_path
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=[{"normalized_identifier": "0xabc", "source": "eth-wallet-main"}],
        source_rows=[{"source": "eth-wallet-main"}],
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="wallet-candidate",
        facts=IntakeFileFacts(scope_tokens=("evm_address:0xabc",)),
    )

    assert decision.source_folder == "eth-wallet-main"
    assert decision.inventory_match_status == "inventory_source_match"
    assert decision.review_required == "no"


def test_resolve_inventory_route_flags_ambiguous_inventory_matches(tmp_path: Path) -> None:
    artifacts = FilesystemArtifactStore()
    workspace_root = tmp_path
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=[
            {"normalized_identifier": "0xabc", "source": "eth-wallet-main"},
            {"normalized_identifier": "0xabc", "source": "eth-wallet-ledger"},
        ],
        source_rows=[
            {"source": "eth-wallet-main"},
            {"source": "eth-wallet-ledger"},
        ],
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="wallet-candidate",
        facts=IntakeFileFacts(scope_tokens=("evm_address:0xabc",)),
    )

    assert decision.source_folder == "wallet-export-unassigned"
    assert decision.inventory_match_status == "inventory_source_ambiguous"
    assert decision.review_required == "yes"
    assert decision.review_codes == "inventory_source_ambiguous"
    assert "eth-wallet-ledger" in decision.review_reason


def test_resolve_inventory_route_falls_back_to_generic_network_scope(tmp_path: Path) -> None:
    decision = resolve_inventory_route(
        artifacts=FilesystemArtifactStore(),
        workspace_root=tmp_path,
        source_folder="wallet-candidate",
        facts=IntakeFileFacts(
            scope_tokens=("evm_address:0xabcdef1234567890",),
            network_hints=("Ethereum",),
        ),
    )

    assert decision.source_folder == "ethereum-wallet-0xabcdef12"
    assert decision.inventory_match_status == "generic_scope_routing"


def _write_inventory_rows(
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
    *,
    evidence_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
) -> None:
    inventory_dir = workspace_root / "analysis" / "inventory"
    issues_dir = workspace_root / "analysis" / "issues"
    inventory_dir.mkdir(parents=True, exist_ok=True)
    issues_dir.mkdir(parents=True, exist_ok=True)
    artifacts.write_rows(
        inventory_dir / "wallet_inventory_evidence.csv",
        ("normalized_identifier", "source"),
        evidence_rows,
    )
    artifacts.write_rows(
        issues_dir / "source_inventory.csv",
        ("source",),
        source_rows,
    )
