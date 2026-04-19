from __future__ import annotations

from dataclasses import asdict

from .model import DocsAuditReport


def report_payload(report: DocsAuditReport) -> dict[str, object]:
    return {
        "requested_paths": list(report.requested_paths),
        "evaluated_rule_ids": list(report.evaluated_rule_ids),
        "full_repo": report.full_repo,
        "evaluated_paths": list(report.evaluated_paths),
        "findings": [asdict(finding) for finding in report.findings],
    }


def render_human_report(report: DocsAuditReport) -> str:
    if not report.findings:
        return "docs audit report: no findings"
    lines: list[str] = []
    for finding in report.findings:
        lines.append(f"{finding.path} [{finding.rule_id}] {finding.message}")
        if finding.suggestion:
            lines.append(f"  suggestion: {finding.suggestion}")
    return "\n".join(lines)
