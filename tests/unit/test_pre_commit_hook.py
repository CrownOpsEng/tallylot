from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_support.pytest_commands import build_fast_pytest_command
import tools.install_git_hooks
import tools.pre_commit_hook
import tools.run_fast_pytest
from tools.install_git_hooks import _COMMIT_MSG_HOOK_TEMPLATE, _HOOK_TEMPLATE
from tools.pre_commit_hook import _format_candidates


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


def test_pre_commit_wrapper_fails_when_commit_msg_hook_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    assert tools.pre_commit_hook.main([]) == 1

    assert "repo commit-msg hook is not installed" in capsys.readouterr().err


def test_pre_commit_wrapper_rejects_stale_commit_msg_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "commit-msg").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert tools.pre_commit_hook.main([]) == 1

    assert "repo commit-msg hook is stale or invalid" in capsys.readouterr().err


def test_pre_commit_wrapper_runs_when_commit_msg_hook_is_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    format_calls: list[tuple[str, ...]] = []
    pre_commit_calls: list[str] = []

    def fake_git_paths(*args: str) -> tuple[str, ...]:
        del args
        return ()

    def fake_format_and_stage(paths: tuple[str, ...]) -> int:
        format_calls.append(paths)
        return 0

    def fake_run_pre_commit() -> int:
        pre_commit_calls.append("run")
        return 0

    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "commit-msg").write_text(
        "#!/usr/bin/env bash\npre_commit hook-impl --hook-type=commit-msg\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tools.pre_commit_hook, "_git_paths", fake_git_paths)
    monkeypatch.setattr(
        tools.pre_commit_hook, "_format_and_stage", fake_format_and_stage
    )
    monkeypatch.setattr(tools.pre_commit_hook, "_run_pre_commit", fake_run_pre_commit)

    assert tools.pre_commit_hook.main([]) == 0
    assert format_calls == [()]
    assert pre_commit_calls == ["run"]


def test_install_hook_template_execs_repo_pre_commit_wrapper() -> None:
    assert "-m tools.pre_commit_hook" in _HOOK_TEMPLATE
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in _HOOK_TEMPLATE
    assert 'export UV_PROJECT_ENVIRONMENT="$PROJECT_ENVIRONMENT"' in _HOOK_TEMPLATE
    assert "--hook-type=commit-msg" in _COMMIT_MSG_HOOK_TEMPLATE
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in _COMMIT_MSG_HOOK_TEMPLATE


def test_install_hooks_syncs_environment_before_writing_repo_hooks(
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
        commands.append(
            (
                tuple(command),
                cwd,
                None if env is None else env.get("UV_PROJECT_ENVIRONMENT"),
            )
        )
        return subprocess.CompletedProcess(command, 0)

    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("", encoding="utf-8")
    commit_msg_hook_path = tmp_path / ".git" / "hooks" / "commit-msg"
    commit_msg_hook_path.write_text("", encoding="utf-8")

    environment_root = tmp_path / "external-env"
    (environment_root / "bin").mkdir(parents=True)
    monkeypatch.setattr(
        "tools.install_git_hooks.sys.executable", str(environment_root / "bin/python3")
    )
    monkeypatch.setattr("tools.install_git_hooks.sys.prefix", str(environment_root))
    monkeypatch.setattr("tools.install_git_hooks.sys.base_prefix", "/usr")
    monkeypatch.setattr(subprocess, "run", fake_run)

    tools.install_git_hooks._install_hooks(tmp_path)

    assert commands == [
        (
            ("git", "config", "--local", "commit.template", ".gitmessage.txt"),
            tmp_path,
            None,
        ),
        (
            ("uv", "sync", "--frozen"),
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
        del check, cwd, env
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("tools.install_git_hooks.sys.executable", "/usr/bin/python3")
    monkeypatch.setattr("tools.install_git_hooks.sys.prefix", "/usr")
    monkeypatch.setattr("tools.install_git_hooks.sys.base_prefix", "/usr")
    monkeypatch.setattr(subprocess, "run", fake_run)

    tools.install_git_hooks._install_hooks(tmp_path)

    expected_environment = Path.home() / ".venvs" / "tallylot-py312"
    assert f"PROJECT_ENVIRONMENT={expected_environment}" in hook_path.read_text(
        encoding="utf-8"
    )
    assert (
        f"PROJECT_ENVIRONMENT={expected_environment}"
        in commit_msg_hook_path.read_text(encoding="utf-8")
    )


def test_pre_commit_config_uses_repo_owned_fast_pytest_entrypoint() -> None:
    config_text = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "entry: uv run python -m tools.run_fast_pytest" in config_text
    assert "--no-cov -q" not in config_text
    assert 'pytest -m "unit and not slow"' not in config_text


def test_run_fast_pytest_uses_shared_command_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_command: tuple[str, ...] | None = None

    def fake_run(
        command: tuple[str, ...],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        nonlocal captured_command
        del check, env
        captured_command = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert tools.run_fast_pytest.main([]) == 0
    assert captured_command == build_fast_pytest_command()
