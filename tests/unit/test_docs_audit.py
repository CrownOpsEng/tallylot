from __future__ import annotations

import json

import pytest

import repo_support.docs_audit as docs_audit
from repo_support.docs_audit.model import DocsAuditFinding, DocsAuditRule
from repo_support.docs_audit.rules import forward_contracts_matrix
from repo_support.docs_audit.rules import forward_contracts_support
from repo_support.docs_audit.rules import policy_alignment
from repo_support.docs_audit.rules import runtime
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


def _phase_label() -> str:
    return " ".join(("Phase", "2"))


def _phase_word_label() -> str:
    return "-".join(("phase", "zero"))


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
        paths=("repo_support/docs_audit/rules/forward_contracts_contracts.py",)
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


def test_durable_doc_policy_rule_rejects_ephemeral_delivery_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phase_label = _phase_label()
    phase_word_label = _phase_word_label()
    payloads = {
        "docs/status/current-state.md": f"Current runtime keeps {phase_label} wording out.",
        "docs/reference/evidence-claim-contract.md": (
            f"Bounded contract keeps {phase_word_label} wording out."
        ),
        "docs/concepts/architecture-overview.md": "This surface only links `ROADMAP.md`.",
    }

    monkeypatch.setattr(
        policy_alignment,
        "_durable_non_planning_surface_texts",
        lambda: tuple(payloads.items()),
    )

    findings = next(
        rule.run()
        for rule in policy_alignment.POLICY_ALIGNMENT_RULES
        if rule.rule_id
        == "policy_alignment.durable_non_planning_surfaces_do_not_use_ephemeral_delivery_labels"
    )

    assert findings == (
        DocsAuditFinding(
            "policy_alignment.durable_non_planning_surfaces_do_not_use_ephemeral_delivery_labels",
            "docs/status/current-state.md",
            (
                "docs/status/current-state.md uses forbidden roadmap/phase delivery labels: "
                f"{phase_label}"
            ),
            None,
        ),
        DocsAuditFinding(
            "policy_alignment.durable_non_planning_surfaces_do_not_use_ephemeral_delivery_labels",
            "docs/reference/evidence-claim-contract.md",
            (
                "docs/reference/evidence-claim-contract.md uses forbidden "
                f"roadmap/phase delivery labels: {phase_word_label}"
            ),
            None,
        ),
    )


def test_durable_doc_policy_rule_rejects_forbidden_planning_phrases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = {
        "docs/reference/journal-contract.md": "These are not durable Phase 6 artifacts.",
        "docs/concepts/domain-ontology.md": "The roadmap trigger ladder decides this.",
        "docs/status/current-state.md": "Use this in the next architecture phase.",
    }

    monkeypatch.setattr(
        policy_alignment,
        "_durable_non_planning_surface_texts",
        lambda: tuple(payloads.items()),
    )

    findings = next(
        rule.run()
        for rule in policy_alignment.POLICY_ALIGNMENT_RULES
        if rule.rule_id
        == "policy_alignment.durable_non_planning_surfaces_do_not_use_forbidden_planning_phrases"
    )

    assert findings == (
        DocsAuditFinding(
            "policy_alignment.durable_non_planning_surfaces_do_not_use_forbidden_planning_phrases",
            "docs/reference/journal-contract.md",
            "docs/reference/journal-contract.md uses forbidden planning phrase: Phase 6 artifacts",
            None,
        ),
        DocsAuditFinding(
            "policy_alignment.durable_non_planning_surfaces_do_not_use_forbidden_planning_phrases",
            "docs/concepts/domain-ontology.md",
            "docs/concepts/domain-ontology.md uses forbidden planning phrase: roadmap trigger ladder",
            None,
        ),
        DocsAuditFinding(
            "policy_alignment.durable_non_planning_surfaces_do_not_use_forbidden_planning_phrases",
            "docs/status/current-state.md",
            "docs/status/current-state.md uses forbidden planning phrase: next architecture phase",
            None,
        ),
    )


def test_runtime_rule_requires_fast_path_phrasing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = {
        "status/current-state.md": "\n".join(
            (
                "Automatic recalculation is the default normalization posture",
                "`source normalize --update-mode full-update`",
                "`source normalize --update-mode rebuild`",
            )
        ),
        "reference/evidence-claim-contract.md": "automatic and transparent only",
        "reference/economics-reconciliation-checkpoint-contract.md": "\n".join(
            ("`full-update`", "`rebuild`", "skip recalculation")
        ),
        "guides/source-intake.md": "\n".join(
            ("--update-mode auto", "--update-mode full-update", "--update-mode rebuild")
        ),
        "guides/normalize-screen-stage.md": "\n".join(
            ("--update-mode auto", "--update-mode full-update", "--update-mode rebuild")
        ),
    }

    def fake_docs_text(path: str) -> str:
        return docs[path]

    monkeypatch.setattr(runtime, "docs_text", fake_docs_text)

    findings = next(
        rule.run()
        for rule in runtime.RUNTIME_RULES
        if rule.rule_id == "runtime.owner_docs_pin_automatic_fast_path_reruns"
    )

    assert findings == (
        DocsAuditFinding(
            "runtime.owner_docs_pin_automatic_fast_path_reruns",
            "docs/status/current-state.md",
            "reference/evidence-claim-contract.md is missing fast-path rerun contract text",
            None,
        ),
    )


def test_runtime_rule_rejects_replay_as_normal_operator_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = {
        "guides/source-intake.md": "Replay validation is just another operator step.",
        "guides/operator-quickstart.md": "Run validate-workspace-replay now.",
        "guides/normalize-screen-stage.md": "Normal path.",
    }

    def fake_docs_text(path: str) -> str:
        return docs[path]

    monkeypatch.setattr(runtime, "docs_text", fake_docs_text)

    findings = next(
        rule.run()
        for rule in runtime.RUNTIME_RULES
        if rule.rule_id == "runtime.operator_docs_keep_workspace_replay_developer_only"
    )

    assert findings == (
        DocsAuditFinding(
            "runtime.operator_docs_keep_workspace_replay_developer_only",
            "docs/guides/source-intake.md",
            (
                "source-intake or operator docs present replay validation as a normal operator step"
            ),
            None,
        ),
    )


def test_roadmap_path_triggers_full_repo_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docs_audit,
        "ALL_RULES",
        (_rule("routes.example"), _rule("forward_contracts.example")),
    )

    report = docs_audit.run_docs_audit(paths=("ROADMAP.md",))

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


def test_owner_docs_exclude_roadmap_and_use_renamed_contract_pages() -> None:
    owner_docs = {
        path.relative_to(forward_contracts_support.repo_root()).as_posix()
        for path in forward_contracts_support.OWNER_DOCS
    }

    assert "ROADMAP.md" not in owner_docs
    assert "docs/reference/evidence-claim-contract.md" in owner_docs
    assert (
        "docs/reference/economics-reconciliation-checkpoint-contract.md" in owner_docs
    )


def test_authoritative_contract_text_uses_renamed_contract_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_text(path: object) -> str:
        return getattr(path, "name", "")

    monkeypatch.setattr(
        forward_contracts_support,
        "text",
        fake_text,
    )

    text = forward_contracts_support.authoritative_contract_text()

    assert "evidence-claim-contract.md" in text
    assert "economics-reconciliation-checkpoint-contract.md" in text
    assert "ROADMAP.md" not in text


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
