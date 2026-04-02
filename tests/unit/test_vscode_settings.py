from __future__ import annotations

import json
from pathlib import Path


def test_workspace_vscode_settings_pin_external_python_environment() -> None:
    settings_path = Path(__file__).resolve().parents[2] / ".vscode" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    assert settings["python.defaultInterpreterPath"] == "${env:HOME}/.venvs/tallylot-py312/bin/python"
    assert settings["terminal.integrated.env.linux"]["UV_PROJECT_ENVIRONMENT"] == "${env:HOME}/.venvs/tallylot-py312"
