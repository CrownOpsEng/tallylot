from pathlib import Path
from typing import TYPE_CHECKING

from . import state
from .cli import (
    RETIRED_REFERENCES,
    build_parser,
    collect_documents,
    default_audience,
    default_doc_type,
    main,
    run_sync,
    scaffold_path,
    section_documents,
    sync_docs_homepage,
    validate_documents,
    validate_nav_order_uniqueness,
    write_scaffold,
)
from .links import (
    bare_uv_examples,
    repo_markdown_paths,
    validate_markdown_links,
    validate_uv_examples,
)
from .metadata import (
    Document,
    parse_frontmatter,
    validate_frontmatter,
    validate_related_target,
)


def __getattr__(name: str) -> object:
    if name == "REPO_ROOT":
        return state.repo_root()
    if name == "DOCS_ROOT":
        return state.docs_root()
    if name == "AGENTS_ROOT":
        return state.agents_root()
    raise AttributeError(name)


if TYPE_CHECKING:
    REPO_ROOT: Path
    DOCS_ROOT: Path
    AGENTS_ROOT: Path


__all__ = [
    "AGENTS_ROOT",
    "DOCS_ROOT",
    "REPO_ROOT",
    "RETIRED_REFERENCES",
    "Document",
    "bare_uv_examples",
    "build_parser",
    "collect_documents",
    "default_audience",
    "default_doc_type",
    "main",
    "parse_frontmatter",
    "repo_markdown_paths",
    "run_sync",
    "scaffold_path",
    "section_documents",
    "sync_docs_homepage",
    "validate_documents",
    "validate_frontmatter",
    "validate_markdown_links",
    "validate_nav_order_uniqueness",
    "validate_related_target",
    "validate_uv_examples",
    "write_scaffold",
]
