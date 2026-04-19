from __future__ import annotations

import json

import pytest

import repo_support.docs_audit as docs_audit
from repo_support.docs_audit.model import DocsAuditFinding, DocsAuditRule
from repo_support.docs_audit.reporting import report_payload
from tools import audit_docs as audit_docs_tool


def _rule(rule_id: str, findings: tuple[DocsAuditFinding, ...] = ()) -> DocsAuditRule:
    return DocsAuditRule(rule_id=rule_id, run=lambda: findings)


def test_run_docs_audit_full_repo_with_no_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (
            _rule("routes.example"),
            _rule("runtime.example"),
            _rule("policy_alignment.example"),
            _rule("contract_lock.example"),
        ),
    )

    report = docs_audit.run_docs_audit()

    assert report.full_repo is True
    assert report.findings == ()
    assert report.evaluated_rule_ids == (
        "routes.example",
        "runtime.example",
        "policy_alignment.example",
        "contract_lock.example",
    )


def test_run_docs_audit_can_report_one_finding_per_rule_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (
            _rule(
                "routes.example",
                (
                    DocsAuditFinding(
                        "routes.example", ".claude/commands/x.md", "missing route"
                    ),
                ),
            ),
            _rule(
                "runtime.example",
                (
                    DocsAuditFinding(
                        "runtime.example",
                        "docs/status/current-state.md",
                        "runtime drift",
                    ),
                ),
            ),
            _rule(
                "policy_alignment.example",
                (
                    DocsAuditFinding(
                        "policy_alignment.example", "AGENTS.md", "policy drift"
                    ),
                ),
            ),
            _rule(
                "contract_lock.example",
                (
                    DocsAuditFinding(
                        "contract_lock.example", "ROADMAP.md", "contract_lock drift"
                    ),
                ),
            ),
        ),
    )

    report = docs_audit.run_docs_audit()

    assert tuple(finding.rule_id for finding in report.findings) == (
        "routes.example",
        "runtime.example",
        "policy_alignment.example",
        "contract_lock.example",
    )


def test_report_payload_json_shape(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (
            _rule(
                "routes.example",
                (
                    DocsAuditFinding(
                        "routes.example",
                        "docs/example.md",
                        "example finding",
                        "update the doc",
                    ),
                ),
            ),
        ),
    )

    assert audit_docs_tool.main(["report", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == report_payload(docs_audit.run_docs_audit())
    assert payload["findings"][0]["rule_id"] == "routes.example"
    assert payload["findings"][0]["path"] == "docs/example.md"


def test_check_fails_closed_when_sensitive_paths_are_supplied_but_no_audit_runs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_run_docs_audit(
        paths: tuple[str, ...] | None = None,
    ) -> docs_audit.DocsAuditReport:
        return docs_audit.DocsAuditReport(
            requested_paths=tuple(paths or ()),
            evaluated_rule_ids=(),
            findings=(),
            full_repo=False,
            evaluated_paths=(),
        )

    monkeypatch.setattr(
        audit_docs_tool,
        "run_docs_audit",
        fake_run_docs_audit,
    )

    assert (
        audit_docs_tool.main(["check", "--paths", "docs/guides/source-intake.md"]) == 1
    )
    assert "failed closed" in capsys.readouterr().out


def test_sensitive_substrate_path_triggers_full_repo_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (_rule("routes.example"), _rule("contract_lock.example")),
    )

    report = docs_audit.run_docs_audit(paths=("docs/guides/source-intake.md",))

    assert report.full_repo is True
    assert report.evaluated_rule_ids == ("routes.example", "contract_lock.example")
