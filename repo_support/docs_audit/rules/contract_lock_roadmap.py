from __future__ import annotations

from . import contract_lock_support as support
from ._common import build_rule

CONTRACT_LOCK_ROADMAP_RULES = (
    build_rule(
        "contract_lock.owner_contract_pages_are_exactly_listed_in_roadmap_gate",
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
                AssertionError("owner docs listed in the Phase 0 gate drifted")
            )
        ),
    ),
    build_rule(
        "contract_lock.completion_gate_maps_exit_criteria_to_authoritative_docs_and_automated_proof",
        "ROADMAP.md",
        lambda: (
            None
            if support.extract_plain_bullets(
                support.text(support.repo_root() / "ROADMAP.md"),
                "Exit criteria:",
                "| Exit criterion | Authoritative doc section(s) | Automated proof |",
            )
            == support.EXPECTED_EXIT_CRITERIA
            and all(
                ":" in proof and not proof.startswith("test_")
                for _criterion, _sections, proof_cell in support.completion_gate_rows()
                for proof in support.extract_backticked_tokens(proof_cell)
            )
            else (_ for _ in ()).throw(
                AssertionError("Phase 0 completion gate rows or proof ids drifted")
            )
        ),
    ),
    build_rule(
        "contract_lock.owner_contract_pages_do_not_compete_for_the_same_authority",
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
        "contract_lock.early_stage_docs_do_not_claim_authority_over_later_bridge_outputs",
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
        "contract_lock.event_link_scope_is_consistent_across_forward_contracts",
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
        "contract_lock.tax_outputs_contract_does_not_require_general_read_side_activation",
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
        "contract_lock.later_phase_docs_remain_explicitly_high_level",
        "docs/status/migration-sequence.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("later-phase docs are no longer explicitly high-level")
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
