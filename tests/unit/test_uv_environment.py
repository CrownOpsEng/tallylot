from __future__ import annotations

from pathlib import Path

from repo_support.uv_environment import (
    default_project_environment,
    repo_uv_environment,
)


def test_default_project_environment_uses_home_scoped_external_env() -> None:
    assert default_project_environment() == str(
        Path.home() / ".venvs" / "tallylot-py312"
    )


def test_repo_uv_environment_preserves_existing_override() -> None:
    environment = repo_uv_environment({"UV_PROJECT_ENVIRONMENT": "/tmp/custom-env"})

    assert environment["UV_PROJECT_ENVIRONMENT"] == "/tmp/custom-env"
    assert environment["VIRTUAL_ENV"] == "/tmp/custom-env"
    assert environment["PATH"].split(":")[0] == "/tmp/custom-env/bin"


def test_repo_uv_environment_sets_default_when_missing() -> None:
    environment = repo_uv_environment({})

    expected = str(Path.home() / ".venvs" / "tallylot-py312")

    assert environment["UV_PROJECT_ENVIRONMENT"] == expected
    assert environment["VIRTUAL_ENV"] == expected
    assert environment["PATH"].split(":")[0] == f"{expected}/bin"
