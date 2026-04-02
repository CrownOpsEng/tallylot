from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATHS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / ".claude").rglob("*.md")),
]


def test_docs_do_not_reference_removed_legacy_paths() -> None:
    forbidden = ("06_scripts/", "07_skills/")

    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still references {needle}"


def test_documented_claude_command_routes_exist() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-reconcile.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
    )

    for relative_path in command_paths:
        assert (REPO_ROOT / relative_path).exists(), f"missing documented command route: {relative_path}"


def test_documented_claude_command_routes_are_not_ignored() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-reconcile.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
    )

    for relative_path in command_paths:
        result = subprocess.run(
            ("git", "check-ignore", "-q", relative_path),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, f"ignored command route: {relative_path}"


def test_source_intake_route_mentions_typed_intake_and_reconcile_commands() -> None:
    text = (REPO_ROOT / ".claude/commands/source-intake.md").read_text(encoding="utf-8")

    for command in ("source intake plan", "source intake apply", "source manifest", "source reconcile"):
        assert command in text


def test_supporting_route_mentions_pdf_balance_extraction_command() -> None:
    text = (REPO_ROOT / ".claude/commands/supporting-artifacts.md").read_text(encoding="utf-8")

    assert "supporting extract-pdf-balances" in text
