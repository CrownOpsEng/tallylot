from __future__ import annotations

from . import contract_lock_support as support
from ._common import build_rule

CONTRACT_LOCK_CONTRACT_RULES = (
    build_rule(
        "contract_lock.forward_contracts_do_not_reference_undefined_record_families_or_refs",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("forward contracts reference undefined record families")
            )
            for condition in (
                support.used_record_families()
                - support.DEFINED_TARGET_RECORD_FAMILIES
                - support.ALLOWED_CURRENT_STATE_RECORD_NAMES
            )
            if condition
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError("forward contracts reference undefined ref types")
            )
            for condition in (
                support.used_ref_types() - support.DEFINED_TARGET_REF_TYPES
            )
            if condition
        ],
    ),
    build_rule(
        "contract_lock.critical_path_observation_field_tables_are_unique_and_complete",
        "docs/reference/first-upstream-slice-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("critical-path observation field tables drifted")
            )
            for text in (
                support.section(
                    support.text(
                        support.docs_path("concepts/pipeline-stage-contracts.md")
                    ),
                    "### First-Slice Critical-Path Observation Kinds",
                    "Stable ids:",
                ),
                support.section(
                    support.text(
                        support.docs_path("reference/first-upstream-slice-contract.md")
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
        "contract_lock.critical_path_claim_field_tables_are_unique_and_complete",
        "docs/reference/first-upstream-slice-contract.md",
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
        "contract_lock.noncritical_observation_and_claim_work_is_explicitly_deferred",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "non-critical observation and claim work is no longer explicitly deferred"
                )
            )
            for needle in (
                "no new observation kind may be implemented until this page or the owning\n  slice page defines its kernel field table explicitly",
                "no non-critical claim kind may be implemented until this page or the\n  owning slice page defines its kernel field table explicitly",
                "valuation-measure taxonomy is intentionally deferred",
                "valuation-measure taxonomy remains intentionally deferred",
                "`valuation` claims remain zero-row by default",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/first-upstream-slice-contract.md")
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.reconciliation_and_checkpoint_hot_path_fields_use_direct_values",
        "docs/reference/first-downstream-slice-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("reconciliation/checkpoint hot-path value rules drifted")
            )
            for needle in (
                "`expected_value`",
                "`observed_value`",
                "`accepted_value`",
                "use value refs that point to undefined sidecar values outside the kernel",
                "`expected_value_ref`",
                "`observed_value_ref`",
                "Not allowed in this slice:",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/first-downstream-slice-contract.md")
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.gap_and_review_attachment_rules_use_truthful_scopes",
        "docs/concepts/gaps-and-reviews.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("gap and review attachment scope rules drifted")
            )
            for needle in (
                "`selection_id`",
                "`claim_scope_id`",
                "`continuity_segment_id`",
                "`balance_target_id`",
                "`checkpoint_proposal_id`",
                "`kernel_scope_id`",
                "do not attach a gap or review to `kernel_scope` when",
                "claim-stage gaps and reviews may attach to `claim_scope_id`",
                "reconciliation-stage gaps and reviews may attach to `balance_target_id`",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/gaps-and-reviews.md"))
                + "\n"
                + support.text(
                    support.docs_path("concepts/pipeline-stage-contracts.md")
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.forward_contracts_keep_placement_mechanical",
        "docs/concepts/domain-ontology.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("forward contract placement rules drifted")
            )
            for needle in (
                "`domain/assessment/`",
                "`application/compatibility/`",
                "`application/claim/`",
                "`application/economics/`",
                "`application/reconciliation/`",
                "`application/checkpoint/`",
                "`application/journal/`",
                "`application/tax/`",
                "Readiness is not a shared assessment family.",
                "do not create a shared readiness record family",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/domain-ontology.md"))
                + "\n"
                + support.text(support.docs_path("concepts/gaps-and-reviews.md"))
            )
        ],
    ),
    build_rule(
        "contract_lock.product_headers_use_product_ids_not_kernel_scope_id",
        "docs/concepts/pipeline-stage-contracts.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError("product header ref rules drifted"))
            for needle in (
                "upstream product refs use product ids only; they never use\n  `kernel_scope_id`",
                "store target product ids, never\n  `kernel_scope_id`",
                "upstream `*_ref` fields in the product header store product ids, never `kernel_scope_id`",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/first-downstream-slice-contract.md")
                )
                + "\n"
                + support.text(
                    support.docs_path("concepts/reconciliation-tax-architecture.md")
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.downstream_identity_recipes_do_not_embed_bridge_nouns",
        "docs/reference/first-upstream-slice-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "downstream identity recipes drifted toward bridge nouns"
                )
            )
            for needle in (
                "source_slug` and `adapter_id` remain evidence-local identity inputs and do\n  not reappear in downstream product ids once `evidence_set_ref` is available",
                "downstream products keep claim lineage through `claim_set_ref` or\n  `claim_set_refs`; they do not copy `source_slug`, `adapter_id`, or\n  `emitter_id` into later product ids",
                "`source_slug` is evidence-local only; it must not become a downstream product\n  id component",
            )
            if needle
            not in (
                support.text(support.docs_path("concepts/pipeline-stage-contracts.md"))
                + "\n"
                + support.text(
                    support.docs_path("reference/first-upstream-slice-contract.md")
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.slice_contracts_freeze_ids_values_and_reader_cutovers",
        "docs/reference/first-upstream-slice-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"{path.name} no longer freezes ids, compatibility views, parity gates, and replay gates"
                )
            )
            for path in (
                support.docs_path("reference/first-upstream-slice-contract.md"),
                support.docs_path("reference/first-downstream-slice-contract.md"),
            )
            if any(
                heading not in (text := support.text(path))
                for heading in (
                    "## Id And Fingerprint Rules",
                    "## Bridge Compatibility Views",
                    "## Parity Gates",
                    "## Replay Gates",
                )
            )
            or (
                "required derived compatibility views:"
                not in support.section(
                    text, "## Bridge Compatibility Views", "## Parity Gates"
                ).lower()
                or "compatibility rule:"
                not in support.section(
                    text, "## Bridge Compatibility Views", "## Parity Gates"
                ).lower()
                or "authoritative products after the slice"
                not in support.section(
                    text, "## Bridge Compatibility Views", "## Parity Gates"
                ).lower()
            )
            or (
                path.name == "first-upstream-slice-contract.md"
                and any(
                    needle not in text
                    for needle in (
                        "Declared compatibility sidecar boundary:",
                        "`translation_input_plan.json`",
                        "`EconomicActivityDraft`",
                        "`SourceTranslationBatch`",
                        "selected, superseded, and blocked evidence membership",
                        "identical `EvidenceSet` and `ClaimSet` kernel fingerprints",
                    )
                )
            )
        ],
    ),
    build_rule(
        "contract_lock.forward_target_contracts_keep_source_specific_crypto_nouns_out_of_canonical_fields",
        "docs/concepts/domain-ontology.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "forward target contracts drifted toward source-specific crypto nouns"
                )
            )
            for condition in (
                "wallet_label"
                in "\n".join(support.text(path) for path in support.OWNER_DOCS),
                "account_label"
                in "\n".join(support.text(path) for path in support.OWNER_DOCS),
                "location_group_label"
                not in "\n".join(support.text(path) for path in support.OWNER_DOCS),
                "location_label"
                not in "\n".join(support.text(path) for path in support.OWNER_DOCS),
                "source-specific crypto nouns such as `wallet`, `exchange`, `address`,"
                not in support.text(support.docs_path("concepts/domain-ontology.md")),
            )
            if condition
        ],
    ),
)
