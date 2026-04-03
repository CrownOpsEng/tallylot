from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.infrastructure.config.loader import (
    _DEFAULT_WORKSPACE_ROOT,
    load_app_config,
)


def test_load_app_config_uses_default_when_project_config_has_no_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "tallylot.toml"
    config_path.write_text("[project]\nname = 'tallylot'\n", encoding="utf-8")
    monkeypatch.delenv("CRYPTO_RECON_WORKSPACE_ROOT", raising=False)

    config = load_app_config(repo_root=tmp_path)

    assert config.repo_root == tmp_path
    assert config.workspace_root == _DEFAULT_WORKSPACE_ROOT


def test_load_app_config_prefers_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "tallylot.toml"
    config_path.write_text("[workspace]\nroot = '~/Documents/ignored'\n", encoding="utf-8")
    override = tmp_path / "external-workspace"
    monkeypatch.setenv("CRYPTO_RECON_WORKSPACE_ROOT", str(override))

    config = load_app_config(repo_root=tmp_path)

    assert config.workspace_root == override
