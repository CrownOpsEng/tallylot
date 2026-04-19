from __future__ import annotations

import pytest

import tools.pre_push_hook


def test_pre_push_hook_skips_without_current_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tools.pre_push_hook, "_current_branch", lambda: None)

    assert tools.pre_push_hook.main([]) == 0


def test_pre_push_hook_skips_without_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tools.pre_push_hook, "_current_branch", lambda: "feat/review")
    monkeypatch.setattr(tools.pre_push_hook, "_upstream_ref", lambda: None)

    assert tools.pre_push_hook.main([]) == 0


def test_pre_push_hook_skips_when_branch_has_no_open_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tools.pre_push_hook, "_current_branch", lambda: "feat/review")
    monkeypatch.setattr(
        tools.pre_push_hook, "_upstream_ref", lambda: "origin/feat/review"
    )
    monkeypatch.setattr(tools.pre_push_hook, "_load_open_pr_metadata", lambda: None)

    assert tools.pre_push_hook.main([]) == 0


def test_pre_push_hook_validates_current_head_against_open_pr_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, str] = {}

    def record_base_sha(sha: str) -> None:
        recorded["base"] = sha

    monkeypatch.setattr(
        tools.pre_push_hook, "_current_branch", lambda: "docs/metadata-hardening"
    )
    monkeypatch.setattr(
        tools.pre_push_hook,
        "_upstream_ref",
        lambda: "origin/docs/metadata-hardening",
    )
    monkeypatch.setattr(
        tools.pre_push_hook,
        "_load_open_pr_metadata",
        lambda: ("docs(commits): update policy", "Why:\n- test\n", "base123"),
    )
    monkeypatch.setattr(
        tools.pre_push_hook, "_ensure_commit_available", record_base_sha
    )
    monkeypatch.setattr(tools.pre_push_hook, "_current_head_sha", lambda: "head456")

    def fake_validate(
        *,
        branch_name: str,
        title: str,
        body: str,
        base_sha: str,
        head_sha: str,
    ) -> int:
        recorded["branch_name"] = branch_name
        recorded["title"] = title
        recorded["body"] = body
        recorded["base_sha"] = base_sha
        recorded["head_sha"] = head_sha
        return 0

    monkeypatch.setattr(tools.pre_push_hook, "_validate_pr_metadata", fake_validate)

    assert tools.pre_push_hook.main([]) == 0
    assert recorded == {
        "base": "base123",
        "branch_name": "docs/metadata-hardening",
        "title": "docs(commits): update policy",
        "body": "Why:\n- test\n",
        "base_sha": "base123",
        "head_sha": "head456",
    }


def test_pre_push_hook_rejects_invalid_branch_before_pr_lookup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        tools.pre_push_hook,
        "_current_branch",
        lambda: "control-plane/metadata-hardening",
    )

    def fail_if_called() -> None:
        raise AssertionError("PR lookup should not run for an invalid branch")

    monkeypatch.setattr(tools.pre_push_hook, "_load_open_pr_metadata", fail_if_called)

    assert tools.pre_push_hook.main([]) == 1
    assert "branch root must be one of" in capsys.readouterr().err


def test_pre_push_hook_fails_when_pr_metadata_query_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(tools.pre_push_hook, "_current_branch", lambda: "feat/review")
    monkeypatch.setattr(
        tools.pre_push_hook, "_upstream_ref", lambda: "origin/feat/review"
    )

    def fail() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(tools.pre_push_hook, "_load_open_pr_metadata", fail)

    assert tools.pre_push_hook.main([]) == 1
    assert (
        "pre-push pull request metadata validation failed: boom"
        in capsys.readouterr().err
    )
