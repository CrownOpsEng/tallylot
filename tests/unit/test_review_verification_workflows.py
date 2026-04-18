from __future__ import annotations

from repo_support.paths import repo_root


def test_pr_review_workflow_uses_draft_aware_planner_gated_atomic_jobs() -> None:
    workflow_text = (repo_root() / ".github/workflows/pr-review.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow_text
    assert "paths:" not in workflow_text
    assert "paths-ignore:" not in workflow_text
    assert "PR_DRAFT: ${{ github.event.pull_request.draft }}" in workflow_text
    assert "MODE=planned" in workflow_text
    assert 'if [ "$PR_DRAFT" != "true" ]; then' in workflow_text
    assert '--mode "$MODE" \\' in workflow_text
    for job_name in (
        "plan-pr-review:",
        "commit-messages:",
        "pr-metadata:",
        "docs-maintenance:",
        "markdownlint:",
        "target-naming:",
        "actionlint:",
        "ruff:",
        "mypy:",
        "pyright:",
        "pylint:",
        "repo-agent-skills:",
        "standards-guards:",
        "docs-runtime-parity:",
        "delivery-guardrails-audit:",
        "pr-metadata-validator:",
        "commit-message-validator:",
        "pre-commit-hook-tooling:",
        "quality-gates-tooling:",
        "audit-pr-review:",
        "run-pr-review-checks:",
        "ci-tooling:",
        "pytest-full:",
        "test-stress-checks:",
        "build:",
        "verify-wheel:",
        "coverage-hotspots:",
        "pr-review:",
    ):
        assert job_name in workflow_text
    assert "tools.run_ci_parity_checks" not in workflow_text
    assert "tools.run_review_check --check-id target-naming" in workflow_text
    assert "tools.run_review_check --check-id pytest-full" in workflow_text
    assert "needs.build.result == 'success'" in workflow_text
    assert "needs.pytest-full.result == 'success'" in workflow_text
    assert "tools.evaluate_review_results" in workflow_text
    actionlint_job = workflow_text.split("  actionlint:\n", maxsplit=1)[1].split(
        "  ruff:\n", maxsplit=1
    )[0]
    assert 'include-ci-group: "true"' in actionlint_job
    assert "  pr-review:\n    if: ${{ always() }}\n    needs:\n" in workflow_text
    pr_review_needs = workflow_text.split("  pr-review:\n", maxsplit=1)[1].split(
        "    runs-on:", maxsplit=1
    )[0]
    assert "- ci-tooling" in pr_review_needs
    assert "- verify-wheel" in pr_review_needs
    assert "- coverage-hotspots" not in pr_review_needs


def test_main_ci_workflow_uses_planner_gated_atomic_jobs() -> None:
    workflow_text = (repo_root() / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )

    assert "push:" in workflow_text
    assert "workflow_dispatch:" in workflow_text
    assert "plan-main-ci:" in workflow_text
    assert "main-ci-result:" in workflow_text
    assert (
        "contains(fromJSON(needs.plan-main-ci.outputs.selected_checks)" in workflow_text
    )
    assert "tools.run_ci_parity_checks" not in workflow_text
    assert "target-naming:" in workflow_text
    assert "tools.run_review_check --check-id target-naming" in workflow_text
    assert "tools.run_review_check --check-id ci-tooling" in workflow_text
    assert "tools.evaluate_review_results" in workflow_text
    actionlint_job = workflow_text.split("  actionlint:\n", maxsplit=1)[1].split(
        "  ruff:\n", maxsplit=1
    )[0]
    assert 'include-ci-group: "true"' in actionlint_job
    main_ci_needs = workflow_text.split("  main-ci-result:\n", maxsplit=1)[1].split(
        "    runs-on:", maxsplit=1
    )[0]
    assert "- verify-wheel" in main_ci_needs
    assert "- coverage-hotspots" not in main_ci_needs


def test_setup_action_pins_external_actions_and_uv_version() -> None:
    action_text = (
        repo_root() / ".github/actions/setup-python-uv/action.yml"
    ).read_text(encoding="utf-8")

    assert (
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405" in action_text
    )
    assert "astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9" in action_text
    assert 'version: "0.9.20"' in action_text
    assert "enable-cache: true" in action_text
    assert "include-ci-group:" in action_text
    assert 'default: "false"' in action_text
    assert 'PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312"' in action_text
    assert (
        'echo "UV_PROJECT_ENVIRONMENT=$PROJECT_ENVIRONMENT" >> "$GITHUB_ENV"'
        in action_text
    )
    assert 'echo "$PROJECT_ENVIRONMENT/bin" >> "$GITHUB_PATH"' in action_text
    assert "SYNC_ARGS=(--python 3.12 --frozen)" in action_text
    assert "SYNC_ARGS+=(--no-group ci)" in action_text
    assert 'uv sync "${SYNC_ARGS[@]}"' in action_text
    assert "uv cache prune --ci" in action_text


def test_workflows_pin_node24_artifact_actions() -> None:
    pr_review_text = (repo_root() / ".github/workflows/pr-review.yml").read_text(
        encoding="utf-8"
    )
    ci_text = (repo_root() / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for workflow_text in (pr_review_text, ci_text):
        assert (
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
            in workflow_text
        )
        assert (
            "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
            in workflow_text
        )
