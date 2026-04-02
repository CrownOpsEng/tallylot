from __future__ import annotations

import ast
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


def override_active_roots(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    docs_root: Path | None = None,
) -> None:
    resolved_docs_root = docs_root or root / "docs"
    monkeypatch.setattr(docs_maintenance.state, "REPO_ROOT", root)
    monkeypatch.setattr(docs_maintenance.state, "DOCS_ROOT", resolved_docs_root)
    monkeypatch.setattr(docs_maintenance.state, "AGENTS_ROOT", root / "agents")


def test_docs_maintenance_sync_check_passes() -> None:
    docs_maintenance.cli.check_retired_references()


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


def test_parse_frontmatter_rejects_missing_related_target() -> None:
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
        related:
          - docs/does-not-exist.md
        ---

        Example body.
        """
    )

    frontmatter = docs_maintenance.parse_frontmatter(text, path)

    with pytest.raises(ValueError, match="uses missing related target docs/does-not-exist.md"):
        docs_maintenance.validate_frontmatter(path, frontmatter)


def test_parse_frontmatter_rejects_missing_related_anchor() -> None:
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
        related:
          - docs/guides/operator-quickstart.md#missing-anchor
        ---

        Example body.
        """
    )

    frontmatter = docs_maintenance.parse_frontmatter(text, path)

    with pytest.raises(ValueError, match="uses missing related anchor #missing-anchor"):
        docs_maintenance.validate_frontmatter(path, frontmatter)


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


def test_parse_frontmatter_wraps_yaml_errors() -> None:
    path = REPO_ROOT / "docs" / "guides" / "example.md"
    text = dedent(
        """\
        ---
        title: "Guide "Quoted""
        summary: "Broken summary."
        doc_type: guide
        audience: human
        owner: repo
        status: active
        ---
        """
    )

    with pytest.raises(ValueError, match="has invalid frontmatter"):
        docs_maintenance.parse_frontmatter(text, path)


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


def test_root_consumers_use_state_getters_instead_of_root_constants() -> None:
    root_constant_names = {"REPO_ROOT", "DOCS_ROOT", "AGENTS_ROOT"}
    for relative in (
        "tools/docs_maintenance/cli.py",
        "tools/docs_maintenance/links.py",
        "tools/docs_maintenance/metadata.py",
    ):
        module_path = REPO_ROOT / relative
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "state"
            for alias in node.names
        }
        assert imported_names.isdisjoint(root_constant_names), relative


def test_repo_markdown_paths_follow_active_state_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_root = tmp_path / "docs"
    agents_root = tmp_path / "agents"
    commands_root = tmp_path / ".claude" / "commands"
    docs_root.mkdir()
    agents_root.mkdir()
    commands_root.mkdir(parents=True)
    for path in (
        tmp_path / "README.md",
        tmp_path / "AGENTS.md",
        tmp_path / "ROADMAP.md",
        tmp_path / "CHANGELOG.md",
        docs_root / "page.md",
        agents_root / "note.md",
        commands_root / "check.md",
    ):
        path.write_text("# Example\n", encoding="utf-8")

    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    assert set(docs_maintenance.repo_markdown_paths()) == {
        tmp_path / "README.md",
        tmp_path / "AGENTS.md",
        tmp_path / "ROADMAP.md",
        tmp_path / "CHANGELOG.md",
        docs_root / "page.md",
        agents_root / "note.md",
        commands_root / "check.md",
    }


def test_docs_maintenance_root_exports_follow_active_state_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_root = tmp_path / "docs"
    agents_root = tmp_path / "agents"
    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    assert tmp_path == docs_maintenance.REPO_ROOT
    assert docs_root == docs_maintenance.DOCS_ROOT
    assert agents_root == docs_maintenance.AGENTS_ROOT


def test_entrypoints_do_not_reference_retired_docs_paths() -> None:
    for path in ENTRYPOINT_PATHS:
        text = path.read_text(encoding="utf-8")
        for retired_reference in docs_maintenance.RETIRED_REFERENCES:
            assert retired_reference not in text, (
                f"{path.relative_to(REPO_ROOT)} still references retired path {retired_reference}"
            )


def test_sync_check_ignores_plain_text_mentions_of_retired_paths(
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

            Historical note: `docs/file-map.md` was removed.
            """
        ),
        encoding="utf-8",
    )
    for path in ("README.md", "AGENTS.md", "ROADMAP.md", "CHANGELOG.md"):
        (tmp_path / path).write_text("# Root\n", encoding="utf-8")

    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    docs_maintenance.cli.check_retired_references()


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


def test_sync_check_rejects_retired_markdown_link_targets(
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

            See [old map](../file-map.md).
            """
        ),
        encoding="utf-8",
    )
    for path in ("README.md", "AGENTS.md", "ROADMAP.md", "CHANGELOG.md"):
        (tmp_path / path).write_text("# Root\n", encoding="utf-8")

    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    with pytest.raises(ValueError, match="still references retired path docs/file-map.md"):
        docs_maintenance.cli.check_retired_references()


