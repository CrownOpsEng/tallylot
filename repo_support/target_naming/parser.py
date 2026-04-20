from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .model import (
    BlockKind,
    DocumentModel,
    Heading,
    MarkerBlock,
    MarkerLabel,
    SourceSpan,
    Table,
    TableCell,
    TableRow,
    TextBlock,
)
from .scope import parse_frontmatter, repo_relative_path, resolve_naming_scope

NORMALIZED_WHITESPACE_PATTERN = re.compile(r"\s+")
MARKER_PATTERN = re.compile(
    r"^\*\*(Contract-local example|Compatibility-only locality|Current runtime note|"
    r"Anti-example|Exception rationale|Migration-only root rationale|"
    r"Locality rule):\*\*"
)
MARKDOWN_PARSER = MarkdownIt("commonmark").enable("table")


def normalize_text(text: str) -> str:
    return NORMALIZED_WHITESPACE_PATTERN.sub(" ", text.casefold()).strip()


def parse_document(
    path: Path,
    *,
    text: str | None = None,
    root_file_scopes: Mapping[str, str] | None = None,
) -> DocumentModel:
    relative_path = repo_relative_path(path)
    raw_text = text if text is not None else path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(raw_text)
    scope_resolution = resolve_naming_scope(
        relative_path,
        text=raw_text,
        frontmatter=frontmatter,
        root_file_scopes=root_file_scopes,
    )
    body_text = _strip_frontmatter(raw_text)
    tokens = MARKDOWN_PARSER.parse(body_text)
    headings = _parse_headings(tokens)
    text_blocks = _parse_text_blocks(tokens, headings)
    tables = _parse_tables(tokens, headings)
    markers = _parse_markers(text_blocks, tables)
    title = frontmatter.get("title")
    summary = frontmatter.get("summary")
    return DocumentModel(
        path=relative_path,
        scope=scope_resolution.scope,
        frontmatter=frontmatter,
        title=title if isinstance(title, str) else None,
        summary=summary if isinstance(summary, str) else None,
        raw_text=raw_text,
        headings=headings,
        text_blocks=text_blocks,
        markers=markers,
        tables=tables,
    )


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        marker = "\n---\n"
        _, separator, remainder = text.partition(marker)
        if separator:
            return remainder
    return text


def _parse_headings(tokens: Sequence[Token]) -> tuple[Heading, ...]:
    headings: list[Heading] = []
    section_stack: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open" and index + 1 < len(tokens):
            inline_token = tokens[index + 1]
            level = int(token.tag.removeprefix("h"))
            title = inline_token.content.strip()
            while len(section_stack) >= level:
                section_stack.pop()
            section_stack.append(title)
            headings.append(
                Heading(
                    level=level,
                    title=title,
                    normalized_title=normalize_text(title),
                    span=_token_span(token, inline_token.content),
                    section_path=tuple(section_stack),
                )
            )
        index += 1
    return tuple(headings)


def _parse_text_blocks(
    tokens: Sequence[Token],
    headings: tuple[Heading, ...],
) -> tuple[TextBlock, ...]:
    text_blocks: list[TextBlock] = []
    parent_kind: str | None = None
    for token in tokens:
        if token.type in {"paragraph_open", "heading_open", "list_item_open", "fence"}:
            parent_kind = token.type
            if token.type == "fence":
                text_blocks.append(
                    TextBlock(
                        kind="fence",
                        text=token.content,
                        normalized_text=normalize_text(token.content),
                        span=_token_span(token, token.content),
                        section_path=_section_path_for_line(
                            headings, _start_line(token)
                        ),
                    )
                )
            continue

        if token.type == "inline":
            section_path = _section_path_for_line(headings, _start_line(token))
            block_kind = _inline_block_kind(parent_kind)
            if block_kind is not None and token.content.strip():
                text_blocks.append(
                    TextBlock(
                        kind=block_kind,
                        text=token.content,
                        normalized_text=normalize_text(token.content),
                        span=_token_span(token, token.content),
                        section_path=section_path,
                    )
                )
            if token.children:
                for child in token.children:
                    if child.type != "code_inline":
                        continue
                    text_blocks.append(
                        TextBlock(
                            kind="inline_code",
                            text=child.content,
                            normalized_text=normalize_text(child.content),
                            span=_child_span(token, child.content),
                            section_path=section_path,
                        )
                    )
            continue

        if token.type in {"paragraph_close", "heading_close", "list_item_close"}:
            parent_kind = None
    return tuple(text_blocks)


