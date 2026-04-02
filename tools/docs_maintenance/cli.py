from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .links import repo_markdown_paths, validate_markdown_links
from .metadata import (
    ALLOWED_AUDIENCES,
    ALLOWED_DOC_TYPES,
    Document,
    expected_audience,
    expected_doc_type,
    frontmatter_text,
    parse_frontmatter,
    validate_frontmatter,
)
from .state import AGENTS_ROOT, DOCS_ROOT, REPO_ROOT, relative_path

SYNCED_SECTIONS = ("concepts", "guides", "reference", "status", "standards")
RETIRED_REFERENCES = (
    "docs/file-map.md",
    "docs/architecture/README.md",
    "docs/operations/README.md",
    "docs/reference/README.md",
    "docs/operations/ai-session-prompt.md",
)
PREFERRED_SECTION_ORDER: dict[str, tuple[str, ...]] = {
    "concepts": (
        "concepts/architecture-overview.md",
        "concepts/reconciliation-tax-architecture.md",
        "concepts/oracle-boundaries.md",
        "concepts/transaction-classification.md",
        "concepts/workspace-model.md",
    ),
    "guides": (
        "guides/operator-quickstart.md",
        "guides/source-intake.md",
        "guides/normalize-screen-stage.md",
        "guides/verify-a-round.md",
        "guides/full-operator-workflow.md",
        "guides/write-an-adapter.md",
    ),
    "reference": (
        "reference/baseline-validation-contract.md",
        "reference/export-checklist.md",
        "reference/wallet-inventory-artifacts.md",
        "reference/timezone-validation-artifacts.md",
        "reference/canadian-crypto-tax-guide.md",
        "reference/tax-source-map.md",
        "reference/cointracking-oracle-artifacts.md",
    ),
    "status": (
        "status/current-state.md",
        "status/migration-sequence.md",
    ),
    "standards": (
        "standards/engineering.md",
        "standards/implementation.md",
        "standards/commits.md",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold and sync repo documentation metadata.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser("scaffold", help="Create a new doc with standard frontmatter.")
    scaffold.add_argument(
        "--section",
        choices=("concepts", "guides", "reference", "standards", "status", "agents"),
        help="Target section when using repo-standard placement.",
    )
    scaffold.add_argument("--slug", help="Kebab-case filename without the .md suffix.")
    scaffold.add_argument(
        "--path",
        help="Explicit repo-relative output path. Use this for docs/workspace/... mirror docs.",
    )
    scaffold.add_argument("--title", required=True, help="Document title.")
    scaffold.add_argument("--summary", required=True, help="One-sentence document summary.")
    scaffold.add_argument(
        "--doc-type",
        choices=tuple(sorted(ALLOWED_DOC_TYPES)),
        help="Explicit doc_type. Defaults from the section or path.",
    )
    scaffold.add_argument(
        "--audience",
        choices=tuple(sorted(ALLOWED_AUDIENCES)),
        help="Explicit audience. Defaults from the section or path.",
    )

    sync = subparsers.add_parser("sync", help="Validate docs metadata and refresh generated docs index sections.")
    sync.add_argument("--check", action="store_true", help="Fail instead of writing files when sync is needed.")

    return parser


def collect_documents() -> list[Document]:
    paths = sorted(DOCS_ROOT.rglob("*.md")) + sorted(AGENTS_ROOT.rglob("*.md"))
    documents: list[Document] = []
    for path in paths:
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"), path)
        validate_frontmatter(path, frontmatter)
        documents.append(
            Document(
                path=path,
                relative_path=relative_path(path),
                frontmatter=frontmatter,
            )
        )
    return documents


def validate_documents() -> list[Document]:
    return collect_documents()


def section_documents(documents: list[Document], section: str) -> list[Document]:
    prefix = f"docs/{section}/"
    matches = [document for document in documents if document.relative_path.startswith(prefix)]
    preferred = PREFERRED_SECTION_ORDER.get(section, ())
    preferred_index = {path: index for index, path in enumerate(preferred)}
    return sorted(
        matches,
        key=lambda document: (
            preferred_index.get(document.relative_path.removeprefix("docs/"), len(preferred)),
            frontmatter_text(document.frontmatter, "title", document.path).lower(),
        ),
    )


def render_section(documents: list[Document]) -> str:
    lines = [
        (
            f"- [{frontmatter_text(document.frontmatter, 'title', document.path)}]"
            f"({document.relative_path.removeprefix('docs/')}): "
            f"{frontmatter_text(document.frontmatter, 'summary', document.path)}"
        )
        for document in documents
    ]
    return "\n".join(lines)


def replace_marker_block(text: str, marker: str, replacement: str) -> str:
    start_marker = f"<!-- docs-maintenance:start {marker} -->"
    end_marker = f"<!-- docs-maintenance:end {marker} -->"
    pattern = re.compile(
        rf"{re.escape(start_marker)}\n.*?\n{re.escape(end_marker)}",
        re.DOTALL,
    )
    new_block = f"{start_marker}\n{replacement}\n{end_marker}"
    if not pattern.search(text):
        raise ValueError(f"docs/README.md is missing marker block {marker!r}")
    return pattern.sub(new_block, text, count=1)


def check_retired_references() -> None:
    for path in repo_markdown_paths():
        text = path.read_text(encoding="utf-8")
        for reference in RETIRED_REFERENCES:
            if reference in text:
                raise ValueError(f"{path} still references retired path {reference}")


def sync_docs_homepage(documents: list[Document], *, check: bool) -> bool:
    docs_readme = DOCS_ROOT / "README.md"
    original = docs_readme.read_text(encoding="utf-8")
    updated = original
    for marker in SYNCED_SECTIONS:
        updated = replace_marker_block(updated, marker, render_section(section_documents(documents, marker)))

    if updated == original:
        return False
    if check:
        raise ValueError("docs/README.md needs generated-section updates")
    docs_readme.write_text(updated, encoding="utf-8")
    return True


def default_doc_type(path: Path, section: str | None) -> str:
    expected = expected_doc_type(path)
    if expected is not None:
        return expected
    if section == "agents":
        return "reference"
    raise ValueError("Provide --doc-type when the path does not map to a known docs section")


def default_audience(path: Path, section: str | None) -> str:
    expected = expected_audience(path)
    if expected is not None:
        return expected
    if section == "agents":
        return "agent"
    raise ValueError("Provide --audience when the path does not map to a known docs section")


def scaffold_path(*, section: str | None, slug: str | None, path_argument: str | None) -> Path:
    if path_argument is not None:
        path = REPO_ROOT / path_argument
    elif section is not None and slug is not None:
        path = AGENTS_ROOT / f"{slug}.md" if section == "agents" else DOCS_ROOT / section / f"{slug}.md"
    else:
        raise ValueError("Provide either --path or both --section and --slug")
    if path.suffix != ".md":
        raise ValueError("Scaffolded docs must use the .md extension")
    return path


def starter_body(doc_type: str, title: str) -> str:
    if doc_type == "concept":
        return f"This document explains {title.lower()}.\n\n## Overview\n\n## Key Constraints\n"
    if doc_type == "guide":
        return f"Use this guide when you need to work on {title.lower()}.\n\n## Steps\n"
    if doc_type == "reference":
        return f"This reference captures the current contract for {title.lower()}.\n\n## Reference\n"
    if doc_type == "standard":
        return f"Use this standard when making decisions about {title.lower()}.\n\n## Rules\n"
    return f"This status page summarizes the current state of {title.lower()}.\n\n## Current State\n"


def write_scaffold(args: argparse.Namespace) -> int:
    path = scaffold_path(section=args.section, slug=args.slug, path_argument=args.path)
    if path.exists():
        raise ValueError(f"{path} already exists")

    doc_type = args.doc_type or default_doc_type(path, args.section)
    audience = args.audience or default_audience(path, args.section)
    frontmatter = (
        "---\n"
        f'title: "{args.title}"\n'
        f'summary: "{args.summary}"\n'
        f"doc_type: {doc_type}\n"
        f"audience: {audience}\n"
        "owner: repo\n"
        "status: active\n"
        "---\n\n"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter + starter_body(doc_type, args.title), encoding="utf-8")
    print(relative_path(path))

    sync_prefixes = (
        "docs/concepts/",
        "docs/guides/",
        "docs/reference/",
        "docs/status/",
        "docs/standards/",
    )
    if relative_path(path).startswith(sync_prefixes):
        documents = collect_documents()
        sync_docs_homepage(documents, check=False)
    return 0


def run_sync(*, check: bool) -> int:
    documents = collect_documents()
    validate_markdown_links(repo_markdown_paths())
    check_retired_references()
    sync_docs_homepage(documents, check=check)
    print("docs maintenance sync passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scaffold":
            return write_scaffold(args)
        if args.command == "sync":
            return run_sync(check=args.check)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    raise AssertionError(f"unexpected command: {args.command}")
