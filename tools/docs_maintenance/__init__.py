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
    write_scaffold,
)
from .links import bare_uv_examples, repo_markdown_paths, validate_markdown_links, validate_uv_examples
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
    "validate_uv_examples",
    "write_scaffold",
]
