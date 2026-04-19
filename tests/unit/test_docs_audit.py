from __future__ import annotations

import json

import pytest

import repo_support.docs_audit as docs_audit
from repo_support.docs_audit.model import DocsAuditFinding, DocsAuditRule
from repo_support.docs_audit.rules import forward_contracts_matrix
from repo_support.docs_audit.rules import forward_contracts_roadmap
from repo_support.docs_audit.rules import forward_contracts_support
from repo_support.docs_audit.reporting import report_payload
from tools import audit_docs as audit_docs_tool


def _rule(rule_id: str, findings: tuple[DocsAuditFinding, ...] = ()) -> DocsAuditRule:
    return DocsAuditRule(rule_id=rule_id, run=lambda: findings)


def _forward_contracts_matrix_rule(rule_id: str) -> DocsAuditRule:
    return next(
        rule
        for rule in forward_contracts_matrix.FORWARD_CONTRACTS_MATRIX_RULES
        if rule.rule_id == rule_id
    )


def _bridge_row(
    **overrides: str,
) -> dict[str, str]:
    row = {
        "Current bridge surface": "`EconomicActivityDraft`",
        "Target authoritative product(s)": "`ClaimSet`",
        "Derived compatibility view": "`EconomicActivityDraft`",
        "Derived compatibility sidecar": "`compatibility sidecar`",
        "Current readers": "`source assemble bridge projection path`",
        "Target readers after cutover": "economics construction from `ClaimSet`",
        "Cutover gate": "claim field tables and retained legacy fields are frozen",
        "Retirement gate": "retire when no active bridge projection path still consumes drafts",
    }
    row.update(overrides)
    return row


def _heading_present_once(_text: str, _heading: str) -> int:
    return 1


def _heading_missing(_text: str, _heading: str) -> int:
    return 0


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
            _rule("forward_contracts.example"),
        ),
    )

    report = docs_audit.run_docs_audit()

    assert report.full_repo is True
    assert not report.findings
    assert report.evaluated_rule_ids == (
        "routes.example",
        "runtime.example",
        "policy_alignment.example",
        "forward_contracts.example",
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
                "forward_contracts.example",
                (
                    DocsAuditFinding(
                        "forward_contracts.example",
                        "ROADMAP.md",
                        "forward-contract drift",
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
        "forward_contracts.example",
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
        (_rule("routes.example"), _rule("forward_contracts.example")),
    )

    report = docs_audit.run_docs_audit(paths=("docs/guides/source-intake.md",))

    assert report.full_repo is True
    assert report.evaluated_rule_ids == (
        "routes.example",
        "forward_contracts.example",
    )


def test_sensitive_docs_audit_tooling_path_triggers_full_repo_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (_rule("routes.example"), _rule("forward_contracts.example")),
    )

    report = docs_audit.run_docs_audit(
        paths=("repo_support/docs_audit/rules/forward_contracts_roadmap.py",)
    )

    assert report.full_repo is True
    assert report.evaluated_rule_ids == (
        "routes.example",
        "forward_contracts.example",
    )


def test_target_naming_catalog_path_triggers_full_repo_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (_rule("routes.example"), _rule("forward_contracts.example")),
    )

    report = docs_audit.run_docs_audit(paths=("tools/target_naming_catalog.yaml",))

    assert report.full_repo is True
    assert report.evaluated_rule_ids == (
        "routes.example",
        "forward_contracts.example",
    )


def test_authority_entries_require_exact_path_heading_pairs() -> None:
    with pytest.raises(
        AssertionError,
        match="exact semicolon-separated `path` `heading` pairs",
    ):
        forward_contracts_support.authority_entries(
            "`docs/concepts/pipeline-stage-contracts.md` matching field-table sections"
        )


def test_completion_gate_validation_rejects_non_owner_authority_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_criteria",
        lambda: ("criterion",),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_rows",
        lambda: (
            (
                "criterion",
                "`docs/reference/target-ids-and-refs.md` `## Origin Ref`",
                "`docs-audit:forward_contracts.example`",
            ),
        ),
    )
    monkeypatch.setattr(
        forward_contracts_roadmap,
        "_registered_proof_tokens",
        lambda: frozenset({"docs-audit:forward_contracts.example"}),
    )

    with pytest.raises(AssertionError, match="owner docs only"):
        forward_contracts_roadmap._validate_completion_gate_rows()


