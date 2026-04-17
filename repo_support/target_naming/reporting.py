from __future__ import annotations

from dataclasses import asdict

from .model import AuditReport


def report_payload(report: AuditReport) -> dict[str, object]:
    return {
        "requested_paths": list(report.requested_paths),
        "evaluated_paths": list(report.evaluated_paths),
        "skipped_paths": list(report.skipped_paths),
        "full_repo": report.full_repo,
        "findings": [asdict(item) for item in report.findings],
    }


def render_human_report(report: AuditReport) -> str:
    if not report.findings:
        return "target naming report: no findings"
    lines: list[str] = []
    for finding in report.findings:
        lines.append(
            f"{finding.path}:{finding.line}:{finding.column} "
            f"[{finding.rule_id}] {finding.message}"
        )
        lines.append(f"  suggestion: {finding.suggestion}")
        if finding.exception_id is not None:
            lines.append(f"  exception: {finding.exception_id}")
    return "\n".join(lines)
