from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from repo_support.paths import repo_root

REQUIRED_STATUS_CHECKS = ("commit-messages", "pr-review")
CONTROL_PLANE_CODEOWNER_PATTERNS = (
    ".agents/skills/**",
    ".github/actions/**",
    ".github/ISSUE_TEMPLATE/**",
    ".github/workflows/**",
    ".github/pull_request_template.md",
    ".github/CODEOWNERS",
    "AGENTS.md",
    "docs/standards/**",
    ".claude/commands/**",
    "tools/install_git_hooks.py",
    "tools/pre_commit_hook.py",
    "tools/audit_delivery_guardrails.py",
    "tools/audit_pr_review.py",
    "tools/benchmark_quality_gates.py",
    "tools/message_standards.py",
    "tools/validate_commit_message.py",
    "tools/validate_pr_metadata.py",
    "tools/run_quality_gates.py",
    "tools/run_ci_parity_checks.py",
    "tools/run_pr_review_checks.py",
)


@dataclass(frozen=True)
class GuardrailReport:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit local and remote delivery guardrails for the current repository."
    )
    parser.add_argument("--repo", help="owner/name override for the GitHub repository")
    parser.add_argument(
        "--branch", help="branch to inspect; defaults to the GitHub default branch"
    )
    parser.add_argument(
        "--codeowners-path",
        type=Path,
        default=repo_root() / ".github" / "CODEOWNERS",
        help="Local CODEOWNERS file path to audit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the audit report as JSON",
    )
    return parser.parse_args(argv)


