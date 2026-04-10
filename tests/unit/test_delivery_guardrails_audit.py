from __future__ import annotations

import subprocess

from pytest import MonkeyPatch

import tools.audit_delivery_guardrails as audit


def _protected_branch_payload() -> dict[str, object]:
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": ["commit-messages", "pr-review"],
            "checks": [
                {"context": "commit-messages", "app_id": 15368},
                {"context": "pr-review", "app_id": 15368},
            ],
        },
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "require_code_owner_reviews": False,
        },
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "required_conversation_resolution": {"enabled": True},
    }


def test_evaluate_remote_guardrails_defers_review_requirements_for_single_maintainer() -> (
    None
):
    report = audit._evaluate_remote_guardrails(
        protection=_protected_branch_payload(),
        rulesets=[],
        collaborators=[
            {
                "login": "CrownOpsEng",
                "permissions": {"pull": True},
            }
        ],
        codeowners_patterns=audit.CONTROL_PLANE_CODEOWNER_PATTERNS,
    )

    assert report.errors == ()
    assert any("one review-capable collaborator" in note for note in report.notes)
    assert report.warnings == ()


def test_evaluate_remote_guardrails_warns_when_multi_reviewer_repo_lacks_review_gates() -> (
    None
):
    report = audit._evaluate_remote_guardrails(
        protection=_protected_branch_payload(),
        rulesets=[],
        collaborators=[
            {"login": "CrownOpsEng", "permissions": {"pull": True}},
            {"login": "teammate", "permissions": {"pull": True}},
        ],
        codeowners_patterns=audit.CONTROL_PLANE_CODEOWNER_PATTERNS,
    )

    assert report.errors == ()
    assert any(
        "at least one approving review" in warning for warning in report.warnings
    )
    assert any("code owner reviews" in warning for warning in report.warnings)


def test_evaluate_remote_guardrails_errors_for_missing_core_branch_controls() -> None:
    payload = _protected_branch_payload()
    payload["required_status_checks"] = {
        "strict": False,
        "contexts": ["commit-messages"],
    }
    payload["enforce_admins"] = {"enabled": False}
    payload["allow_force_pushes"] = {"enabled": True}
    payload["required_conversation_resolution"] = {"enabled": False}

    report = audit._evaluate_remote_guardrails(
        protection=payload,
        rulesets=[],
        collaborators=[
            {"login": "CrownOpsEng", "permissions": {"pull": True}},
            {"login": "teammate", "permissions": {"pull": True}},
        ],
        codeowners_patterns=(),
    )

    assert any("strict status checks" in error for error in report.errors)
    assert any("missing required status checks" in error for error in report.errors)
    assert any("enforce admins" in error for error in report.errors)
    assert any("block force pushes" in error for error in report.errors)
    assert any("conversation resolution" in error for error in report.errors)
    assert any(".github/CODEOWNERS" in error for error in report.errors)


def test_evaluate_remote_guardrails_errors_for_unpinned_required_status_checks() -> (
    None
):
    payload = _protected_branch_payload()
    payload["required_status_checks"] = {
        "strict": True,
        "contexts": ["commit-messages", "pr-review"],
        "checks": [
            {"context": "commit-messages", "app_id": 15368},
            {"context": "pr-review", "app_id": None},
        ],
    }

    report = audit._evaluate_remote_guardrails(
        protection=payload,
        rulesets=[],
        collaborators=[{"login": "CrownOpsEng", "permissions": {"pull": True}}],
        codeowners_patterns=audit.CONTROL_PLANE_CODEOWNER_PATTERNS,
    )

    assert any(
        "pin required status checks to their app: pr-review" in error
        for error in report.errors
    )


def test_missing_codeowners_entries_reports_missing_patterns() -> None:
    missing = audit._missing_codeowners_patterns(("AGENTS.md", "docs/standards/**"))

    assert ".agents/skills/**" in missing
    assert ".github/actions/**" in missing
    assert ".github/ISSUE_TEMPLATE/**" in missing
    assert ".github/workflows/**" in missing
    assert "tools/benchmark_quality_gates.py" in missing
    assert "tools/message_standards.py" in missing
    assert "tools/run_ci_parity_checks.py" in missing
    assert "tools/run_pr_review_checks.py" in missing


def test_rulesets_only_repo_does_not_fail_branch_protection_audit() -> None:
    report = audit._evaluate_remote_guardrails(
        protection=None,
        rulesets=[{"name": "protect-main"}],
        collaborators=[{"login": "CrownOpsEng", "permissions": {"pull": True}}],
        codeowners_patterns=audit.CONTROL_PLANE_CODEOWNER_PATTERNS,
    )

    assert report.errors == ()
    assert any(
        "rulesets are the active platform control" in warning
        for warning in report.warnings
    )
    assert any("repository rulesets are configured" in note for note in report.notes)


def test_gh_api_json_or_none_returns_none_for_404(monkeypatch: MonkeyPatch) -> None:
    def fake_gh_json(*_args: str) -> object:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=("gh", "api", "repos/CrownOpsEng/tallylot/branches/main/protection"),
            stderr="gh: HTTP 404: Not Found",
        )

    monkeypatch.setattr(audit, "_gh_json", fake_gh_json)

    assert (
        audit._gh_api_json_or_none(
            "repos/CrownOpsEng/tallylot/branches/main/protection"
        )
        is None
    )
