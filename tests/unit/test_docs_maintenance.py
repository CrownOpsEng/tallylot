from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tools import docs_maintenance

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    *sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")),
)


def test_docs_maintenance_sync_check_passes() -> None:
    assert docs_maintenance.main(["sync", "--check"]) == 0


def test_parse_frontmatter_supports_optional_fields() -> None:
    path = REPO_ROOT / "docs" / "reference" / "example.md"
    text = dedent(
        """\
        ---
        title: "Example"
        summary: "Example summary."
        doc_type: reference
        audience: human
        owner: repo
        status: active
        last_reviewed: "2026-04-01"
        related:
          - docs/reference/export-checklist.md
          - docs/guides/operator-quickstart.md
        ---

        Example body.
        """
    )

    frontmatter = docs_maintenance.parse_frontmatter(text, path)
    docs_maintenance.validate_frontmatter(path, frontmatter)

    assert frontmatter["last_reviewed"] == "2026-04-01"
    assert frontmatter["related"] == [
        "docs/reference/export-checklist.md",
        "docs/guides/operator-quickstart.md",
    ]


def test_docs_and_agents_pages_have_valid_frontmatter() -> None:
    paths = (
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / "agents").rglob("*.md")),
    )
    documents = docs_maintenance.validate_documents()

    assert {document.path for document in documents} == set(paths)


def test_entrypoints_do_not_reference_retired_docs_paths() -> None:
    for path in ENTRYPOINT_PATHS:
        text = path.read_text(encoding="utf-8")
        for retired_reference in docs_maintenance.RETIRED_REFERENCES:
            assert retired_reference not in text, (
                f"{path.relative_to(REPO_ROOT)} still references retired path {retired_reference}"
            )


def test_validate_markdown_links_accepts_repo_local_links(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    agents = tmp_path / "agents"
    commands = tmp_path / ".claude" / "commands"
    docs = tmp_path / "docs" / "guides"
    agents.mkdir(parents=True)
    commands.mkdir(parents=True)
    docs.mkdir(parents=True)

    (docs / "sample.md").write_text(
        dedent(
            """\
            ## Step One

            Continue with the guide.
            """
        ),
        encoding="utf-8",
    )
    (agents / "context.md").write_text(
        dedent(
            """\
            ## Agent Context

            Use [Sample Guide](../docs/guides/sample.md#step-one).
            """
        ),
        encoding="utf-8",
    )
    (commands / "check.md").write_text(
        dedent(
            """\
            # Check

            See [Agent Context](../../agents/context.md#agent-context).
            """
        ),
        encoding="utf-8",
    )
    readme.write_text(
        dedent(
            """\
            # Repo

            - [Guide](docs/guides/sample.md#step-one)
            - [Agent](agents/context.md)
            - [Command](.claude/commands/check.md)
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_markdown_links(
        [
            readme,
            agents / "context.md",
            commands / "check.md",
            docs / "sample.md",
        ]
    )


def test_validate_markdown_links_rejects_missing_relative_target(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("# Repo\n\n[Missing](docs/does-not-exist.md)\n", encoding="utf-8")

    with pytest.raises(ValueError, match="links to missing path docs/does-not-exist.md"):
        docs_maintenance.validate_markdown_links([path])


def test_validate_markdown_links_rejects_missing_anchor(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("## Step One\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("[Guide](docs/guides/sample.md#missing-anchor)\n", encoding="utf-8")

    with pytest.raises(ValueError, match="links to missing anchor #missing-anchor"):
        docs_maintenance.validate_markdown_links([readme, guide])


def test_scaffold_workspace_doc_infers_reference_and_both(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docs_maintenance.cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_maintenance.cli, "DOCS_ROOT", tmp_path / "docs")
    monkeypatch.setattr(docs_maintenance.cli, "AGENTS_ROOT", tmp_path / "agents")
    monkeypatch.setattr(docs_maintenance.state, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_maintenance.state, "DOCS_ROOT", tmp_path / "docs")
    monkeypatch.setattr(docs_maintenance.state, "AGENTS_ROOT", tmp_path / "agents")

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--path",
            "docs/workspace/working/example.md",
            "--title",
            "Workspace Example",
            "--summary",
            "Example workspace guidance.",
        ]
    )

    assert exit_code == 0

    created = tmp_path / "docs" / "workspace" / "working" / "example.md"
    frontmatter = docs_maintenance.parse_frontmatter(created.read_text(encoding="utf-8"), created)

    assert frontmatter["doc_type"] == "reference"
    assert frontmatter["audience"] == "both"
