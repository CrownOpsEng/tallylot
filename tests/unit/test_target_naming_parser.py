from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from repo_support.paths import override_repo_root
from repo_support.target_naming import parse_document


def _write_doc(root: Path, relative_path: str, text: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_document_extracts_frontmatter_blocks_and_table(tmp_path: Path) -> None:
    path = _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Example summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            ## Overview

            Paragraph with `inline_code`.

            | Column | Value |
            | --- | --- |
            | Term | `activity_label` |

            ```python
            activity_label = "bridge-local"
            ```
            """
        ),
    )

    with override_repo_root(tmp_path):
        document = parse_document(path, root_file_scopes={})

    assert document.title == "Example"
    assert document.summary == "Example summary."
    assert document.scope == "forward_target"
    assert [heading.title for heading in document.headings] == ["Overview"]
    assert [block.kind for block in document.text_blocks] == [
        "heading",
        "paragraph",
        "inline_code",
        "inline_code",
        "fence",
    ]
    assert len(document.tables) == 1
    assert tuple(cell.text for cell in document.tables[0].header.cells) == (
        "Column",
        "Value",
    )


def test_marker_governed_span_covers_nested_subsections(tmp_path: Path) -> None:
    path = _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Example summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            ## Bridge Rules

            **Locality rule:** Retain bridge-only naming inside this section.

            ### Nested Detail

            Nested prose with `activity_label`.
            """
        ),
    )

    with override_repo_root(tmp_path):
        document = parse_document(path, root_file_scopes={})

    assert len(document.markers) == 1
    marker = document.markers[0]
    nested_block = next(
        block
        for block in document.text_blocks
        if block.kind == "paragraph" and "activity_label" in block.text
    )
    assert marker.label == "Locality rule"
    assert marker.section_path == ("Bridge Rules",)
    assert marker.governed_span.end_line >= nested_block.span.end_line
