from __future__ import annotations

import re

from ..catalog import TargetNamingCatalog, VocabularyCheck
from ..model import DocumentModel, NamingFinding, SourceSpan
from ._common import build_finding

NESTED_LIST_PATTERN = re.compile(
    r"^- `(?P<label>[^`]+)`:\n(?P<body>(?:  - `[^`]+`\n)+)",
    re.MULTILINE,
)
HEADING_SHARED_VOCABULARY_PATTERN = re.compile(
    r"^### `(?P<label>[^`]+)`\n\nShared vocabulary:\n\n"
    r"(?P<body>(?:- `[^`]+`\n)+)",
    re.MULTILINE,
)
BODY_VALUE_PATTERN = re.compile(r"- `([^`]+)`")
VOCABULARY_RULE_ID_OVERRIDES = {
    "valuation_purpose": "vocab.axis.valuation_purpose",
    "journal_entry_status": "vocab.axis.journal_entry",
    "tax_output_status": "vocab.axis.tax_output",
    "checkpoint_proposal_status": "vocab.axis.checkpoint_proposal",
    "continuity_segment_status": "vocab.axis.continuity_segment",
}


def vocabulary_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for check in catalog.vocabularies.checks:
        if check.path != document.path:
            continue
        expected_values = (
            check.expected_values
            if check.expected_values
            else catalog.vocabularies.values.get(check.vocabulary, ())
        )
        actual_values, span = _extract_values(document.raw_text, check)
        if actual_values is None or span is None:
            findings.append(
                build_finding(
                    rule_id=f"vocab.block.{check.vocabulary}",
                    document=document,
                    span=SourceSpan(line=1, column=1, end_line=1, end_column=1),
                    message=(
                        f"missing configured vocabulary block for {check.label!r} "
                        f"in {check.path}"
                    ),
                    suggestion="restore the configured vocabulary block shape",
                )
            )
            continue
        if tuple(actual_values) == tuple(expected_values):
            continue
        findings.append(
            build_finding(
                rule_id=_vocabulary_rule_id(check.vocabulary),
                document=document,
                span=span,
                message=(
                    f"{check.label} vocabulary drifted from the catalog; expected "
                    f"{expected_values!r}, found {tuple(actual_values)!r}"
                ),
                suggestion="rewrite the documented vocabulary to match the catalog",
            )
        )
    return tuple(findings)


def vocabulary_rule_ids(catalog: TargetNamingCatalog) -> frozenset[str]:
    rule_ids: set[str] = set()
    for check in catalog.vocabularies.checks:
        rule_ids.add(f"vocab.block.{check.vocabulary}")
        rule_ids.add(_vocabulary_rule_id(check.vocabulary))
    return frozenset(rule_ids)


def _extract_values(
    text: str, check: VocabularyCheck
) -> tuple[tuple[str, ...] | None, SourceSpan | None]:
    if check.block_type == "nested_list":
        matches = [
            match
            for match in NESTED_LIST_PATTERN.finditer(text)
            if match.group("label") == check.label
        ]
    elif check.block_type == "heading_shared_vocabulary":
        matches = [
            match
            for match in HEADING_SHARED_VOCABULARY_PATTERN.finditer(text)
            if match.group("label") == check.label
        ]
    else:
        raise ValueError(f"unsupported vocabulary block type: {check.block_type}")
    if not matches:
        return None, None
    match = matches[0]
    values = tuple(BODY_VALUE_PATTERN.findall(match.group("body")))
    return values, _span_from_offset(text, match.start())


def _span_from_offset(text: str, offset: int) -> SourceSpan:
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset)
    column = offset + 1 if line_start == -1 else offset - line_start
    return SourceSpan(line=line, column=column, end_line=line, end_column=column + 1)


def _vocabulary_rule_id(vocabulary: str) -> str:
    if vocabulary.startswith("balance_target_"):
        return "vocab.axis.balance_target"
    return VOCABULARY_RULE_ID_OVERRIDES.get(vocabulary, f"vocab.axis.{vocabulary}")