def test_sync_check_rejects_retired_related_targets(
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
            related:
              - docs/file-map.md
            ---

            Example.
            """
        ),
        encoding="utf-8",
    )
    for path in ("README.md", "AGENTS.md", "ROADMAP.md", "CHANGELOG.md"):
        (tmp_path / path).write_text("# Root\n", encoding="utf-8")

    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    with pytest.raises(ValueError, match="still references retired path docs/file-map.md"):
        docs_maintenance.cli.check_retired_references()


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
    override_active_roots(monkeypatch, tmp_path)

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


def test_scaffold_rejects_repo_escape_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--path",
            "../escape.md",
            "--title",
            "Escape",
            "--summary",
            "Escape summary.",
            "--doc-type",
            "reference",
            "--audience",
            "human",
        ]
    )

    assert exit_code == 1
    assert not (tmp_path.parent / "escape.md").exists()


def test_scaffold_rejects_absolute_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)
    absolute_path = tmp_path / "outside.md"

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--path",
            str(absolute_path),
            "--title",
            "Absolute",
            "--summary",
            "Absolute summary.",
            "--doc-type",
            "reference",
            "--audience",
            "human",
        ]
    )

    assert exit_code == 1
    assert not absolute_path.exists()


def test_scaffold_rejects_slug_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--section",
            "guides",
            "--slug",
            "../escape",
            "--title",
            "Escape",
            "--summary",
            "Escape summary.",
            "--nav-order",
            "10",
        ]
    )

    assert exit_code == 1
    assert not (tmp_path / "docs" / "escape.md").exists()
    assert not (tmp_path / "escape.md").exists()


def test_scaffold_rejects_non_kebab_case_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--section",
            "guides",
            "--slug",
            "Bad Slug",
            "--title",
            "Bad Slug",
            "--summary",
            "Bad slug summary.",
            "--nav-order",
            "10",
        ]
    )

    assert exit_code == 1
    assert not (tmp_path / "docs" / "guides" / "Bad Slug.md").exists()


def test_scaffold_agents_doc_requires_explicit_doc_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

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
    override_active_roots(monkeypatch, tmp_path)

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


def test_scaffold_sync_managed_doc_accepts_nav_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    (tmp_path / "agents").mkdir()
    docs_root = tmp_path / "docs"
    (docs_root / "concepts").mkdir(parents=True)
    (docs_root / "guides").mkdir(parents=True)
    (docs_root / "reference").mkdir(parents=True)
    (docs_root / "status").mkdir(parents=True)
    (docs_root / "standards").mkdir(parents=True)
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
            """
        ),
        encoding="utf-8",
    )

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--section",
            "guides",
            "--slug",
            "example-guide",
            "--title",
            "Example Guide",
            "--summary",
            "Example guide summary.",
            "--nav-order",
            "70",
        ]
    )

    assert exit_code == 0

    created = tmp_path / "docs" / "guides" / "example-guide.md"
    frontmatter = docs_maintenance.parse_frontmatter(created.read_text(encoding="utf-8"), created)

    assert frontmatter["nav_order"] == 70


def test_scaffold_sync_managed_doc_requires_docs_readme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    (tmp_path / "agents").mkdir()
    docs_root = tmp_path / "docs"
    (docs_root / "concepts").mkdir(parents=True)
    (docs_root / "guides").mkdir(parents=True)
    (docs_root / "reference").mkdir(parents=True)
    (docs_root / "status").mkdir(parents=True)
    (docs_root / "standards").mkdir(parents=True)

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--section",
            "guides",
            "--slug",
            "example-guide",
            "--title",
            "Example Guide",
            "--summary",
            "Example guide summary.",
            "--nav-order",
            "70",
        ]
    )

    assert exit_code == 1
    assert not (tmp_path / "docs" / "guides" / "example-guide.md").exists()