def _gh_json(*args: str) -> Any:
    result = subprocess.run(
        ("gh", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _gh_api_json_or_none(path: str) -> Any:
    try:
        return _gh_json("api", path)
    except subprocess.CalledProcessError as error:
        if "HTTP 404" in error.stderr:
            return None
        raise


def _repo_identity(
    repo_override: str | None, branch_override: str | None
) -> tuple[str, str]:
    if repo_override is not None and branch_override is not None:
        return repo_override, branch_override

    repo_view = cast(
        Mapping[str, object],
        _gh_json(
            "repo",
            "view",
            "--json",
            "nameWithOwner,defaultBranchRef",
        ),
    )
    repo_name = repo_override or cast(str, repo_view["nameWithOwner"])
    default_branch_ref = cast(Mapping[str, object], repo_view["defaultBranchRef"])
    branch_name = branch_override or cast(str, default_branch_ref["name"])
    return repo_name, branch_name


def _codeowners_patterns(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()

    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.split()[0])
    return tuple(patterns)


def _missing_codeowners_patterns(codeowners_patterns: Sequence[str]) -> tuple[str, ...]:
    present = set(codeowners_patterns)
    return tuple(
        pattern
        for pattern in CONTROL_PLANE_CODEOWNER_PATTERNS
        if pattern not in present
    )


def _required_status_contexts(protection: Mapping[str, object]) -> set[str]:
    required_status_checks = cast(
        Mapping[str, object] | None,
        protection.get("required_status_checks"),
    )
    if required_status_checks is None:
        return set()

    contexts = {
        context
        for context in cast(list[object], required_status_checks.get("contexts") or [])
        if isinstance(context, str)
    }
    for raw_check in cast(list[object], required_status_checks.get("checks") or []):
        if not isinstance(raw_check, Mapping):
            continue
        check = cast(Mapping[str, object], raw_check)
        context = check.get("context")
        if isinstance(context, str):
            contexts.add(context)
    return contexts


def _collaborator_is_review_capable(collaborator: Mapping[str, object]) -> bool:
    permissions_object = collaborator.get("permissions")
    if not isinstance(permissions_object, Mapping):
        return False
    permissions = cast(Mapping[str, object], permissions_object)
    return bool(permissions.get("pull"))


def _has_multi_reviewer_surface(collaborators: Sequence[Mapping[str, object]]) -> bool:
    review_capable = {
        login
        for collaborator in collaborators
        if isinstance(login := collaborator.get("login"), str)
        and _collaborator_is_review_capable(collaborator)
    }
    return len(review_capable) > 1


def _evaluate_codeowners_guardrails(
    codeowners_patterns: Sequence[str],
) -> tuple[str, ...]:
    missing_codeowners = _missing_codeowners_patterns(codeowners_patterns)
    if not codeowners_patterns:
        return ("local .github/CODEOWNERS is missing",)
    if missing_codeowners:
        return (
            ".github/CODEOWNERS is missing control-plane entries: "
            + ", ".join(missing_codeowners),
        )
    return ()


def _evaluate_status_check_guardrails(
    protection: Mapping[str, object],
) -> tuple[str, ...]:
    errors: list[str] = []
    required_status_checks = cast(
        Mapping[str, object] | None,
        protection.get("required_status_checks"),
    )
    if not isinstance(required_status_checks, Mapping):
        return ("branch protection must require strict status checks",)

    if not bool(required_status_checks.get("strict")):
        errors.append("branch protection must require strict status checks")

    expected_status_checks: set[str] = set(REQUIRED_STATUS_CHECKS)
    missing_status_checks = sorted(
        expected_status_checks - _required_status_contexts(protection)
    )
    if missing_status_checks:
        errors.append(
            "branch protection is missing required status checks: "
            + ", ".join(missing_status_checks)
        )
    return tuple(errors)


def _bool_setting(protection: Mapping[str, object], setting_name: str) -> bool:
    setting_object = protection.get(setting_name)
    if not isinstance(setting_object, Mapping):
        return False
    setting = cast(Mapping[str, object], setting_object)
    return bool(setting.get("enabled"))


def _review_guardrail_messages(
    collaborators: Sequence[Mapping[str, object]],
    pr_reviews: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    warnings: list[str] = []
    notes: list[str] = []
    review_count = cast(int, pr_reviews.get("required_approving_review_count") or 0)
    code_owner_reviews = bool(pr_reviews.get("require_code_owner_reviews"))

    if _has_multi_reviewer_surface(collaborators):
        if review_count < 1:
            warnings.append(
                "branch protection should require at least one approving review "
                "when more than one review-capable collaborator exists"
            )
        if not code_owner_reviews:
            warnings.append(
                "branch protection should require code owner reviews when more "
                "than one review-capable collaborator exists"
            )
        return tuple(warnings), ()

    if review_count < 1 or not code_owner_reviews:
        notes.append(
            "required approving reviews and code owner reviews remain deferred "
            "because the repo currently has only one review-capable collaborator"
        )
    return (), tuple(notes)


def _evaluate_remote_guardrails(
    *,
    protection: Mapping[str, object] | None,
    rulesets: Sequence[Mapping[str, object]],
    collaborators: Sequence[Mapping[str, object]],
    codeowners_patterns: Sequence[str],
) -> GuardrailReport:
    errors = list(_evaluate_codeowners_guardrails(codeowners_patterns))
    warnings: list[str] = []
    notes: list[str] = []

    if protection is None:
        if rulesets:
            warnings.append(
                "default-branch protection endpoint is absent; repository rulesets "
                "are the active platform control and branch-protection-specific "
                "checks were skipped"
            )
            notes.append("repository rulesets are configured")
            return GuardrailReport(
                errors=tuple(errors),
                warnings=tuple(warnings),
                notes=tuple(notes),
            )
        errors.append("default-branch protection is missing")
        return GuardrailReport(
            errors=tuple(errors),
            warnings=tuple(warnings),
            notes=tuple(notes),
        )

    errors.extend(_evaluate_status_check_guardrails(protection))

    if not _bool_setting(protection, "enforce_admins"):
        errors.append("branch protection must enforce admins")
    if _bool_setting(protection, "allow_force_pushes"):
        errors.append("branch protection must block force pushes")

    if not _bool_setting(protection, "required_conversation_resolution"):
        errors.append("branch protection must require conversation resolution")

    pr_reviews = cast(
        Mapping[str, object],
        protection.get("required_pull_request_reviews") or {},
    )
    review_warnings, review_notes = _review_guardrail_messages(
        collaborators, pr_reviews
    )
    warnings.extend(review_warnings)
    notes.extend(review_notes)

    if rulesets:
        notes.append("repository rulesets are configured")
    else:
        notes.append(
            "classic branch protection is the active platform control; no "
            "repository rulesets are configured"
        )

    return GuardrailReport(
        errors=tuple(errors),
        warnings=tuple(warnings),
        notes=tuple(notes),
    )


def _print_report(report: GuardrailReport) -> None:
    for label, items in (
        ("ERROR", report.errors),
        ("WARNING", report.warnings),
        ("NOTE", report.notes),
    ):
        for item in items:
            print(f"{label}: {item}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_name, branch_name = _repo_identity(args.repo, args.branch)
    codeowners_patterns = _codeowners_patterns(args.codeowners_path)

    protection = cast(
        Mapping[str, object] | None,
        _gh_api_json_or_none(f"repos/{repo_name}/branches/{branch_name}/protection"),
    )
    rulesets = cast(
        Sequence[Mapping[str, object]],
        _gh_json("api", f"repos/{repo_name}/rulesets"),
    )
    collaborators = cast(
        Sequence[Mapping[str, object]],
        _gh_json("api", f"repos/{repo_name}/collaborators?per_page=100"),
    )
    report = _evaluate_remote_guardrails(
        protection=protection,
        rulesets=rulesets,
        collaborators=collaborators,
        codeowners_patterns=codeowners_patterns,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "notes": report.notes,
                },
                indent=2,
            )
        )
    else:
        _print_report(report)

    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
