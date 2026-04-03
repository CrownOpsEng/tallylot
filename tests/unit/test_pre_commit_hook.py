from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import tools.install_git_hooks
from tools.install_git_hooks import _COMMIT_MSG_HOOK_TEMPLATE, _HOOK_TEMPLATE
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
    assert "-m tools.pre_commit_hook" in _HOOK_TEMPLATE
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in _HOOK_TEMPLATE
    assert 'export UV_PROJECT_ENVIRONMENT="$PROJECT_ENVIRONMENT"' in _HOOK_TEMPLATE
    assert "--hook-type=commit-msg" in _COMMIT_MSG_HOOK_TEMPLATE
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in _COMMIT_MSG_HOOK_TEMPLATE


def test_install_hooks_uses_pre_commit_overwrite_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[tuple[str, ...], Path, str | None]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check is True
        commands.append((tuple(command), cwd, None if env is None else env.get("UV_PROJECT_ENVIRONMENT")))
        return subprocess.CompletedProcess(command, 0)

    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("", encoding="utf-8")
    commit_msg_hook_path = tmp_path / ".git" / "hooks" / "commit-msg"
    commit_msg_hook_path.write_text("", encoding="utf-8")

    environment_root = tmp_path / "external-env"
    (environment_root / "bin").mkdir(parents=True)
    monkeypatch.setattr("tools.install_git_hooks.sys.executable", str(environment_root / "bin/python3"))
    monkeypatch.setattr("tools.install_git_hooks.sys.prefix", str(environment_root))
    monkeypatch.setattr("tools.install_git_hooks.sys.base_prefix", "/usr")
    monkeypatch.setattr(subprocess, "run", fake_run)

    tools.install_git_hooks._install_hooks(tmp_path)

    assert commands == [
        (("git", "config", "--local", "commit.template", ".gitmessage.txt"), tmp_path, None),
        (
            (
                "uv",
                "run",
                "pre-commit",
                "install",
                "--overwrite",
                "--hook-type",
                "pre-commit",
                "--hook-type",
                "commit-msg",
            ),
            tmp_path,
            str(Path.home() / ".venvs" / "tallylot-py312"),
        ),
    ]
    hook_text = hook_path.read_text(encoding="utf-8")
    assert f"PROJECT_ENVIRONMENT={environment_root}" in hook_text
    assert f"PYTHON={environment_root / 'bin/python3'}" in hook_text
    commit_msg_hook_text = commit_msg_hook_path.read_text(encoding="utf-8")
    assert f"PROJECT_ENVIRONMENT={environment_root}" in commit_msg_hook_text
    assert "--hook-type=commit-msg" in commit_msg_hook_text


def test_install_hooks_falls_back_to_default_external_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("", encoding="utf-8")
    commit_msg_hook_path = tmp_path / ".git" / "hooks" / "commit-msg"
    commit_msg_hook_path.write_text("", encoding="utf-8")

    def fake_run(
        command: list[str],
        *,
        check: bool,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("tools.install_git_hooks.sys.executable", "/usr/bin/python3")
    monkeypatch.setattr("tools.install_git_hooks.sys.prefix", "/usr")
    monkeypatch.setattr("tools.install_git_hooks.sys.base_prefix", "/usr")
    monkeypatch.setattr(subprocess, "run", fake_run)

    tools.install_git_hooks._install_hooks(tmp_path)

    expected_environment = Path.home() / ".venvs" / "tallylot-py312"
    assert f"PROJECT_ENVIRONMENT={expected_environment}" in hook_path.read_text(encoding="utf-8")
    assert f"PROJECT_ENVIRONMENT={expected_environment}" in commit_msg_hook_path.read_text(encoding="utf-8")
