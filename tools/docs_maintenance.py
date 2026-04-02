from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
AGENTS_ROOT = REPO_ROOT / "agents"

REQUIRED_FRONTMATTER_FIELDS = (
    "title",
    "summary",
    "doc_type",
    "audience",
    "owner",
    "status",
)
ALLOWED_DOC_TYPES = {"concept", "guide", "reference", "standard", "status"}
ALLOWED_AUDIENCES = {"human", "agent", "both"}
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


@dataclass(frozen=True)
class Document:
    path: Path
    relative_path: str
    frontmatter: dict[str, str]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold and sync repo documentation metadata.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser("scaffold", help="Create a new doc with standard frontmatter.")
    scaffold.add_argument(
        "--section",
        choices=("concepts", "guides", "reference", "standards", "status", "agents"),
        help="Target section when using repo-standard placement.",
    )
    scaffold.add_argument("--slug", help="Kebab-case filename without the .md suffix.")
    scaffold.add_argument("--path", help="Explicit repo-relative output path.")
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


def _parse_frontmatter(text: str, path: Path) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path} is missing frontmatter")
    end_marker = "\n---\n"
    end_index = text.find(end_marker, 4)
    if end_index == -1:
        raise ValueError(f"{path} has unterminated frontmatter")

    raw_lines = text[4:end_index].splitlines()
    frontmatter: dict[str, str] = {}
    for line in raw_lines:
        if not line or line.startswith("  - "):
            continue
        if ":" not in line:
            raise ValueError(f"{path} has malformed frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter


def _relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _expected_doc_type(path: Path) -> str | None:
    relative = _relative_path(path)
    if relative == "docs/README.md":
        return "reference"
    if relative.startswith("docs/workspace/"):
        return "reference"
    if relative.startswith("docs/concepts/"):
        return "concept"
    if relative.startswith("docs/guides/"):
        return "guide"
    if relative.startswith("docs/reference/"):
        return "reference"
    if relative.startswith("docs/standards/"):
        return "standard"
    if relative.startswith("docs/status/"):
        return "status"
    return None


def _expected_audience(path: Path) -> str | None:
    relative = _relative_path(path)
    if relative.startswith("agents/"):
        return "agent"
    if relative.startswith("docs/workspace/"):
        return "both"
    if relative.startswith("docs/"):
        return "human"
    return None


def _validate_frontmatter(path: Path, frontmatter: dict[str, str]) -> None:
    missing = [field for field in REQUIRED_FRONTMATTER_FIELDS if not frontmatter.get(field)]
    if missing:
        raise ValueError(f"{path} is missing frontmatter fields: {', '.join(missing)}")

    doc_type = frontmatter["doc_type"]
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"{path} has invalid doc_type {doc_type!r}")

    audience = frontmatter["audience"]
    if audience not in ALLOWED_AUDIENCES:
        raise ValueError(f"{path} has invalid audience {audience!r}")

    if frontmatter["owner"] != "repo":
        raise ValueError(f"{path} must use owner: repo")

    expected_doc_type = _expected_doc_type(path)
    if expected_doc_type is not None and doc_type != expected_doc_type:
        raise ValueError(f"{path} must use doc_type: {expected_doc_type}")

    expected_audience = _expected_audience(path)
    if expected_audience is not None and audience != expected_audience:
        raise ValueError(f"{path} must use audience: {expected_audience}")


def _collect_documents() -> list[Document]:
    paths = sorted(DOCS_ROOT.rglob("*.md")) + sorted(AGENTS_ROOT.rglob("*.md"))
    documents: list[Document] = []
    for path in paths:
        frontmatter = _parse_frontmatter(path.read_text(encoding="utf-8"), path)
        _validate_frontmatter(path, frontmatter)
        documents.append(Document(path=path, relative_path=_relative_path(path), frontmatter=frontmatter))
    return documents


def _section_documents(documents: list[Document], section: str) -> list[Document]:
    prefix = f"docs/{section}/"
    matches = [document for document in documents if document.relative_path.startswith(prefix)]
    preferred = PREFERRED_SECTION_ORDER.get(section, ())
    preferred_index = {path: index for index, path in enumerate(preferred)}
    return sorted(
        matches,
        key=lambda document: (
            preferred_index.get(document.relative_path.removeprefix("docs/"), len(preferred)),
            document.frontmatter["title"].lower(),
        ),
    )


