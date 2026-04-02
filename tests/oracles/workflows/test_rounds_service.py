from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.workspace import FilesystemWorkspaceRepository
from tools.oracles.contracts import RoundScaffoldRequest
from tools.oracles.rounds import (
    DEFAULT_VERIFICATION_EXPORTS,
    RoundScaffoldingService,
    build_verification_readme,
    create_round_log_entry,
    validate_round_id,
)


def test_validate_round_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_round_id("   ")


def test_validate_round_id_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="single path segment"):
        validate_round_id("../outside")


def test_validate_round_id_rejects_nested_path() -> None:
    with pytest.raises(ValueError, match="single path segment"):
        validate_round_id("rounds/01")


def test_build_verification_readme_lists_default_exports() -> None:
    readme = build_verification_readme("round_01", "baseline_repair", "shakepay")

    for export_name in DEFAULT_VERIFICATION_EXPORTS:
        assert f"- {export_name}" in readme
    assert "round_01" in readme


def test_create_round_log_entry_uses_phase_specific_goal() -> None:
    entry = create_round_log_entry(
        RoundScaffoldRequest(
            workspace_root=Path("/repo"),
            round_id="round_02",
            phase="post_import",
            source="kraken",
            today=date(2026, 3, 22),
        ),
        Path("/repo/working/verification/round_02"),
        date(2026, 3, 22),
    )

    assert entry["goal"] == "Capture fresh verification exports after source import"
    assert entry["exports_captured"] == "working/verification/round_02"


def test_round_scaffolding_service_creates_round_dir_readme_and_log_entry(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    FilesystemWorkspaceRepository().initialize(workspace_root)
    artifacts = FilesystemArtifactStore()

    response = RoundScaffoldingService(artifacts).execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root,
            round_id="round_01",
            phase="baseline_repair",
            source="shakepay",
            today=date(2026, 3, 22),
        )
    )

    round_log_rows = artifacts.read_rows(workspace_root / "outputs/logs/round_log.csv")

    assert response.round_dir.exists()
    assert response.readme_path.exists()
    assert response.seeded is True
    assert round_log_rows == [
        {
            "round_id": "round_01",
            "phase": "baseline_repair",
            "source": "shakepay",
            "date": "2026-03-22",
            "goal": "Capture fresh verification exports after baseline repair",
            "output_change": "",
            "exports_captured": "working/verification/round_01",
            "issues_opened_or_closed": "",
            "gate_result": "pending",
            "next_action": "",
        }
    ]


def test_round_scaffolding_service_is_idempotent_for_existing_round_id(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    FilesystemWorkspaceRepository().initialize(workspace_root)
    artifacts = FilesystemArtifactStore()
    request = RoundScaffoldRequest(
        workspace_root=workspace_root,
        round_id="round_01",
        phase="post_import",
        source="shakepay",
        today=date(2026, 3, 22),
    )

    service = RoundScaffoldingService(artifacts)
    service.execute(request)
    response = service.execute(request)

    rows = artifacts.read_rows(workspace_root / "outputs/logs/round_log.csv")

    assert response.seeded is False
    assert len(rows) == 1


def test_round_scaffolding_service_preserves_existing_round_log_rows(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    FilesystemWorkspaceRepository().initialize(workspace_root)
    artifacts = FilesystemArtifactStore()
    round_log_path = workspace_root / "outputs/logs/round_log.csv"
    artifacts.write_rows(
        round_log_path,
        (
            "round_id",
            "phase",
            "source",
            "date",
            "goal",
            "output_change",
            "exports_captured",
            "issues_opened_or_closed",
            "gate_result",
            "next_action",
        ),
        (
            {
                "round_id": "round_00",
                "phase": "baseline_repair",
                "source": "cointracking",
                "date": "2026-03-21",
                "goal": "Existing goal",
                "output_change": "",
                "exports_captured": "working/verification/round_00",
                "issues_opened_or_closed": "",
                "gate_result": "pass",
                "next_action": "Done",
            },
        ),
    )

    RoundScaffoldingService(artifacts).execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root,
            round_id="round_01",
            phase="post_import",
            source="shakepay",
            today=date(2026, 3, 22),
        )
    )

    rows = artifacts.read_rows(round_log_path)

    assert [row["round_id"] for row in rows] == ["round_00", "round_01"]
    assert rows[0]["goal"] == "Existing goal"
    assert rows[1]["goal"] == "Capture fresh verification exports after source import"


def test_round_scaffolding_service_preserves_existing_readme(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    FilesystemWorkspaceRepository().initialize(workspace_root)
    artifacts = FilesystemArtifactStore()
    readme_path = workspace_root / "working/verification/round_01/README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("custom notes\n", encoding="utf-8")

    RoundScaffoldingService(artifacts).execute(
        RoundScaffoldRequest(
            workspace_root=workspace_root,
            round_id="round_01",
            phase="baseline_repair",
            source="shakepay",
            today=date(2026, 3, 22),
        )
    )

    assert readme_path.read_text(encoding="utf-8") == "custom notes\n"
