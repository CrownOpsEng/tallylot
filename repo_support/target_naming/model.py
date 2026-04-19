from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NamingScope = Literal[
    "forward_target",
    "repo_policy",
    "current_state",
    "bridge_local",
    "oracle_local",
    "adapter_local",
    "workspace_reference",
]
Severity = Literal["error", "warning"]
BlockKind = Literal[
    "heading",
    "paragraph",
    "list_item",
    "table_cell",
    "inline_code",
    "fence",
]
MarkerLabel = Literal[
    "Contract-local example",
    "Compatibility-only locality",
    "Current runtime note",
    "Anti-example",
    "Exception rationale",
    "Migration-only root rationale",
    "Locality rule",
]


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class TextBlock:
    kind: BlockKind
    text: str
    normalized_text: str
    span: SourceSpan
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    normalized_title: str
    span: SourceSpan
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class MarkerBlock:
    label: MarkerLabel
    text: str
    span: SourceSpan
    governed_span: SourceSpan
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class TableCell:
    text: str
    normalized_text: str
    span: SourceSpan


@dataclass(frozen=True)
class TableRow:
    cells: tuple[TableCell, ...]
    span: SourceSpan


@dataclass(frozen=True)
class Table:
    header: TableRow
    rows: tuple[TableRow, ...]
    span: SourceSpan
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class DocumentModel:
    path: str
    scope: NamingScope | None
    frontmatter: dict[str, object]
    title: str | None
    summary: str | None
    raw_text: str
    headings: tuple[Heading, ...]
    text_blocks: tuple[TextBlock, ...]
    markers: tuple[MarkerBlock, ...]
    tables: tuple[Table, ...]


@dataclass(frozen=True)
class NamingFinding:
    rule_id: str
    severity: Severity
    path: str
    line: int
    column: int
    scope: NamingScope | None
    message: str
    suggestion: str
    exception_id: str | None = None


@dataclass(frozen=True)
class AuditReport:
    requested_paths: tuple[str, ...]
    evaluated_paths: tuple[str, ...]
    findings: tuple[NamingFinding, ...]
    skipped_paths: tuple[str, ...]
    full_repo: bool
