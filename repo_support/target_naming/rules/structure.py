from __future__ import annotations

import re

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, SourceSpan
from ._common import block_is_covered_by_marker, build_finding

SUPPORT_PATH_PATTERN = re.compile(r"\bsupport/([a-z0-9_.-]+(?:/[a-z0-9_.-]+)*)\b")


def structure_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog | None = None,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    if (
        document.path.startswith("docs/")
        and document.path.endswith(".md")
        and document.scope is None
    ):
        findings.append(
            build_finding(
                rule_id="structure.missing_naming_scope",
                document=document,
                span=document.headings[0].span
                if document.headings
                else _line_one_span(),
                message="repo docs must declare naming_scope in frontmatter",
                suggestion=(
                    "add naming_scope with one of: forward_target, repo_policy, "
                    "current_state, bridge_local, oracle_local, adapter_local, "
                    "workspace_reference"
                ),
            )
        )
    if catalog is None:
        return tuple(findings)

    for block in document.text_blocks:
        if block.kind != "inline_code":
            continue
        scope_profile = (
            catalog.scope_profiles.get(document.scope)
            if document.scope is not None
            else None
        )
        if (
            scope_profile is not None
            and scope_profile.allow_anti_examples
            and block_is_covered_by_marker(document, block, "Anti-example")
        ):
            continue
        for match in SUPPORT_PATH_PATTERN.finditer(block.text):
            findings.append(
                build_finding(
                    rule_id="structure.flat_support_path",
                    document=document,
                    span=block.span,
                    message=f"support-root path {match.group(0)!r} is not allowed",
                    suggestion=(
                        "use assessment/gap/, assessment/review/, or "
                        "assessment/readiness/ "
                        "with a mirrored family basename"
                    ),
                )
            )
    return tuple(findings)


def _line_one_span() -> SourceSpan:
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