def test_completion_gate_validation_rejects_unknown_proof_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_criteria",
        lambda: ("criterion",),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_rows",
        lambda: (
            (
                "criterion",
                "`ROADMAP.md` `## Phase 0. Contract Lock And Bounded-Slice Prep`",
                "`pytest:test_docs_gate`",
            ),
        ),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "heading_occurrence_count",
        _heading_present_once,
    )
    monkeypatch.setattr(
        forward_contracts_roadmap,
        "_registered_proof_tokens",
        lambda: frozenset({"docs-audit:forward_contracts.example"}),
    )

    with pytest.raises(AssertionError, match="unsupported prefix"):
        forward_contracts_roadmap._validate_completion_gate_rows()


def test_completion_gate_validation_rejects_unregistered_proof_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_criteria",
        lambda: ("criterion",),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_rows",
        lambda: (
            (
                "criterion",
                "`ROADMAP.md` `## Phase 0. Contract Lock And Bounded-Slice Prep`",
                "`docs-audit:forward_contracts.renamed_rule`",
            ),
        ),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "heading_occurrence_count",
        _heading_present_once,
    )
    monkeypatch.setattr(
        forward_contracts_roadmap,
        "_registered_proof_tokens",
        lambda: frozenset({"docs-audit:forward_contracts.example"}),
    )

    with pytest.raises(AssertionError, match="is not registered"):
        forward_contracts_roadmap._validate_completion_gate_rows()


def test_completion_gate_validation_rejects_missing_authority_heading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_criteria",
        lambda: ("criterion",),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_rows",
        lambda: (
            (
                "criterion",
                "`ROADMAP.md` `## Missing Heading`",
                "`docs-audit:forward_contracts.example`",
            ),
        ),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "heading_occurrence_count",
        _heading_missing,
    )
    monkeypatch.setattr(
        forward_contracts_roadmap,
        "_registered_proof_tokens",
        lambda: frozenset({"docs-audit:forward_contracts.example"}),
    )

    with pytest.raises(AssertionError, match="must exist exactly once"):
        forward_contracts_roadmap._validate_completion_gate_rows()


def test_bridge_cutover_matrix_current_reader_labels_stay_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rule = _forward_contracts_matrix_rule(
        "forward_contracts.bridge_cutover_matrix_current_reader_labels_are_canonical"
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "bridge_matrix_rows",
        lambda: (
            _bridge_row(
                **{"Current readers": "source assemble bridge projection path"}
            ),
        ),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "reader_inventory",
        lambda: ("source assemble bridge projection path",),
    )

    findings = rule.run()

    assert findings
    assert findings[0].rule_id == (
        "forward_contracts.bridge_cutover_matrix_current_reader_labels_are_canonical"
    )


def test_bridge_cutover_matrix_target_readers_name_capability_and_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rule = _forward_contracts_matrix_rule(
        "forward_contracts.bridge_cutover_matrix_target_readers_name_capability_and_authority"
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "bridge_matrix_rows",
        lambda: (
            _bridge_row(
                **{
                    "Target readers after cutover": (
                        "future consumer reading `ClaimSet`"
                    )
                }
            ),
        ),
    )

    findings = rule.run()

    assert findings
    assert findings[0].rule_id == (
        "forward_contracts.bridge_cutover_matrix_target_readers_name_capability_and_authority"
    )


def test_bridge_cutover_matrix_compatibility_shapes_stay_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rule = _forward_contracts_matrix_rule(
        "forward_contracts.bridge_cutover_matrix_compatibility_shapes_and_surface_names_are_canonical"
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "bridge_matrix_rows",
        lambda: (
            _bridge_row(
                **{
                    "Derived compatibility sidecar": (
                        "`declared claim compatibility sidecars`"
                    )
                }
            ),
        ),
    )

    findings = rule.run()

    assert findings
    assert findings[0].rule_id == (
        "forward_contracts.bridge_cutover_matrix_compatibility_shapes_and_surface_names_are_canonical"
    )


def test_completion_gate_validation_requires_all_must_freeze_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_rule = next(
        rule
        for rule in forward_contracts_roadmap.FORWARD_CONTRACTS_ROADMAP_RULES
        if rule.rule_id
        == "forward_contracts.completion_gate_maps_all_must_freeze_items"
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "must_freeze_items",
        lambda: ("freeze-a", "freeze-b"),
    )
    monkeypatch.setattr(
        forward_contracts_support,
        "completion_gate_criteria",
        lambda: ("freeze-a",),
    )

    findings = target_rule.run()

    assert findings
    assert findings[0].rule_id == (
        "forward_contracts.completion_gate_maps_all_must_freeze_items"
    )
