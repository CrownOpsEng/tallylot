from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast

import pytest
from typer.testing import CliRunner

from crypto_reconciliation.interfaces.cli import app
from crypto_reconciliation.interfaces.cli import rounds as cli_rounds
from crypto_reconciliation.interfaces.cli import workspace as cli_workspace

runner = CliRunner()


class HasWorkspaceRoot(Protocol):
    workspace_root: Path


def test_cli_registers_expected_command_groups() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    commands = (
        "workspace",
        "baseline",
        "source",
        "wallet",
        "output",
        "verification",
        "batch",
        "round",
        "supporting",
    )
    for command in commands:
        assert command in result.stdout


def test_workspace_init_uses_configured_root_when_option_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_root = tmp_path / "configured-workspace"
    seen: dict[str, Path] = {}

    class StubWorkspaceInitializationService:
        def __init__(self, repository: object) -> None:
            del repository

        def execute(self, request: object) -> object:
            workspace_root = cast(HasWorkspaceRoot, request).workspace_root
            seen["workspace_root"] = workspace_root
            return SimpleNamespace(workspace_root=workspace_root, created_paths=("a", "b"))

    monkeypatch.setattr(cli_workspace, "configured_workspace_root", lambda: configured_root)
    monkeypatch.setattr(cli_workspace, "WorkspaceInitializationService", StubWorkspaceInitializationService)

    result = runner.invoke(app, ["workspace", "init"])

    assert result.exit_code == 0
    assert seen["workspace_root"] == configured_root


def test_round_scaffold_uses_configured_root_when_option_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_root = tmp_path / "configured-workspace"
    seen: dict[str, Path] = {}

    class StubRoundScaffoldingService:
        def __init__(self, artifacts: object) -> None:
            del artifacts

        def execute(self, request: object) -> object:
            workspace_root = cast(HasWorkspaceRoot, request).workspace_root
            seen["workspace_root"] = workspace_root
            return SimpleNamespace(workspace_root=workspace_root, round_dir=workspace_root / "rounds/example")

    monkeypatch.setattr(cli_rounds, "configured_workspace_root", lambda: configured_root)
    monkeypatch.setattr(cli_rounds, "RoundScaffoldingService", StubRoundScaffoldingService)

    result = runner.invoke(
        app,
        ["round", "scaffold", "--round-id", "post_import_fixture_01", "--phase", "post_import", "--source", "fixture"],
    )

    assert result.exit_code == 0
    assert seen["workspace_root"] == configured_root
