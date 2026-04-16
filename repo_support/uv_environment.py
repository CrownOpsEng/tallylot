from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from repo_support.paths import repo_root


def default_project_environment() -> str:
    return str(Path.home() / ".venvs" / "tallylot-py312")


def _is_repo_local_project_environment(path: Path) -> bool:
    return path.expanduser().resolve() == (repo_root() / ".venv").resolve()


def repo_uv_environment(existing: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if existing is None else existing)
    explicit_project_environment = environment.get("UV_PROJECT_ENVIRONMENT")
    active_project_environment = environment.get("VIRTUAL_ENV")
    if explicit_project_environment:
        project_environment = Path(explicit_project_environment)
    elif active_project_environment and not _is_repo_local_project_environment(
        Path(active_project_environment)
    ):
        project_environment = Path(active_project_environment)
    else:
        project_environment = Path(default_project_environment())
    environment["UV_PROJECT_ENVIRONMENT"] = str(project_environment)
    environment["VIRTUAL_ENV"] = str(project_environment)
    project_bin = str(project_environment / "bin")
    current_path = environment.get("PATH", "")
    path_entries = current_path.split(os.pathsep) if current_path else ()
    if project_bin not in path_entries:
        environment["PATH"] = (
            f"{project_bin}{os.pathsep}{current_path}" if current_path else project_bin
        )
    return environment