def _render_section(documents: list[Document]) -> str:
    lines = [
        (
            f"- [{document.frontmatter['title']}]"
            f"({document.relative_path.removeprefix('docs/')}): "
            f"{document.frontmatter['summary']}"
        )
        for document in documents
    ]
    return "\n".join(lines)


def _replace_marker_block(text: str, marker: str, replacement: str) -> str:
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


def _check_retired_references() -> None:
    scan_paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *sorted(DOCS_ROOT.rglob("*.md")),
        *sorted((REPO_ROOT / ".claude").rglob("*.md")),
        *sorted(AGENTS_ROOT.rglob("*.md")),
    ]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8")
        for reference in RETIRED_REFERENCES:
            if reference in text:
                raise ValueError(f"{path} still references retired path {reference}")


def _sync_docs_homepage(documents: list[Document], *, check: bool) -> bool:
    docs_readme = DOCS_ROOT / "README.md"
    original = docs_readme.read_text(encoding="utf-8")
    updated = original
    for marker in SYNCED_SECTIONS:
        updated = _replace_marker_block(updated, marker, _render_section(_section_documents(documents, marker)))

    if updated == original:
        return False
    if check:
        raise ValueError("docs/README.md needs generated-section updates")
    docs_readme.write_text(updated, encoding="utf-8")
    return True


def _default_doc_type(path: Path, section: str | None) -> str:
    expected = _expected_doc_type(path)
    if expected is not None:
        return expected
    if section == "agents":
        return "reference"
    raise ValueError("Provide --doc-type when the path does not map to a known docs section")


def _default_audience(path: Path, section: str | None) -> str:
    expected = _expected_audience(path)
    if expected is not None:
        return expected
    if section == "agents":
        return "agent"
    raise ValueError("Provide --audience when the path does not map to a known docs section")


def _scaffold_path(*, section: str | None, slug: str | None, path_argument: str | None) -> Path:
    if path_argument is not None:
        path = REPO_ROOT / path_argument
    elif section is not None and slug is not None:
        path = AGENTS_ROOT / f"{slug}.md" if section == "agents" else DOCS_ROOT / section / f"{slug}.md"
    else:
        raise ValueError("Provide either --path or both --section and --slug")
    if path.suffix != ".md":
        raise ValueError("Scaffolded docs must use the .md extension")
    return path


def _starter_body(doc_type: str, title: str) -> str:
    if doc_type == "concept":
        return f"This document explains {title.lower()}.\n\n## Overview\n\n## Key Constraints\n"
    if doc_type == "guide":
        return f"Use this guide when you need to work on {title.lower()}.\n\n## Steps\n"
    if doc_type == "reference":
        return f"This reference captures the current contract for {title.lower()}.\n\n## Reference\n"
    if doc_type == "standard":
        return f"Use this standard when making decisions about {title.lower()}.\n\n## Rules\n"
    return f"This status page summarizes the current state of {title.lower()}.\n\n## Current State\n"


def _write_scaffold(args: argparse.Namespace) -> int:
    path = _scaffold_path(section=args.section, slug=args.slug, path_argument=args.path)
    if path.exists():
        raise ValueError(f"{path} already exists")

    doc_type = args.doc_type or _default_doc_type(path, args.section)
    audience = args.audience or _default_audience(path, args.section)
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
    path.write_text(frontmatter + _starter_body(doc_type, args.title), encoding="utf-8")
    print(_relative_path(path))

    sync_prefixes = (
        "docs/concepts/",
        "docs/guides/",
        "docs/reference/",
        "docs/status/",
        "docs/standards/",
    )
    if _relative_path(path).startswith(sync_prefixes):
        documents = _collect_documents()
        _sync_docs_homepage(documents, check=False)
    return 0


def _run_sync(*, check: bool) -> int:
    documents = _collect_documents()
    _check_retired_references()
    _sync_docs_homepage(documents, check=check)
    print("docs maintenance sync passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "scaffold":
            return _write_scaffold(args)
        if args.command == "sync":
            return _run_sync(check=args.check)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
