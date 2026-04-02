from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tools import docs_maintenance

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "ROADMAP.md",
    REPO_ROOT / "CHANGELOG.md",
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


def test_parse_frontmatter_supports_nav_order() -> None:
    path = REPO_ROOT / "docs" / "guides" / "example.md"
    text = dedent(
        """\
        ---
        title: "Example"
        summary: "Example summary."
        doc_type: guide
        audience: human
        owner: repo
        status: active
        nav_order: 20
        ---

        Example body.
        """
    )

    frontmatter = docs_maintenance.parse_frontmatter(text, path)
    docs_maintenance.validate_frontmatter(path, frontmatter)

    assert frontmatter["nav_order"] == 20


def test_parse_frontmatter_rejects_invalid_nav_order() -> None:
    path = REPO_ROOT / "docs" / "guides" / "example.md"
    text = dedent(
        """\
        ---
        title: "Example"
        summary: "Example summary."
        doc_type: guide
        audience: human
        owner: repo
        status: active
        nav_order: "first"
        ---

        Example body.
        """
    )

    frontmatter = docs_maintenance.parse_frontmatter(text, path)

    with pytest.raises(ValueError, match="must use an integer for nav_order"):
        docs_maintenance.validate_frontmatter(path, frontmatter)


def test_docs_and_agents_pages_have_valid_frontmatter() -> None:
    paths = (
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / "agents").rglob("*.md")),
    )
    documents = docs_maintenance.validate_documents()

    assert {document.path for document in documents} == set(paths)


def test_repo_markdown_paths_include_root_repo_docs() -> None:
    repo_paths = set(docs_maintenance.repo_markdown_paths())

    assert REPO_ROOT / "ROADMAP.md" in repo_paths
    assert REPO_ROOT / "CHANGELOG.md" in repo_paths


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


def test_validate_markdown_links_accepts_reference_style_links(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("## Step One\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text(
        dedent(
            """\
            [Guide][guide]
            [Same File]

            ## Same File

            [guide]: docs/guides/sample.md#step-one
            [same file]: #same-file
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_markdown_links([readme, guide])


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


def test_validate_markdown_links_rejects_broken_reference_style_link(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        dedent(
            """\
            [Guide][guide]

            [guide]: docs/guides/missing.md
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="links to missing path docs/guides/missing.md"):
        docs_maintenance.validate_markdown_links([readme])


def test_validate_markdown_links_accepts_duplicate_github_style_heading_anchor(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    page.write_text(
        dedent(
            """\
            # Overview

            ## Step

            ## Step

            [Later](#step-1)
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_markdown_links([page])


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


def test_scaffold_agents_doc_requires_explicit_doc_type(
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
            "--section",
            "agents",
            "--slug",
            "example-agent",
            "--title",
            "Example Agent",
            "--summary",
            "Example agent guidance.",
        ]
    )

    assert exit_code == 1


def test_scaffold_agents_doc_accepts_explicit_doc_type(
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
            "--section",
            "agents",
            "--slug",
            "example-agent",
            "--title",
            "Example Agent",
            "--summary",
            "Example agent guidance.",
            "--doc-type",
            "standard",
        ]
    )

    assert exit_code == 0

    created = tmp_path / "agents" / "example-agent.md"
    frontmatter = docs_maintenance.parse_frontmatter(created.read_text(encoding="utf-8"), created)

    assert frontmatter["doc_type"] == "standard"
    assert frontmatter["audience"] == "agent"


def test_validate_uv_examples_rejects_bare_uv_examples(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    page.write_text("Run `uv run python -m tools.docs_maintenance sync --check`.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="markdown surfaces contain bare uv examples"):
        docs_maintenance.validate_uv_examples([page])


def test_fenced_tilde_code_blocks_are_ignored_for_uv_and_link_validation(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Sample\n", encoding="utf-8")
    page = tmp_path / "README.md"
    page.write_text(
        dedent(
            """\
            ~~~bash
            uv run python -m tools.docs_maintenance sync --check
            [Guide](docs/guides/missing.md)
            ~~~
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_uv_examples([page])
    docs_maintenance.validate_markdown_links([page, guide])


def test_indented_code_blocks_are_ignored_for_uv_and_link_validation(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Sample\n", encoding="utf-8")
    page = tmp_path / "README.md"
    page.write_text(
        dedent(
            """\
            Paragraph.

                uv run python -m tools.docs_maintenance sync --check
                [Guide](docs/guides/missing.md)
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_uv_examples([page])
    docs_maintenance.validate_markdown_links([page, guide])


def test_sync_check_rejects_bare_uv_examples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_root = tmp_path / "docs"
    concepts_root = docs_root / "concepts"
    concepts_root.mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    (tmp_path / ".claude" / "commands").mkdir(parents=True)

    (docs_root / "README.md").write_text(
        dedent(
            """\
            ---
            title: "Documentation"
            summary: "Docs home."
            doc_type: reference
            audience: human
            owner: repo
            status: active
            ---

            ## Concepts

            <!-- docs-maintenance:start concepts -->
            <!-- docs-maintenance:end concepts -->

            ## Guides

            <!-- docs-maintenance:start guides -->
            <!-- docs-maintenance:end guides -->

            ## Reference

            <!-- docs-maintenance:start reference -->
            <!-- docs-maintenance:end reference -->

            ## Status

            <!-- docs-maintenance:start status -->
            <!-- docs-maintenance:end status -->

            ## Standards

            <!-- docs-maintenance:start standards -->
            <!-- docs-maintenance:end standards -->

            Run `uv run python -m tools.docs_maintenance sync --check`.
            """
        ),
        encoding="utf-8",
    )
    (concepts_root / "example.md").write_text(
        dedent(
            """\
            ---
            title: "Example"
            summary: "Example concept."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            nav_order: 10
            ---

            ## Example
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("# ROADMAP\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    monkeypatch.setattr(docs_maintenance.cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_maintenance.cli, "DOCS_ROOT", docs_root)
    monkeypatch.setattr(docs_maintenance.cli, "AGENTS_ROOT", tmp_path / "agents")
    monkeypatch.setattr(docs_maintenance.state, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_maintenance.state, "DOCS_ROOT", docs_root)
    monkeypatch.setattr(docs_maintenance.state, "AGENTS_ROOT", tmp_path / "agents")
    monkeypatch.setattr(docs_maintenance.links, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(docs_maintenance.links, "DOCS_ROOT", docs_root)
    monkeypatch.setattr(docs_maintenance.links, "AGENTS_ROOT", tmp_path / "agents")

    assert docs_maintenance.main(["sync", "--check"]) == 1
