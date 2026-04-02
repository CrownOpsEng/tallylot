from __future__ import annotations

from tools.install_git_hooks import HOOK_TEMPLATE
from tools.pre_commit_hook import _format_candidates, _skip_value


def test_format_candidates_selects_only_safe_staged_python_files() -> None:
    candidates = _format_candidates(
        initially_staged=("src/app.py", "README.md", "src/types.pyi"),
        initially_unstaged=("README.md",),
    )

    assert candidates == ("src/app.py", "src/types.pyi")


def test_format_candidates_skips_partially_staged_python_files() -> None:
    candidates = _format_candidates(
        initially_staged=("src/app.py", "src/other.py"),
        initially_unstaged=("src/app.py",),
    )

    assert candidates == ("src/other.py",)


def test_skip_value_appends_formatter_hooks_once() -> None:
    assert _skip_value(None) == "ruff,ruff-format"
    assert _skip_value("pytest,ruff") == "pytest,ruff,ruff-format"


def test_install_hook_template_execs_repo_pre_commit_wrapper() -> None:
    assert "-m tools.pre_commit_hook" in HOOK_TEMPLATE
    assert 'REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"' in HOOK_TEMPLATE
