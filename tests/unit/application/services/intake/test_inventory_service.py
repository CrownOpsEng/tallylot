from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.intake.file_facts import IntakeFileFacts
from crypto_reconciliation.application.services.intake.inventory import resolve_inventory_route
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository


def test_resolve_inventory_route_skips_non_wallet_sources(tmp_path: Path) -> None:
    decision = resolve_inventory_route(
        artifacts=FilesystemArtifactStore(),
        workspace_root=tmp_path,
        source_folder="coinbase",
        facts=IntakeFileFacts(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
    )

    assert decision.source_folder == "coinbase"
    assert decision.inventory_match_status == "unmatched"


def test_resolve_inventory_route_requires_inventory_artifacts(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    FilesystemWorkspaceRepository().initialize(workspace_root)

    decision = resolve_inventory_route(
        artifacts=FilesystemArtifactStore(),
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=IntakeFileFacts(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
    )

    assert decision.inventory_match_status == "unmatched"


def test_resolve_inventory_route_requires_evm_identifiers(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "evm_wallet",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
        ),
        source_rows=({"source": "evm_wallet"},),
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=IntakeFileFacts(scope_tokens=("label:account-main",)),
    )

    assert decision.inventory_match_status == "unmatched"


def test_resolve_inventory_route_uses_single_matching_existing_source(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "evm_explorer",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
        ),
        source_rows=({"source": "evm_explorer"},),
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=IntakeFileFacts(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
    )

    assert decision.source_folder == "evm_explorer"
    assert decision.inventory_match_status == "inventory_source_match"


def test_resolve_inventory_route_marks_ambiguous_wallet_matches_for_review(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "evm_explorer",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
            {
                "source": "evm_wallet",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
        ),
        source_rows=(
            {"source": "evm_explorer"},
            {"source": "evm_wallet"},
        ),
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=IntakeFileFacts(scope_tokens=("evm:0x1111111111111111111111111111111111111111",)),
    )

    assert decision.source_folder == "wallet-export-unassigned"
    assert decision.inventory_match_status == "inventory_source_ambiguous"
    assert decision.review_required == "yes"
    assert decision.review_codes == "inventory_source_ambiguous"
    assert "evm_explorer" in decision.review_reason
    assert "evm_wallet" in decision.review_reason


def test_resolve_inventory_route_uses_generic_scope_folder_for_unknown_wallet(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_explorer",
        facts=IntakeFileFacts(
            scope_tokens=("evm:0x1234567890abcdef1234567890abcdef12345678",),
            network_hints=("polygon",),
        ),
    )

    assert decision.source_folder == "polygon-wallet-0x12345678"
    assert decision.inventory_match_status == "generic_scope_routing"


def test_resolve_inventory_route_uses_generic_scope_folder_when_inventory_rows_do_not_match(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)
    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "eth-primary",
                "normalized_identifier": "0x9999999999999999999999999999999999999999",
            },
        ),
        source_rows=({"source": "eth-primary"},),
    )

    decision = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_explorer",
        facts=IntakeFileFacts(
            scope_tokens=("evm:0x1234567890abcdef1234567890abcdef12345678",),
            network_hints=("ethereum",),
        ),
    )

    assert decision.source_folder == "ethereum-wallet-0x12345678"
    assert decision.inventory_match_status == "generic_scope_routing"


def test_resolve_inventory_route_reloads_inventory_after_file_changes(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    FilesystemWorkspaceRepository().initialize(workspace_root)
    facts = IntakeFileFacts(scope_tokens=("evm:0x1111111111111111111111111111111111111111",))

    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "source-a",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
        ),
        source_rows=({"source": "source-a"},),
    )
    first = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=facts,
    )

    _write_inventory_rows(
        artifacts,
        workspace_root,
        evidence_rows=(
            {
                "source": "source-b",
                "normalized_identifier": "0x1111111111111111111111111111111111111111",
            },
        ),
        source_rows=({"source": "source-b"},),
    )
    second = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=workspace_root,
        source_folder="evm_wallet",
        facts=facts,
    )

    assert first.source_folder == "source-a"
    assert first.inventory_match_status == "inventory_source_match"
    assert second.source_folder == "source-b"
    assert second.inventory_match_status == "inventory_source_match"


def _write_inventory_rows(
    artifacts: FilesystemArtifactStore,
    workspace_root: Path,
    *,
    evidence_rows: tuple[dict[str, str], ...],
    source_rows: tuple[dict[str, str], ...],
) -> None:
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "wallet_inventory_evidence.csv",
        ("source", "normalized_identifier"),
        evidence_rows,
    )
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        ("source",),
        source_rows,
    )
