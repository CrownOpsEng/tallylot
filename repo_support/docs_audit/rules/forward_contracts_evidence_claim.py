from __future__ import annotations

from repo_support.docs_audit.rules import forward_contracts_support as support
from repo_support.docs_audit.rules._common import build_rule


FORWARD_CONTRACTS_EVIDENCE_CLAIM_RULES = (
    build_rule(
        "forward_contracts.evidence_set_contract_and_fingerprint_rules_are_defined",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "EvidenceSet contract or selection fingerprint rules drifted"
                )
            )
            for needle in (
                "## `EvidenceSet`",
                "`selection_fingerprint`",
                "`EvidenceSelectionRecord`",
                "`EvidenceMemberRecord`",
                "`EvidenceObservationRecord`",
                "the authoritative selection state intentionally produces a new",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/evidence-claim-contract.md")
                )
            )
        ],
    ),
    build_rule(
        "forward_contracts.claim_set_scope_bundle_decision_and_compatibility_boundary_are_defined",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "ClaimSet scope, bundle, decision, or compatibility boundary drifted"
                )
            )
            for needle in (
                "## `ClaimSet`",
                "`ClaimBundleRecord`",
                "`ClaimBundleDecisionRecord`",
                "`observation_refs`",
                "`ClaimBundleDecisionRecord.basis` is a pure reason axis.",
                "### Derived Compatibility Sidecars",
                "these bridge-only fields must live only in derived compatibility sidecars",
                "review markers map to shared gap/review records and sidecars",
            )
            if needle
            not in support.text(
                support.docs_path("concepts/pipeline-stage-contracts.md")
            )
        ],
    ),
    build_rule(
        "forward_contracts.critical_path_observation_field_tables_are_unique_and_complete",
        "docs/reference/evidence-claim-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("critical-path observation field tables drifted")
            )
            for text in (
                support.section(
                    support.text(
                        support.docs_path("concepts/pipeline-stage-contracts.md")
                    ),
                    "### Bounded Evidence-Claim Critical-Path Observation Kinds",
                    "Stable ids:",
                ),
                support.section(
                    support.text(
                        support.docs_path("reference/evidence-claim-contract.md")
                    ),
                    "Frozen kind-specific observation fields:",
                    "Observation-field rules:",
                ),
            )
            if text.count("| `statement_document` |") != 1
            or text.count("| `statement_balance_row` |") != 1
            or "statement_kind" not in text
            or "location_group_label" not in text
            or "price_currency" not in text
        ],
    ),
    build_rule(
        "forward_contracts.critical_path_claim_field_tables_are_unique_and_complete",
        "docs/reference/evidence-claim-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("critical-path claim field tables drifted")
            )
            for condition in (
                support.extract_code_bullets(
                    support.text(
                        support.docs_path("concepts/pipeline-stage-contracts.md")
                    ),
                    "Canonical `ClaimRecord.kind` values:",
                    "Controlled vocabularies:",
                )
                != (
                    "activity",
                    "balance",
                    "instrument",
                    "location",
                    "legal_owner",
                    "beneficial_owner",
                    "counterparty",
                    "statement_document",
                    "contract",
                    "valuation",
                ),
            )
            if condition
        ],
    ),
    build_rule(
        "forward_contracts.noncritical_observation_and_claim_work_is_explicitly_deferred",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "non-critical observation and claim work is no longer explicitly deferred"
                )
            )
            for needle in (
                (
                    "no new observation kind may be implemented until this page "
                    "or the owning\n"
                    "  slice page defines its kernel field table explicitly"
                ),
                (
                    "no non-critical claim kind may be implemented until this "
                    "page or the\n"
                    "  owning slice page defines its kernel field table "
                    "explicitly"
                ),
                "valuation-measure taxonomy is intentionally deferred",
                "valuation-measure taxonomy remains intentionally deferred",
                "`valuation` claims remain zero-row by default",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/evidence-claim-contract.md")
                )
            )
        ],
    ),
)
