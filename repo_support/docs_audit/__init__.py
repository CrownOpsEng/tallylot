from __future__ import annotations

from .catalog import ALL_RULES
from .model import DocsAuditFinding, DocsAuditReport
from .surfaces import is_docs_audit_substrate_path


def run_docs_audit(paths: tuple[str, ...] | None = None) -> DocsAuditReport:
    requested_paths = paths or ()
    full_repo = paths is None or any(
        is_docs_audit_substrate_path(path) for path in requested_paths
    )
    evaluated_rule_ids: list[str] = []
    findings: list[DocsAuditFinding] = []
    evaluated_paths: list[str] = []
    if full_repo:
        for rule in ALL_RULES:
            evaluated_rule_ids.append(rule.rule_id)
            rule_findings = rule.run()
            findings.extend(rule_findings)
            evaluated_paths.extend(finding.path for finding in rule_findings)
    return DocsAuditReport(
        requested_paths=requested_paths,
        evaluated_rule_ids=tuple(evaluated_rule_ids),
        findings=tuple(findings),
        full_repo=full_repo,
        evaluated_paths=tuple(dict.fromkeys(evaluated_paths)),
    )


def audit_docs(paths: tuple[str, ...] | None = None) -> tuple[DocsAuditFinding, ...]:
    return run_docs_audit(paths=paths).findings


__all__ = [
    "DocsAuditFinding",
    "DocsAuditReport",
    "audit_docs",
    "is_docs_audit_substrate_path",
    "run_docs_audit",
]
