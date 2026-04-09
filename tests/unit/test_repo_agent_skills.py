from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from repo_support.paths import repo_root


@dataclass(frozen=True)
class ExpectedSkill:
    display_name: str
    required_fragments: tuple[str, ...]


EXPECTED_SKILLS = {
    "adapter-authoring": ExpectedSkill(
        display_name="Adapter Authoring",
        required_fragments=(
            "docs/guides/write-an-adapter.md",
            ".claude/commands/adapter-authoring.md",
            "tools.scaffold_adapter",
        ),
    ),
    "docs-authoring": ExpectedSkill(
        display_name="Docs Authoring",
        required_fragments=(
            "docs/README.md",
            "docs/status/current-state.md",
            "docs/reference/repository-history.md",
            "docs/standards/implementation.md",
            "docs/standards/commits.md",
            "tools/docs_maintenance/cli.py",
            "tools/docs_maintenance/metadata.py",
            "uv run python -m tools.docs_maintenance sync --check",
        ),
    ),
    "implementation-workflow": ExpectedSkill(
        display_name="Implementation Workflow",
        required_fragments=(
            "docs/standards/engineering.md",
            "docs/standards/implementation.md",
            "docs/standards/commits.md",
            ".claude/commands/implementation-checkpoint.md",
            "shell-safe commit/PR authoring path",
            "shell-sensitive text",
        ),
    ),
    "issue-workflow": ExpectedSkill(
        display_name="Issue Workflow",
        required_fragments=(
            "docs/standards/issues.md",
            "docs/standards/delivery-guardrails.md",
            "docs/standards/commits.md",
            ".claude/commands/issue-workflow.md",
            "Summary",
            "Acceptance Criteria",
            "shell-safe PR-body guidance",
            "shell-sensitive",
        ),
    ),
    "pr-review": ExpectedSkill(
        display_name="PR Review",
        required_fragments=(
            "docs/standards/delivery-guardrails.md",
            "docs/standards/implementation.md",
            "docs/standards/commits.md",
            ".claude/commands/pr-review.md",
            "tools.audit_pr_review",
            "applicable surface groups",
        ),
    ),
    "balance-submission-operations": ExpectedSkill(
        display_name="Balance Submission",
        required_fragments=(
            ".claude/commands/balance-submission-operations.md",
            ".agents/skills/balance-submission-operations/scripts/balance_submission_operations.py",
            "checkpoint scaffold-balance-submission",
            "checkpoint submit-balances",
        ),
    ),
    "reconciliation-balance-operations": ExpectedSkill(
        display_name="Reconciliation Balances",
        required_fragments=(
            ".claude/commands/reconciliation-balance-operations.md",
            ".agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py",
        ),
    ),
    "reconciliation-tax-build": ExpectedSkill(
        display_name="Reconciliation And Tax Build",
        required_fragments=(
            "docs/concepts/reconciliation-tax-architecture.md",
            "docs/concepts/oracle-boundaries.md",
            "docs/concepts/transaction-classification.md",
            "docs/status/migration-sequence.md",
            ".claude/commands/reconciliation-tax-build.md",
            "ROADMAP.md",
        ),
    ),
    "round-verification-operations": ExpectedSkill(
        display_name="Round Verification",
        required_fragments=(
            "docs/guides/verify-a-round.md",
            ".claude/commands/round-verification.md",
            "tools.oracles.cli round scaffold",
            "tools.oracles.cli verification compare",
        ),
    ),
    "source-intake-operations": ExpectedSkill(
        display_name="Source Intake",
        required_fragments=(
            "docs/guides/operator-quickstart.md",
            "docs/guides/source-intake.md",
            ".claude/commands/source-intake.md",
            "source intake plan",
            "source intake apply",
        ),
    ),
}


def _skill_root(skill_name: str) -> Path:
    return repo_root() / ".agents" / "skills" / skill_name


def test_expected_repo_local_skills_exist() -> None:
    skill_names = {
        path.name
        for path in (repo_root() / ".agents" / "skills").iterdir()
        if path.is_dir()
    }

    for skill_name in EXPECTED_SKILLS:
        assert skill_name in skill_names, f"missing repo-local skill {skill_name}"


def test_repo_local_skill_metadata_and_bodies_are_lightweight() -> None:
    for skill_name, expected in EXPECTED_SKILLS.items():
        skill_root = _skill_root(skill_name)
        skill_path = skill_root / "SKILL.md"
        metadata_path = skill_root / "agents" / "openai.yaml"

        assert skill_path.exists(), f"{skill_name} is missing SKILL.md"
        assert metadata_path.exists(), f"{skill_name} is missing agents/openai.yaml"

        skill_text = skill_path.read_text(encoding="utf-8")
        skill_lines = skill_text.splitlines()
        assert len(skill_lines) <= 120, (
            f"{skill_name} is too large for progressive disclosure"
        )
        assert "## Workflow" in skill_text, (
            f"{skill_name} is missing a workflow section"
        )
        for fragment in expected.required_fragments:
            assert fragment in skill_text, f"{skill_name} is missing {fragment}"

        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
        assert metadata["interface"]["display_name"] == expected.display_name
        assert f"${skill_name}" in metadata["interface"]["default_prompt"]
        assert metadata["policy"]["allow_implicit_invocation"] is True
