from __future__ import annotations

import re

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding
from ._common import block_is_covered_by_marker, build_finding

SUPPORT_PATH_PATTERN = re.compile(r"\bsupport/([a-z0-9_.-]+(?:/[a-z0-9_.-]+)*)\b")


def structure_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog | None = None,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
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
                        "use assessment/gap/ or assessment/review/ with a "
                        "mirrored family basename"
                    ),
                )
            )
    return tuple(findings)
