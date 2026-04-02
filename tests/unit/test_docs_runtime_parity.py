from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATHS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / ".claude").rglob("*.md")),
]
DOC_COMMAND_ROUTE_PATTERN = re.compile(
    r"uv run crypto-reconciliation "
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
)


def _documented_cli_routes() -> set[str]:
    routes: set[str] = set()

    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for match in DOC_COMMAND_ROUTE_PATTERN.finditer(text):
            routes.add(match.group("route"))

    return routes


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
        ".claude/commands/source-diff.md",
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
        ".claude/commands/source-diff.md",
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


def test_source_intake_route_mentions_typed_intake_and_diff_commands() -> None:
    text = (REPO_ROOT / ".claude/commands/source-intake.md").read_text(encoding="utf-8")

    for command in ("source intake plan", "source intake apply", "source manifest", "source diff"):
        assert command in text


def test_supporting_route_mentions_pdf_balance_extraction_command() -> None:
    text = (REPO_ROOT / ".claude/commands/supporting-artifacts.md").read_text(encoding="utf-8")

    assert "supporting extract-pdf-balances" in text


def test_documented_cli_routes_exist() -> None:
    for route in sorted(_documented_cli_routes()):
        result = subprocess.run(
            ("uv", "run", "crypto-reconciliation", *route.split(), "--help"),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"documented CLI route does not exist: {route}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def test_docs_use_lowercase_filenames_except_readmes() -> None:
    for path in sorted((REPO_ROOT / "docs").rglob("*")):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        assert path.name == path.name.lower(), f"doc filename is not lowercase: {path}"


def test_repo_docs_do_not_reference_personal_workspace_roots() -> None:
    forbidden = (
        "/home/user/",
        "Documents/CryptoLedgerWorkspaces/crypto-reconciliation-2025",
        "~/Documents/CryptoLedgerWorkspaces/crypto-reconciliation-2025",
    )
    paths = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "crypto-reconciliation.toml",
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / ".claude").rglob("*.md")),
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still references personal workspace path {needle}"


def test_private_oracle_manifest_is_not_checked_in() -> None:
    assert not (REPO_ROOT / "docs" / "reference" / "cointracking-full-export-manifest.csv").exists()


def test_reference_docs_do_not_check_in_oracle_data_files() -> None:
    forbidden_suffixes = {".csv", ".json", ".zip", ".html", ".pdf"}

    for path in sorted((REPO_ROOT / "docs" / "reference").rglob("*")):
        if not path.is_file():
            continue
        assert path.suffix not in forbidden_suffixes, (
            f"repo reference docs should not contain oracle data files: {path}"
        )


def test_adapter_pack_goldens_do_not_embed_absolute_home_paths() -> None:
    forbidden = ("/home/user/", "CoinTracking.info/crypto-reconciliation-2025")

    for path in sorted((REPO_ROOT / "tests" / "fixtures" / "adapter_packs").rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still embeds absolute local path content"
