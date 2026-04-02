from . import state
from .cli import (
    PREFERRED_SECTION_ORDER,
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
    write_scaffold,
)
from .links import repo_markdown_paths, validate_markdown_links
from .metadata import (
    Document,
    parse_frontmatter,
    validate_frontmatter,
)

REPO_ROOT = state.REPO_ROOT
DOCS_ROOT = state.DOCS_ROOT
AGENTS_ROOT = state.AGENTS_ROOT

__all__ = [
    "AGENTS_ROOT",
    "DOCS_ROOT",
    "PREFERRED_SECTION_ORDER",
    "REPO_ROOT",
    "RETIRED_REFERENCES",
    "Document",
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
    "write_scaffold",
]
