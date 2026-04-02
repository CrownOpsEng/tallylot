from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import cast

import yaml

from .links import markdown_target_paths, repo_markdown_paths, validate_markdown_links, validate_uv_examples
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
from .state import agents_root, docs_root, relative_path, repo_root

SYNCED_SECTIONS = ("concepts", "guides", "reference", "status", "standards")
RETIRED_REFERENCES = (
    "docs/file-map.md",
    "docs/architecture/README.md",
    "docs/operations/README.md",
    "docs/reference/README.md",
    "docs/operations/ai-session-prompt.md",
)


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
    scaffold.add_argument(
        "--nav-order",
        type=int,
        help="Optional nav_order for sync-managed human docs.",
    )

    sync = subparsers.add_parser("sync", help="Validate docs metadata and refresh generated docs index sections.")
    sync.add_argument("--check", action="store_true", help="Fail instead of writing files when sync is needed.")

    return parser


def collect_documents() -> list[Document]:
    paths = sorted(docs_root().rglob("*.md")) + sorted(agents_root().rglob("*.md"))
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
    validate_nav_order_uniqueness(documents)
    return documents


def validate_documents() -> list[Document]:
    return collect_documents()


def section_documents(documents: list[Document], section: str) -> list[Document]:
    prefix = f"docs/{section}/"
    matches = [document for document in documents if document.relative_path.startswith(prefix)]
    return sorted(
        matches,
        key=lambda document: (
            document.frontmatter.get("nav_order")
            if isinstance(document.frontmatter.get("nav_order"), int)
            else float("inf"),
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


def validate_nav_order_uniqueness(documents: list[Document]) -> None:
    for section in SYNCED_SECTIONS:
        used: dict[int, str] = {}
        prefix = f"docs/{section}/"
        for document in documents:
            if not document.relative_path.startswith(prefix):
                continue
            nav_order = document.frontmatter.get("nav_order")
            if not isinstance(nav_order, int):
                continue
            previous = used.get(nav_order)
            if previous is not None:
                raise ValueError(
                    f"duplicate nav_order {nav_order} in docs/{section}: {previous} and {document.relative_path}"
                )
            used[nav_order] = document.relative_path


def replace_marker_block(text: str, marker: str, replacement: str) -> str:
    start_marker = f"<!-- docs-maintenance:start {marker} -->"
    end_marker = f"<!-- docs-maintenance:end {marker} -->"
    pattern = re.compile(
        rf"{re.escape(start_marker)}\n(?:.*?\n)?{re.escape(end_marker)}",
        re.DOTALL,
    )
    new_block = f"{start_marker}\n{replacement}\n{end_marker}"
    if not pattern.search(text):
        raise ValueError(f"docs/README.md is missing marker block {marker!r}")
    return pattern.sub(new_block, text, count=1)


def check_retired_references() -> None:
    for path in repo_markdown_paths():
        referenced_paths = set(markdown_target_paths(path))
        if path.suffix == ".md" and path.exists() and relative_path(path).startswith(("docs/", "agents/")):
            frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"), path)
            related = frontmatter.get("related")
            if isinstance(related, list):
                for target in cast(list[object], related):
                    if not isinstance(target, str):
                        continue
                    referenced_paths.add(target.split("#", 1)[0])
        for reference in RETIRED_REFERENCES:
            if reference in referenced_paths:
                raise ValueError(f"{path} still references retired path {reference}")


def sync_docs_homepage(documents: list[Document], *, check: bool) -> bool:
    docs_readme = docs_root() / "README.md"
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
    if section == "agents" or relative_path(path).startswith("agents/"):
        raise ValueError("Provide --doc-type when scaffolding agent docs")
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
        supplied = Path(path_argument)
        if supplied.is_absolute():
            raise ValueError("--path must be repo-relative")
        path = (repo_root() / supplied).resolve()
        try:
            relative_path(path)
        except ValueError as error:
            raise ValueError("--path must stay inside the repo") from error
    elif section is not None and slug is not None:
        path = agents_root() / f"{slug}.md" if section == "agents" else docs_root() / section / f"{slug}.md"
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
    relative = relative_path(path)
    nav_order_allowed = relative.startswith(
        ("docs/concepts/", "docs/guides/", "docs/reference/", "docs/status/", "docs/standards/")
    )
    if args.nav_order is not None and not nav_order_allowed:
        raise ValueError("--nav-order is only valid for sync-managed human docs")
    frontmatter_data: dict[str, object] = {
        "title": args.title,
        "summary": args.summary,
        "doc_type": doc_type,
        "audience": audience,
        "owner": "repo",
        "status": "active",
    }
    if args.nav_order is not None:
        frontmatter_data["nav_order"] = args.nav_order
    frontmatter = f"---\n{yaml.safe_dump(frontmatter_data, sort_keys=False)}---\n\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter + starter_body(doc_type, args.title), encoding="utf-8")

    sync_prefixes = (
        "docs/concepts/",
        "docs/guides/",
        "docs/reference/",
        "docs/status/",
        "docs/standards/",
    )
    try:
        validate_frontmatter(path, parse_frontmatter(path.read_text(encoding="utf-8"), path))
        if relative_path(path).startswith(sync_prefixes):
            documents = collect_documents()
            sync_docs_homepage(documents, check=False)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print(relative)
    return 0


def run_sync(*, check: bool) -> int:
    documents = validate_documents()
    validate_markdown_links(repo_markdown_paths())
    validate_uv_examples(repo_markdown_paths())
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
