from __future__ import annotations

from repo_support.docs_audit.rules import forward_contracts_support as support
from repo_support.docs_audit.rules._common import build_rule


FORWARD_CONTRACTS_BOUNDARY_RULES = (
    build_rule(
        "forward_contracts.gap_and_review_attachment_rules_use_truthful_scopes",
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
        "forward_contracts.gap_review_records_sidecars_and_subject_refs_are_defined",
        "docs/concepts/gaps-and-reviews.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "gap/review record, sidecar, or SubjectRef contracts drifted"
                )
            )
            for needle in (
                "## `SubjectRef`",
                "## Non-Subject Scope Ids",
                "### `GapRecord`",
                "### `GapExplanation`",
                "### `ReviewRecord`",
                "### `ReviewExplanation`",
                "## Readiness Locality",
                "## Sidecar Taxonomy",
            )
            if needle
            not in support.text(support.docs_path("concepts/gaps-and-reviews.md"))
        ],
    ),
    build_rule(
        "forward_contracts.keep_placement_mechanical",
        "docs/concepts/domain-ontology.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("forward contract placement rules drifted")
            )
            for needle in (
                "`domain/assessment/`",
                "`application/compatibility/`",
                "`application/evidence/`",
                "`application/economics/`",
                "`application/reconciliation/`",
                "`application/accounting/`",
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
        "forward_contracts.product_headers_use_product_ids_not_kernel_scope_id",
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
                    support.docs_path(
                        "reference/economics-reconciliation-checkpoint-contract.md"
                    )
                )
                + "\n"
                + support.text(
                    support.docs_path("concepts/reconciliation-tax-architecture.md")
                )
            )
        ],
    ),
    build_rule(
        "forward_contracts.downstream_identity_recipes_do_not_embed_bridge_nouns",
        "docs/reference/evidence-claim-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "downstream identity recipes drifted toward bridge nouns"
                )
            )
            for needle in (
                (
                    "source_slug` and `adapter_id` remain evidence-local identity "
                    "inputs and do\n"
                    "  not reappear in downstream product ids once "
                    "`evidence_set_ref` is available"
                ),
                (
                    "downstream products keep claim lineage through "
                    "`claim_set_ref` or\n"
                    "  `claim_set_refs`; they do not copy `source_slug`, "
                    "`adapter_id`, or\n"
                    "  `emitter_id` into later product ids"
                ),
                (
                    "`source_slug` is evidence-local only; it must not become "
                    "a downstream product\n"
                    "  id component"
                ),
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
        "forward_contracts.slice_contracts_freeze_ids_values_and_reader_cutovers",
        "docs/reference/evidence-claim-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"{path.name} no longer freezes ids, compatibility views, "
                    "parity gates, and idempotent rerun guarantees"
                )
            )
            for path in (
                support.docs_path("reference/evidence-claim-contract.md"),
                support.docs_path(
                    "reference/economics-reconciliation-checkpoint-contract.md"
                ),
            )
            if any(
                heading not in (text := support.text(path))
                for heading in (
                    "## Id And Fingerprint Rules",
                    "## Bridge Compatibility Views",
                    "## Parity Gates",
                    "## Idempotent Rerun Guarantees",
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
                path.name == "evidence-claim-contract.md"
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
        "forward_contracts.persistence_model_partition_scopes_and_filesystem_layout_are_defined",
        "docs/concepts/reconciliation-tax-architecture.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "authoritative persistence model or filesystem placement drifted"
                )
            )
            for needle in (
                "## Authoritative Persistence Model",
                "### Default Partition Scopes",
                "### Default Filesystem Placement",
                "product sidecars persist separately from kernels",
                "target basenames use the owning product or sidecar family directly",
                "working/products/evidence_sets/<evidence_set_id>/evidence_set.json",
                "assessment/gap/gap_records.json",
                "assessment/review/review_records.json",
            )
            if needle
            not in support.text(
                support.docs_path("concepts/reconciliation-tax-architecture.md")
            )
        ],
    ),
    build_rule(
        "forward_contracts.keep_source_specific_crypto_nouns_out_of_canonical_fields",
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
