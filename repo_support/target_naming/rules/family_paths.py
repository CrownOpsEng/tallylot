from __future__ import annotations

import re

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, TextBlock
from ._common import block_is_covered_by_marker, build_finding

PATH_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?:[A-Za-z0-9_.-]+/)+(?:[A-Za-z0-9_.-]+/?)?"
    r"(?![A-Za-z0-9_./-])"
)


def family_path_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if document.scope not in {"forward_target", "repo_policy"}:
        return ()
    controlled_prefixes = _controlled_prefixes(catalog)
    canonical_exact = {
        *catalog.canonical_families.package_paths,
        *catalog.canonical_families.directory_paths,
        *catalog.canonical_families.sidecar_paths,
    }
    findings: list[NamingFinding] = []
    for block in document.text_blocks:
        if block.kind != "inline_code":
            continue
        scope_profile = catalog.scope_profiles.get(document.scope)
        if (
            scope_profile is not None
            and scope_profile.allow_anti_examples
            and block_is_covered_by_marker(document, block, "Anti-example")
        ):
            continue
        findings.extend(
            _block_findings(
                document=document,
                block=block,
                canonical_exact=canonical_exact,
                controlled_prefixes=controlled_prefixes,
            )
        )
    return tuple(findings)


def _block_findings(
    *,
    document: DocumentModel,
    block: TextBlock,
    canonical_exact: set[str],
    controlled_prefixes: tuple[str, ...],
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for token in PATH_TOKEN_PATTERN.findall(block.text):
        if not _is_controlled_path_candidate(
            token,
            controlled_prefixes=controlled_prefixes,
        ):
            continue
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


def _controlled_prefixes(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    package_roots = {
        f"{path.split('/', maxsplit=1)[0]}/"
        for path in catalog.canonical_families.package_paths
    }
    group_roots = {
        f"{group.root}/" for group in catalog.canonical_families.directory_groups
    }
    standalone_roots = set(catalog.canonical_families.standalone_directory_paths)
    return tuple(
        sorted(
            package_roots | group_roots | standalone_roots,
            key=len,
            reverse=True,
        )
    )


def _is_controlled_path_candidate(
    token: str,
    *,
    controlled_prefixes: tuple[str, ...],
) -> bool:
    for prefix in controlled_prefixes:
        if not token.startswith(prefix):
            continue
        if token == prefix and prefix != "compatibility/":
            return False
        return True
    return False
