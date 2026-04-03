"""Application config loading."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_WORKSPACE_ROOT = Path(
    "~/crypto-reconciliation-workspace",
).expanduser()
CONFIG_FILE_NAME = "crypto-reconciliation.toml"


class WorkspaceConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: Path | None = None


class ProjectConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace: WorkspaceConfigModel = Field(default_factory=WorkspaceConfigModel)


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo_root: Path
    workspace_root: Path


def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / CONFIG_FILE_NAME).exists():
            return candidate
    return start


def load_app_config(*, repo_root: Path | None = None) -> AppConfig:
    base_root = _find_repo_root(repo_root or Path.cwd())
    config_path = base_root / CONFIG_FILE_NAME

    parsed = ProjectConfigModel()
    if config_path.exists():
        parsed = ProjectConfigModel.model_validate(
            tomllib.loads(config_path.read_text(encoding="utf-8")),
        )

    env_workspace_root = os.getenv("CRYPTO_RECON_WORKSPACE_ROOT")
    if env_workspace_root:
        workspace_root = Path(env_workspace_root).expanduser()
    elif parsed.workspace.root is not None:
        workspace_root = parsed.workspace.root.expanduser()
    else:
        workspace_root = DEFAULT_WORKSPACE_ROOT

    return AppConfig(repo_root=base_root, workspace_root=workspace_root)
