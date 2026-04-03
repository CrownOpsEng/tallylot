from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def default_project_environment() -> str:
    return str(Path.home() / ".venvs" / "tallylot-py312")


def repo_uv_environment(existing: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if existing is None else existing)
    environment.setdefault("UV_PROJECT_ENVIRONMENT", default_project_environment())
    return environment
