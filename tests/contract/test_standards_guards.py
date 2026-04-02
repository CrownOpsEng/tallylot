from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repo_has_no_type_ignore_comments() -> None:
    python_files = (
        REPO_ROOT / "conftest.py",
        *sorted((REPO_ROOT / "src").rglob("*.py")),
        *sorted((REPO_ROOT / "tests").rglob("*.py")),
        *sorted((REPO_ROOT / "tools").rglob("*.py")),
    )
    forbidden = ("type:" + " ignore", "pyright:" + " ignore")

    for path in python_files:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains forbidden typing bypass {needle!r}"


def test_markdownlint_only_disables_md013() -> None:
    config = json.loads((REPO_ROOT / ".markdownlint.json").read_text(encoding="utf-8"))

    assert config == {"default": True, "MD013": False}


def test_typecheck_configs_remain_strict() -> None:
    mypy_text = (REPO_ROOT / "mypy.ini").read_text(encoding="utf-8")
    pyright_config = json.loads((REPO_ROOT / "pyrightconfig.json").read_text(encoding="utf-8"))

    assert "strict = true" in mypy_text
    assert "warn_unused_ignores = true" in mypy_text
    assert pyright_config["typeCheckingMode"] == "strict"
    assert pyright_config["reportUnnecessaryTypeIgnoreComment"] is True
