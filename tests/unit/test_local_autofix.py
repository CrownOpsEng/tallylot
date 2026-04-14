from __future__ import annotations

import sys

from pytest import CaptureFixture, MonkeyPatch

import repo_support.local_autofix as local_autofix


def test_staged_repo_paths_reads_only_index() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git_paths(*args: str) -> tuple[str, ...]:
        calls.append(args)
        return ("repo_support/local_autofix.py", "docs/standards/implementation.md")

    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(local_autofix, "_git_paths", fake_git_paths)
    try:
        assert local_autofix.staged_repo_paths() == (
            "repo_support/local_autofix.py",
            "docs/standards/implementation.md",
        )
    finally:
        monkeypatch.undo()

    assert calls == [("diff", "--cached", "--name-only", "--diff-filter=ACMR")]


def test_run_local_autofix_returns_early_without_staged_paths(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(local_autofix, "staged_repo_paths", lambda: ())

    assert local_autofix.run_local_autofix() == 0

    assert "[auto-fix] no staged paths detected" in capsys.readouterr().out


def test_run_local_autofix_targets_only_staged_python_and_markdown(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_autofix,
        "staged_repo_paths",
        lambda: (
            "repo_support/local_autofix.py",
            "docs/standards/implementation.md",
            "notes/todo.txt",
        ),
    )
    monkeypatch.setattr(local_autofix, "_markdownlint_available", lambda: True)

    calls: list[tuple[tuple[str, ...], dict[str, str] | None]] = []

    def fake_run_command(
        command: tuple[str, ...], *, env: dict[str, str] | None = None
    ) -> int:
        calls.append((command, env))
        return 0

    monkeypatch.setattr(local_autofix, "_run_command", fake_run_command)
    monkeypatch.setattr(
        local_autofix,
        "_markdownlint_environment",
        lambda: {"PATH": "/bin"},
    )

    assert local_autofix.run_local_autofix() == 0

    assert calls == [
        (
            (
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--fix",
                "repo_support/local_autofix.py",
            ),
            None,
        ),
        (
            (
                sys.executable,
                "-m",
                "ruff",
                "format",
                "repo_support/local_autofix.py",
            ),
            None,
        ),
        (
            (
                "markdownlint",
                "--fix",
                "--config",
                ".markdownlint.json",
                "docs/standards/implementation.md",
            ),
            {"PATH": "/bin"},
        ),
    ]
