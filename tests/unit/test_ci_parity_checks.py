from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

import tools.run_ci_parity_checks as ci_parity
from repo_support.paths import repo_root


def test_commit_message_range_uses_merge_base(monkeypatch: MonkeyPatch) -> None:
    def fake_git_stdout(*args: str) -> str:
        if args == ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"):
            return "origin/main"
        if args == ("merge-base", "HEAD", "origin/main"):
            return "abc123"
        if args == ("rev-parse", "HEAD"):
            return "def456"
        raise AssertionError(args)

    monkeypatch.setattr(ci_parity, "_git_stdout", fake_git_stdout)

    assert ci_parity._commit_message_range() == "abc123..def456"


def test_commit_message_range_falls_back_to_head_commit(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_git_stdout(*args: str) -> str:
        if args == ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"):
            return "origin/main"
        if args == ("merge-base", "HEAD", "origin/main"):
            return "abc123"
        if args == ("rev-parse", "HEAD"):
            return "abc123"
        raise AssertionError(args)

    monkeypatch.setattr(ci_parity, "_git_stdout", fake_git_stdout)

    assert ci_parity._commit_message_range() == "HEAD^!"


def test_ci_parity_stops_when_commit_message_step_fails(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ci_parity, "_commit_message_range", lambda: "base..head")

    def fake_run_step(step: ci_parity._ParityStep) -> int:
        assert step.name == "commit-messages"
        return 1

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)

    assert ci_parity.main(["--include-commit-messages"]) == 1


def test_ci_parity_requires_full_pr_metadata_input(tmp_path: Path) -> None:
    pr_body = tmp_path / "pr.md"
    pr_body.write_text("Why:\n- explain\n", encoding="utf-8")

    assert ci_parity.main(["--pr-title", "ci: tighten parity"]) == 2
    assert ci_parity.main(["--pr-body-file", str(pr_body)]) == 2


def test_ci_parity_runs_quality_build_and_verify(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel_path = dist_dir / "tallylot-0.1.0-py3-none-any.whl"
    wheel_path.write_text("stub", encoding="utf-8")

    steps_seen: list[str] = []

    def fake_run_step(step: ci_parity._ParityStep) -> int:
        steps_seen.append(step.name)
        if step.name == "build":
            dist_dir.mkdir(exist_ok=True)
            wheel_path.write_text("rebuilt", encoding="utf-8")
        return 0

    def fake_verify_built_wheel(dist_path: Path) -> tuple[int, str, str]:
        assert dist_path.resolve() == dist_dir.resolve()
        return 0, "", ""

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)
    monkeypatch.setattr(ci_parity, "_verify_built_wheel", fake_verify_built_wheel)

    assert ci_parity.main([]) == 0
    assert steps_seen == ["quality", "build"]


def test_ci_parity_can_include_commit_messages(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ci_parity, "_commit_message_range", lambda: "base..head")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel_path = dist_dir / "tallylot-0.1.0-py3-none-any.whl"
    wheel_path.write_text("stub", encoding="utf-8")

    steps_seen: list[str] = []

    def fake_run_step(step: ci_parity._ParityStep) -> int:
        steps_seen.append(step.name)
        if step.name == "build":
            dist_dir.mkdir(exist_ok=True)
            wheel_path.write_text("rebuilt", encoding="utf-8")
        return 0

    def fake_verify_built_wheel(dist_path: Path) -> tuple[int, str, str]:
        assert dist_path.resolve() == dist_dir.resolve()
        return 0, "", ""

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)
    monkeypatch.setattr(ci_parity, "_verify_built_wheel", fake_verify_built_wheel)

    assert ci_parity.main(["--include-commit-messages"]) == 0
    assert steps_seen == ["commit-messages", "quality", "build"]


def test_ci_parity_can_include_pr_metadata(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ci_parity, "_pr_validation_shas", lambda: ("base", "head"))
    pr_body = tmp_path / "pr.md"
    pr_body_text = (
        "Why:\n- explain\n\n"
        "What:\n- change\n\n"
        "Checks:\n- uv run pytest\n\n"
        "Included checkpoints:\n- `ci: tighten parity`\n"
    )
    pr_body.write_text(
        pr_body_text,
        encoding="utf-8",
    )
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel_path = dist_dir / "tallylot-0.1.0-py3-none-any.whl"
    wheel_path.write_text("stub", encoding="utf-8")

    steps_seen: list[ci_parity._ParityStep] = []

    def fake_run_step(step: ci_parity._ParityStep) -> int:
        steps_seen.append(step)
        if step.name == "build":
            dist_dir.mkdir(exist_ok=True)
            wheel_path.write_text("rebuilt", encoding="utf-8")
        return 0

    def fake_verify_built_wheel(dist_path: Path) -> tuple[int, str, str]:
        assert dist_path.resolve() == dist_dir.resolve()
        return 0, "", ""

    monkeypatch.setattr(ci_parity, "_run_step", fake_run_step)
    monkeypatch.setattr(ci_parity, "_verify_built_wheel", fake_verify_built_wheel)

    assert (
        ci_parity.main(
            ["--pr-title", "ci: tighten parity", "--pr-body-file", str(pr_body)]
        )
        == 0
    )
    assert [step.name for step in steps_seen] == ["pr-metadata", "quality", "build"]
    assert steps_seen[0].command[4] == "tools.validate_pr_metadata"
    assert "--base-sha" in steps_seen[0].command
    assert "--head-sha" in steps_seen[0].command


def test_ci_workflow_uses_parity_runner_for_quality_job() -> None:
    workflow_text = (repo_root() / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )

    assert "uv run python -m tools.run_ci_parity_checks" in workflow_text
    assert "run: uv run mypy" not in workflow_text
    assert "run: uv run pyright" not in workflow_text
    assert "run: uv run pytest" not in workflow_text
