from __future__ import annotations

from ..catalog import ScopeProfile, TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, TextBlock
from ._common import block_is_covered_by_marker, build_finding, find_phrase_column


def body_phrase_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
    scope_profile: ScopeProfile,
) -> tuple[NamingFinding, ...]:
    if document.scope is None:
        return ()
    findings: list[NamingFinding] = []
    for block in document.text_blocks:
        if block.kind in {"inline_code", "fence"}:
            continue
        if scope_profile.allow_anti_examples and block_is_covered_by_marker(
            document, block, "Anti-example"
        ):
            continue
        findings.extend(_phrase_findings_for_block(document, block, catalog))
        findings.extend(_alias_findings_for_block(document, block, catalog))
    for block in document.text_blocks:
        if block.kind != "inline_code":
            continue
        if scope_profile.allow_anti_examples and block_is_covered_by_marker(
            document, block, "Anti-example"
        ):
            continue
        findings.extend(_alias_findings_for_block(document, block, catalog))
    return tuple(findings)


def _phrase_findings_for_block(
    document: DocumentModel,
    block: TextBlock,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for rule in catalog.banned_phrases:
        if "body" not in rule.contexts or document.scope not in rule.allowed_scopes:
            continue
        if rule.paths and document.path not in rule.paths:
            continue
        column = find_phrase_column(block.text, rule.term, case_sensitive=False)
        if column is None:
            continue
        findings.append(
            build_finding(
                rule_id=rule.rule_id,
                document=document,
                span=block.span,
                message=f"retired phrase {rule.term!r} is not allowed in governed prose",
                suggestion="rewrite the prose using the canonical contract wording",
            )
        )
    return tuple(findings)


def _alias_findings_for_block(
    document: DocumentModel,
    block: TextBlock,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    contexts = {"body"} if block.kind != "inline_code" else {"inline_code", "body"}
    for rule in catalog.retired_aliases:
        if document.scope not in rule.allowed_scopes:
            continue
        if rule.paths and document.path not in rule.paths:
            continue
        if document.path in rule.allowed_paths:
            continue
        if not contexts.intersection(rule.contexts):
            continue
        column = find_phrase_column(block.text, rule.term, case_sensitive=True)
        if column is None:
            continue
        findings.append(
            build_finding(
                rule_id=rule.rule_id,
                document=document,
                span=block.span,
                message=f"retired term {rule.term!r} is not allowed here",
                suggestion=f"use {rule.replacement!r} instead",
            )
        )
    return tuple(findings)
