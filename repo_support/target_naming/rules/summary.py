from __future__ import annotations

import re
from typing import cast

from ..catalog import AliasRule, PhraseRule, TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, NamingScope, SourceSpan
from ._common import build_finding, find_phrase_column


def summary_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if document.summary is None or document.scope is None:
        return ()
    summary_span = _summary_span(document)
    findings: list[NamingFinding] = []
    for phrase_rule in catalog.banned_phrases:
        if "summary" not in phrase_rule.contexts or not _phrase_rule_applies(
            phrase_rule, document
        ):
            continue
        column = find_phrase_column(
            document.summary, phrase_rule.term, case_sensitive=False
        )
        if column is None:
            continue
        findings.append(
            build_finding(
                rule_id=phrase_rule.rule_id,
                document=document,
                span=SourceSpan(
                    line=summary_span.line,
                    column=column,
                    end_line=summary_span.line,
                    end_column=column + len(phrase_rule.term),
                ),
                message=f"summary must not use {phrase_rule.term!r}",
                suggestion="rewrite the summary in content-first target terminology",
            )
        )
    for alias_rule in catalog.retired_aliases:
        if "summary" not in alias_rule.contexts or not _alias_rule_applies(
            alias_rule, document
        ):
            continue
        column = find_phrase_column(
            document.summary, alias_rule.term, case_sensitive=True
        )
        if column is None:
            continue
        findings.append(
            build_finding(
                rule_id=alias_rule.rule_id,
                document=document,
                span=SourceSpan(
                    line=summary_span.line,
                    column=column,
                    end_line=summary_span.line,
                    end_column=column + len(alias_rule.term),
                ),
                message=f"summary uses retired alias {alias_rule.term!r}",
                suggestion=f"use {alias_rule.replacement!r} instead",
            )
        )
    return tuple(findings)


def validate_summary_text(
    path: str,
    summary: str,
    *,
    scope: str | None,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if scope is None:
        return ()
    document = DocumentModel(
        path=path,
        scope=cast(NamingScope, scope),
        frontmatter={},
        title=None,
        summary=summary,
        raw_text=f"summary: {summary}\n",
        headings=(),
        text_blocks=(),
        markers=(),
        tables=(),
    )
    return summary_findings(document, catalog)


def _phrase_rule_applies(rule: PhraseRule, document: DocumentModel) -> bool:
    if document.scope not in rule.allowed_scopes:
        return False
    return not rule.paths or document.path in rule.paths


def _alias_rule_applies(rule: AliasRule, document: DocumentModel) -> bool:
    if document.scope not in rule.allowed_scopes:
        return False
    if rule.paths and document.path not in rule.paths:
        return False
    return document.path not in rule.allowed_paths


def _summary_span(document: DocumentModel) -> SourceSpan:
    for line_number, line in enumerate(document.raw_text.splitlines(), start=1):
        if re.match(r"summary:\s", line):
            return SourceSpan(
                line=line_number,
                column=1,
                end_line=line_number,
                end_column=max(1, len(line) + 1),
            )
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
