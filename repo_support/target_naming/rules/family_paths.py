from __future__ import annotations

import re

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, TextBlock
from ._common import build_finding

CONTROLLED_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?:application|domain|assessment|support|working/products)/[A-Za-z0-9_./-]+"
    r"(?![A-Za-z0-9_./-])"
)


def family_path_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if document.scope != "forward_target":
        return ()
    canonical_exact = {
        *catalog.canonical_families.package_paths,
        *catalog.canonical_families.directory_paths,
        *catalog.canonical_families.sidecar_paths,
    }
    findings: list[NamingFinding] = []
    for block in document.text_blocks:
        if block.kind != "inline_code":
            continue
        findings.extend(
            _block_findings(
                document=document,
                block=block,
                canonical_exact=canonical_exact,
            )
        )
    return tuple(findings)


def _block_findings(
    *,
    document: DocumentModel,
    block: TextBlock,
    canonical_exact: set[str],
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for match in CONTROLLED_PATH_PATTERN.finditer(block.text):
        token = match.group(0)
        if token in canonical_exact:
            continue
        findings.append(
            build_finding(
                rule_id="family.path.canonical",
                document=document,
                span=block.span,
                message=f"path {token!r} is not a canonical target family path",
                suggestion=(
                    "use the catalog-approved assessment, package, or sidecar path "
                    "family instead"
                ),
            )
        )
    return tuple(findings)
