from __future__ import annotations

from repo_support.target_naming import target_naming_rule_ids

from . import forward_contracts_support as support
from ._common import build_rule
from .forward_contracts_contracts import FORWARD_CONTRACTS_CONTRACT_RULES
from .forward_contracts_matrix import FORWARD_CONTRACTS_MATRIX_RULES
from .policy_alignment import POLICY_ALIGNMENT_RULES
from .routes import ROUTE_RULES
from .runtime import RUNTIME_RULES


def _registered_proof_tokens() -> frozenset[str]:
    return frozenset(
        {
            *(
                f"docs-audit:{rule.rule_id}"
                for rules in (
                    ROUTE_RULES,
                    RUNTIME_RULES,
                    POLICY_ALIGNMENT_RULES,
                    FORWARD_CONTRACTS_MATRIX_RULES,
                    FORWARD_CONTRACTS_CONTRACT_RULES,
                    FORWARD_CONTRACTS_ROADMAP_RULES,
                )
                for rule in rules
            ),
            *(f"target-naming:{rule_id}" for rule_id in target_naming_rule_ids()),
        }
    )


def _validate_completion_gate_rows() -> None:
    criteria = support.completion_gate_criteria()
    rows = support.completion_gate_rows()
    row_criteria = tuple(row[0] for row in rows)
    if criteria != row_criteria:
        raise AssertionError(
            "completion-gate bullet list and completion-gate table rows must match exactly"
        )
    if len(set(row_criteria)) != len(row_criteria):
        raise AssertionError("completion-gate rows must not duplicate exit criteria")

    registered_tokens = _registered_proof_tokens()
    for criterion, authority_cell, proof_cell in rows:
        entries = support.authority_entries(authority_cell)
        proofs = support.proof_tokens(proof_cell)
        if len(set(proofs)) != len(proofs):
            raise AssertionError(
                f"completion-gate proof tokens must be unique within {criterion!r}"
            )
        for proof in proofs:
            prefix, _, _rule_id = proof.partition(":")
            if prefix not in support.ALLOWED_PROOF_TOKEN_PREFIXES:
                raise AssertionError(
                    f"completion-gate proof token uses unsupported prefix in {criterion!r}: {proof}"
                )
            if proof not in registered_tokens:
                raise AssertionError(
                    f"completion-gate proof token is not registered for {criterion!r}: {proof}"
                )
        for path, heading in entries:
            if path not in support.OWNER_DOC_SET:
                raise AssertionError(
                    f"completion-gate authority must cite owner docs only for {criterion!r}: {path}"
                )
            occurrences = support.heading_occurrence_count(
                support.text(support.repo_root() / path),
                heading,
            )
            if occurrences != 1:
                raise AssertionError(
                    f"completion-gate authority heading must exist exactly once for {criterion!r}: {path} {heading}"
                )


