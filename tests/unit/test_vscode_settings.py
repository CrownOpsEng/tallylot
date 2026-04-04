from __future__ import annotations

import json

from repo_support.paths import vscode_settings_path


def test_workspace_vscode_settings_pin_external_python_environment() -> None:
    settings = json.loads(vscode_settings_path().read_text(encoding="utf-8"))

    assert (
        settings["python.defaultInterpreterPath"]
        == "${env:HOME}/.venvs/tallylot-py312/bin/python"
    )
    assert (
        settings["terminal.integrated.env.linux"]["UV_PROJECT_ENVIRONMENT"]
        == "${env:HOME}/.venvs/tallylot-py312"
    )
    assert settings["pylint.path"] == [
        "${interpreter}",
        "-m",
        "tools.vscode_pylint",
    ]
