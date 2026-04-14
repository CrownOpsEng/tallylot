from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def default_project_environment() -> str:
    return str(Path.home() / ".venvs" / "tallylot-py312")


def repo_uv_environment(existing: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if existing is None else existing)
    project_environment = Path(
        environment.get("VIRTUAL_ENV")
        or environment.get("UV_PROJECT_ENVIRONMENT")
        or default_project_environment()
    )
    environment.setdefault("UV_PROJECT_ENVIRONMENT", str(project_environment))
    environment.setdefault("VIRTUAL_ENV", str(project_environment))
    project_bin = str(project_environment / "bin")
    current_path = environment.get("PATH", "")
    path_entries = current_path.split(os.pathsep) if current_path else ()
    if project_bin not in path_entries:
        environment["PATH"] = (
            f"{project_bin}{os.pathsep}{current_path}" if current_path else project_bin
        )
    return environment