FORWARD_CONTRACTS_ROADMAP_RULES = (
    build_rule(
        "forward_contracts.owner_contract_pages_are_exactly_listed_in_completion_gate",
        "ROADMAP.md",
        lambda: (
            None
            if support.extract_code_bullets(
                support.text(support.repo_root() / "ROADMAP.md"),
                "Owner docs that must align before broad implementation begins:",
                "Exit criteria:",
            )
            == support.EXPECTED_OWNER_DOCS
            else (_ for _ in ()).throw(
                AssertionError("owner docs listed in the completion gate drifted")
            )
        ),
    ),
    build_rule(
        "forward_contracts.completion_gate_maps_all_must_freeze_items",
        "ROADMAP.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"Must freeze item is not mapped into the completion gate: {item}"
                )
            )
            for item in support.must_freeze_items()
            if item not in frozenset(support.completion_gate_criteria())
        ],
    ),
    build_rule(
        "forward_contracts.completion_gate_uses_exact_owner_doc_authority_and_registered_proof_tokens",
        "ROADMAP.md",
        _validate_completion_gate_rows,
    ),
    build_rule(
        "forward_contracts.owner_contract_pages_do_not_compete_for_the_same_authority",
        "docs/status/migration-sequence.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError("owner contract routing text drifted"))
            for condition in (
                support.normalized(
                    "[ROADMAP.md](../../ROADMAP.md) is the only numbered implementation program of record."
                )
                not in support.normalized(
                    support.text(support.docs_path("status/migration-sequence.md"))
                ),
                "It does not redefine target product contracts or recreate roadmap phase detail."
                not in support.normalized(
                    support.text(support.docs_path("status/migration-sequence.md"))
                ),
                "It does not redefine live bridge truth or target product contracts."
                not in support.normalized(
                    support.text(
                        support.docs_path("concepts/bridge-to-target-mapping.md")
                    )
                ),
                "This page does not redefine every lower-level contract."
                not in support.normalized(
                    support.text(
                        support.docs_path("concepts/reconciliation-tax-architecture.md")
                    )
                ),
                "The authoritative cutover matrix lives in"
                not in support.text(support.docs_path("status/migration-sequence.md")),
            )
            if condition
        ],
    ),
    build_rule(
        "forward_contracts.early_stage_docs_do_not_claim_authority_over_later_bridge_outputs",
        "ROADMAP.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "Phase 1 or Phase 2 claims authority over later bridge outputs"
                )
            )
            for needle in (
                "TransactionFact",
                "facts.csv",
                "balance_snapshots.csv",
                "balance_references.csv",
                "cointracking_csv",
            )
            if needle
            in support.section(
                support.text(support.repo_root() / "ROADMAP.md"),
                "## Phase 1. Land `EvidenceSet`",
                "## Phase 2. Land `ClaimSet`",
            )
            or needle
            in support.section(
                support.text(support.repo_root() / "ROADMAP.md"),
                "## Phase 2. Land `ClaimSet`",
                "## Phase 3. Land `EconomicFacts`",
            )
        ],
    ),
    build_rule(
        "forward_contracts.event_link_scope_is_consistent_across_forward_contracts",
        "docs/reference/first-downstream-slice-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("EventLinkRecord scope wording drifted")
            )
            for needle in (
                "`EventLinkRecord` when a later in-phase reconciliation increment needs\n  explicit event linkage",
                "`EventLinkRecord`",
                "`EventLinkRecord` remains out of scope for this slice and may land only in a\nlater in-phase reconciliation increment.",
            )
            if needle
            not in (
                support.text(support.repo_root() / "ROADMAP.md")
                + "\n"
                + support.text(
                    support.docs_path("concepts/pipeline-stage-contracts.md")
                )
                + "\n"
                + support.text(
                    support.docs_path("reference/first-downstream-slice-contract.md")
                )
            )
        ],
    ),
    build_rule(
        "forward_contracts.tax_outputs_contract_does_not_require_general_read_side_activation",
        "ROADMAP.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "TaxOutputs contract now requires general read-side activation"
                )
            )
            for needle in (
                "tax-output-local derived content",
                "tax-output-local, narrow rendering-local, or compatibility-local derived output",
                "TaxOutputs`-local grouped readiness output",
                "Trigger A. Second Grouped Non-Compatibility Consumer",
            )
            if needle
            not in support.normalized(
                support.text(support.repo_root() / "ROADMAP.md")
                + "\n"
                + support.text(support.docs_path("concepts/architecture-overview.md"))
                + "\n"
                + support.text(
                    support.docs_path("concepts/reconciliation-tax-architecture.md")
                )
                + "\n"
                + support.text(support.docs_path("concepts/gaps-and-reviews.md"))
            )
        ],
    ),
    build_rule(
        "forward_contracts.post_filing_expansion_docs_remain_explicitly_high_level",
        "docs/status/migration-sequence.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "post-filing expansion docs are no longer explicitly high-level"
                )
            )
            for condition in (
                "Phases 6 and later remain intentionally high-level in this round."
                not in support.text(support.repo_root() / "ROADMAP.md"),
                "Phases 6 and later remain intentionally high-level in this round. They are\nout of scope for this repair"
                not in support.text(support.docs_path("status/migration-sequence.md")),
            )
            if condition
        ],
    ),
)