def _parse_tables(
    tokens: Sequence[Token],
    headings: tuple[Heading, ...],
) -> tuple[Table, ...]:
    tables: list[Table] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type != "table_open":
            index += 1
            continue
        table_start = token
        header_row: TableRow | None = None
        body_rows: list[TableRow] = []
        current_cells: list[TableCell] = []
        row_start_line = _start_line(token)
        in_header = False
        index += 1
        while index < len(tokens) and tokens[index].type != "table_close":
            current = tokens[index]
            if current.type == "thead_open":
                in_header = True
            elif current.type == "tbody_open":
                in_header = False
            elif current.type == "tr_open":
                current_cells = []
                row_start_line = _start_line(current)
            elif current.type == "inline":
                current_cells.append(
                    TableCell(
                        text=current.content,
                        normalized_text=normalize_text(current.content),
                        span=_token_span(current, current.content),
                    )
                )
            elif current.type == "tr_close":
                row_span = SourceSpan(
                    line=row_start_line,
                    column=1,
                    end_line=current.map[1] if current.map else row_start_line,
                    end_column=1,
                )
                row = TableRow(cells=tuple(current_cells), span=row_span)
                if in_header and header_row is None:
                    header_row = row
                else:
                    body_rows.append(row)
            index += 1

        if header_row is not None:
            section_path = _section_path_for_line(headings, _start_line(table_start))
            table_close = tokens[index]
            tables.append(
                Table(
                    header=header_row,
                    rows=tuple(body_rows),
                    span=SourceSpan(
                        line=_start_line(table_start),
                        column=1,
                        end_line=table_close.map[1]
                        if table_close.map
                        else _start_line(table_start),
                        end_column=1,
                    ),
                    section_path=section_path,
                )
            )
        index += 1
    return tuple(tables)


def _parse_markers(
    text_blocks: tuple[TextBlock, ...],
    tables: tuple[Table, ...],
) -> tuple[MarkerBlock, ...]:
    markers: list[MarkerBlock] = []
    candidate_blocks = [
        block for block in text_blocks if block.kind in {"paragraph", "list_item"}
    ]
    for block in candidate_blocks:
        match = MARKER_PATTERN.match(block.text.strip())
        if match is None:
            continue
        governed_span = _governed_marker_span(
            block=block,
            candidate_blocks=candidate_blocks,
            tables=tables,
        )
        markers.append(
            MarkerBlock(
                label=cast(MarkerLabel, match.group(1)),
                text=block.text,
                span=block.span,
                governed_span=governed_span,
                section_path=block.section_path,
            )
        )
    return tuple(markers)


def _inline_block_kind(parent_kind: str | None) -> BlockKind | None:
    if parent_kind == "paragraph_open":
        return "paragraph"
    if parent_kind == "heading_open":
        return "heading"
    if parent_kind == "list_item_open":
        return "list_item"
    return None


def _section_path_for_line(
    headings: tuple[Heading, ...],
    line: int,
) -> tuple[str, ...]:
    current: tuple[str, ...] = ()
    for heading in headings:
        if heading.span.line > line:
            break
        current = heading.section_path
    return current


def _start_line(token: Token) -> int:
    return (token.map[0] + 1) if token.map else 1


def _token_span(token: Token, content: str) -> SourceSpan:
    line = _start_line(token)
    end_line = token.map[1] if token.map else line
    end_column = max(1, len(content.splitlines()[-1]) + 1 if content else 1)
    return SourceSpan(
        line=line,
        column=1,
        end_line=end_line,
        end_column=end_column,
    )


def _child_span(token: Token, content: str) -> SourceSpan:
    span = _token_span(token, content)
    return SourceSpan(
        line=span.line,
        column=1,
        end_line=span.line,
        end_column=max(1, len(content) + 1),
    )


def _governed_marker_span(
    *,
    block: TextBlock,
    candidate_blocks: list[TextBlock],
    tables: tuple[Table, ...],
) -> SourceSpan:
    section_end_line = _section_end_line(block.section_path, candidate_blocks, tables)
    return SourceSpan(
        line=block.span.line,
        column=block.span.column,
        end_line=section_end_line,
        end_column=1,
    )


def _section_end_line(
    section_path: tuple[str, ...],
    blocks: list[TextBlock],
    tables: tuple[Table, ...],
) -> int:
    end_line = 1
    for block in blocks:
        if block.section_path[: len(section_path)] == section_path:
            end_line = max(end_line, block.span.end_line)
    for table in tables:
        if table.section_path[: len(section_path)] == section_path:
            end_line = max(end_line, table.span.end_line)
    return end_line
