from __future__ import annotations

from typing import cast

from repo_support.paths import repo_root

from .catalog import (
    TargetNamingCatalog,
    is_target_naming_tooling_path,
    load_target_naming_catalog,
)
from .model import AuditReport, DocumentModel, NamingFinding, NamingScope
from .parser import parse_document
from .scope import resolve_naming_scope, scope_requires_target_naming
from .rules.locality import locality_findings
from .rules.matrix import matrix_findings
from .rules.phrases import body_phrase_findings
from .rules.structure import structure_findings
from .rules.summary import (
    summary_findings,
    validate_summary_text as validate_summary_text_rules,
)
from .rules.title import title_findings
from .rules.vocabulary import vocabulary_findings


def run_target_naming_audit(
    *,
    paths: tuple[str, ...] | None = None,
    catalog: TargetNamingCatalog | None = None,
) -> AuditReport:
    loaded = catalog or load_target_naming_catalog()
    requested_paths = paths or ()
    full_repo = False
    if paths is None or any(
        is_target_naming_tooling_path(path, catalog=loaded) for path in requested_paths
    ):
        evaluation_paths = _all_docs_and_root_files(loaded)
        full_repo = True
    else:
        evaluation_paths = tuple(
            path
            for path in dict.fromkeys(requested_paths)
            if _is_auditable_markdown_path(path, loaded)
        )

    documents = tuple(_load_document(path, loaded) for path in evaluation_paths)
    findings: list[NamingFinding] = []
    evaluated_paths: list[str] = []
    for document in documents:
        if _document_is_governed(document, loaded):
            findings.extend(_document_findings(document, loaded))
        elif document.path.startswith("docs/") and document.scope is None:
            findings.extend(structure_findings(document))
        evaluated_paths.append(document.path)

    skipped_paths = tuple(
        path
        for path in requested_paths
        if path not in evaluation_paths
        and not is_target_naming_tooling_path(path, catalog=loaded)
    )
    return AuditReport(
        requested_paths=requested_paths,
        evaluated_paths=tuple(evaluated_paths),
        findings=tuple(findings),
        skipped_paths=skipped_paths,
        full_repo=full_repo,
    )


def audit_target_naming(
    catalog: TargetNamingCatalog | None = None,
    paths: tuple[str, ...] | None = None,
) -> tuple[NamingFinding, ...]:
    return run_target_naming_audit(paths=paths, catalog=catalog).findings


def validate_summary_style(
    path: str,
    summary: str,
    *,
    scope: str | None,
    catalog: TargetNamingCatalog | None = None,
) -> tuple[NamingFinding, ...]:
    loaded = catalog or load_target_naming_catalog()
    return validate_summary_text_rules(path, summary, scope=scope, catalog=loaded)


def validate_title_style(
    path: str,
    title: str,
    *,
    scope: str | None,
    catalog: TargetNamingCatalog | None = None,
) -> tuple[NamingFinding, ...]:
    loaded = catalog or load_target_naming_catalog()
    document = DocumentModel(
        path=path,
        scope=cast(NamingScope | None, scope),
        frontmatter={"title": title},
        title=title,
        summary=None,
        raw_text="",
        headings=(),
        text_blocks=(),
        markers=(),
        tables=(),
    )
    return title_findings(document, loaded)


def is_target_naming_sensitive_path(
    path: str,
    *,
    catalog: TargetNamingCatalog | None = None,
) -> bool:
    loaded = catalog or load_target_naming_catalog()
    if is_target_naming_tooling_path(path, catalog=loaded):
        return True
    if path in loaded.root_file_scopes:
        return scope_requires_target_naming(loaded.root_file_scopes[path])
    if not path.startswith("docs/") or not path.endswith(".md"):
        return False
    resolved = resolve_naming_scope(
        path,
        text=(repo_root() / path).read_text(encoding="utf-8")
        if (repo_root() / path).exists()
        else None,
        root_file_scopes=loaded.root_file_scopes,
    )
    return resolved.missing_required_scope or scope_requires_target_naming(
        resolved.scope
    )


def _document_is_governed(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> bool:
    if document.scope is None:
        return False
    profile = catalog.scope_profiles.get(document.scope)
    return profile.enforce_target_naming if profile is not None else False


def _document_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    profile = catalog.scope_profiles[cast(NamingScope, document.scope)]
    findings: list[NamingFinding] = []
    findings.extend(title_findings(document, catalog))
    findings.extend(structure_findings(document, catalog))
    findings.extend(summary_findings(document, catalog))
    findings.extend(body_phrase_findings(document, catalog, profile))
    findings.extend(vocabulary_findings(document, catalog))
    findings.extend(matrix_findings(document, catalog))
    findings.extend(locality_findings(document, catalog))
    return tuple(findings)


def _all_docs_and_root_files(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    docs_paths = sorted(
        path.relative_to(repo_root()).as_posix()
        for path in repo_root().joinpath("docs").rglob("*.md")
    )
    root_paths = sorted(catalog.root_file_scopes)
    return tuple(dict.fromkeys((*docs_paths, *root_paths)))


def _is_auditable_markdown_path(path: str, catalog: TargetNamingCatalog) -> bool:
    return (
        path.startswith("docs/") and path.endswith(".md")
    ) or path in catalog.root_file_scopes


def _load_document(path: str, catalog: TargetNamingCatalog) -> DocumentModel:
    return parse_document(repo_root() / path, root_file_scopes=catalog.root_file_scopes)
