from __future__ import annotations

from pathlib import Path

from tools.uv_environment import default_project_environment, repo_uv_environment


def test_default_project_environment_uses_home_scoped_external_env() -> None:
    assert default_project_environment() == str(Path.home() / ".venvs" / "tallylot-py312")


def test_repo_uv_environment_preserves_existing_override() -> None:
    environment = repo_uv_environment({"UV_PROJECT_ENVIRONMENT": "/tmp/custom-env"})

    assert environment["UV_PROJECT_ENVIRONMENT"] == "/tmp/custom-env"


def test_repo_uv_environment_sets_default_when_missing() -> None:
    environment = repo_uv_environment({})

    assert environment["UV_PROJECT_ENVIRONMENT"] == str(Path.home() / ".venvs" / "tallylot-py312")