def test_scaffold_sync_managed_doc_escapes_yaml_sensitive_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

    (tmp_path / "agents").mkdir()
    docs_root = tmp_path / "docs"
    (docs_root / "concepts").mkdir(parents=True)
    (docs_root / "guides").mkdir(parents=True)
    (docs_root / "reference").mkdir(parents=True)
    (docs_root / "status").mkdir(parents=True)
    (docs_root / "standards").mkdir(parents=True)
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
            """
        ),
        encoding="utf-8",
    )

    exit_code = docs_maintenance.main(
        [
            "scaffold",
            "--section",
            "guides",
            "--slug",
            "quoted-guide",
            "--title",
            'Guide "Quoted"',
            "--summary",
            'Summary with "quotes".',
            "--nav-order",
            "70",
        ]
    )

    assert exit_code == 0

    created = tmp_path / "docs" / "guides" / "quoted-guide.md"
    frontmatter = docs_maintenance.parse_frontmatter(created.read_text(encoding="utf-8"), created)

    assert frontmatter["title"] == 'Guide "Quoted"'
    assert frontmatter["summary"] == 'Summary with "quotes".'


def test_scaffold_rejects_nav_order_outside_sync_managed_docs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override_active_roots(monkeypatch, tmp_path)

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
            "--nav-order",
            "10",
        ]
    )

    assert exit_code == 1


def test_validate_documents_rejects_duplicate_nav_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_root = tmp_path / "docs"
    (docs_root / "guides").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    for name in ("one", "two"):
        (docs_root / "guides" / f"{name}.md").write_text(
            dedent(
                f"""\
                ---
                title: "{name.title()}"
                summary: "{name.title()} summary."
                doc_type: guide
                audience: human
                owner: repo
                status: active
                nav_order: 10
                ---

                ## {name.title()}
                """
            ),
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="duplicate nav_order 10 in docs/guides"):
        docs_maintenance.validate_documents()


def test_validate_documents_accepts_related_targets_in_active_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_root = tmp_path / "docs"
    (docs_root / "reference").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    (docs_root / "reference" / "target.md").write_text(
        dedent(
            """\
            ---
            title: "Target"
            summary: "Target summary."
            doc_type: reference
            audience: human
            owner: repo
            status: active
            ---

            ## Target Section
            """
        ),
        encoding="utf-8",
    )
    (docs_root / "reference" / "source.md").write_text(
        dedent(
            """\
            ---
            title: "Source"
            summary: "Source summary."
            doc_type: reference
            audience: human
            owner: repo
            status: active
            related:
              - docs/reference/target.md#target-section
            ---

            ## Source
            """
        ),
        encoding="utf-8",
    )

    documents = docs_maintenance.validate_documents()

    assert {document.relative_path for document in documents} == {
        "docs/reference/source.md",
        "docs/reference/target.md",
    }


def test_scaffold_rejects_duplicate_nav_order_and_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    docs_root = tmp_path / "docs"
    (tmp_path / "agents").mkdir()
    for section in ("concepts", "guides", "reference", "status", "standards"):
        (docs_root / section).mkdir(parents=True, exist_ok=True)
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
            """
        ),
        encoding="utf-8",
    )
    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    assert (
        docs_maintenance.main(
            [
                "scaffold",
                "--section",
                "guides",
                "--slug",
                "one",
                "--title",
                "One",
                "--summary",
                "One summary.",
                "--nav-order",
                "10",
            ]
        )
        == 0
    )

    assert (
        docs_maintenance.main(
            [
                "scaffold",
                "--section",
                "guides",
                "--slug",
                "two",
                "--title",
                "Two",
                "--summary",
                "Two summary.",
                "--nav-order",
                "10",
            ]
        )
        == 1
    )
    assert not (docs_root / "guides" / "two.md").exists()
    captured = capsys.readouterr()
    assert "docs/guides/one.md" in captured.out
    assert "docs/guides/two.md" not in captured.out


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


def test_blockquoted_fenced_code_blocks_are_ignored_for_uv_and_link_validation(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Sample\n", encoding="utf-8")
    page = tmp_path / "README.md"
    page.write_text(
        dedent(
            """\
            > ```bash
            > uv run python -m tools.docs_maintenance sync --check
            > [Guide](docs/guides/missing.md)
            > ```
            """
        ),
        encoding="utf-8",
    )

    docs_maintenance.validate_uv_examples([page])
    docs_maintenance.validate_markdown_links([page, guide])


def test_html_comments_are_ignored_for_uv_and_link_validation(tmp_path: Path) -> None:
    guide = tmp_path / "docs" / "guides" / "sample.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Sample\n", encoding="utf-8")
    page = tmp_path / "README.md"
    page.write_text(
        dedent(
            """\
            <!--
            uv run python -m tools.docs_maintenance sync --check
            [Guide](docs/guides/missing.md)
            -->
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

    override_active_roots(monkeypatch, tmp_path, docs_root=docs_root)

    assert docs_maintenance.main(["sync", "--check"]) == 1
