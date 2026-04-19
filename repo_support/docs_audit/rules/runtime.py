from __future__ import annotations

from tallylot.domain.captures import provenance_locator_header
from tallylot.domain.transactions import ProjectionHint
from tallylot.infrastructure.workspace.layout import SEED_FILES
from tallylot.ports.source_profiles import PROFILE_INVENTORY_HEADER

from ._common import build_rule
from ..helpers import docs_path, docs_text


def _seed_header(relative_path: str) -> str:
    return next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == relative_path
    )


RUNTIME_RULES = (
    build_rule(
        "runtime.current_state_mentions_capture_and_assembly_runtime_surfaces",
        "docs/status/current-state.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"missing runtime surface {needle!r}"))
            for needle in (
                "capture registry",
                "working/normalized/captures/<capture_uid>/",
                "working/normalized/sources/<source>/",
                "shared statement extraction",
                "tools.validate_workspace_replay",
                "expected-difference fixtures",
            )
            if needle not in docs_text("status/current-state.md")
        ],
    ),
    build_rule(
        "runtime.updated_workspace_and_operator_docs_drop_legacy_capture_and_normalized_paths",
        "docs/guides",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"{path} still uses legacy capture path")
            )
            for path in (
                docs_path("guides/operator-quickstart.md"),
                docs_path("guides/source-intake.md"),
                docs_path("guides/normalize-screen-stage.md"),
                docs_path("guides/full-operator-workflow.md"),
                docs_path("workspace/evidence/raw/source/README.md"),
                docs_path("workspace/working/normalized/README.md"),
            )
            if "<capture_id>" in path.read_text(encoding="utf-8")
            or "working/normalized/<source>" in path.read_text(encoding="utf-8")
        ],
    ),
    build_rule(
        "runtime.docs_require_materialized_capture_roots_for_profile_and_normalize",
        "docs/status/current-state.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"{path} does not pin materialized capture roots")
            )
            for path in (
                docs_path("status/current-state.md"),
                docs_path("guides/operator-quickstart.md"),
                docs_path("guides/source-intake.md"),
                docs_path("guides/normalize-screen-stage.md"),
                docs_path("guides/full-operator-workflow.md"),
                docs_path("workspace/evidence/raw/source/README.md"),
            )
            if (
                "capture.json" not in (text := path.read_text(encoding="utf-8"))
                or not (
                    ("materialized" in text and "capture root" in text)
                    or "exact capture root" in text
                )
            )
        ],
    ),
    build_rule(
        "runtime.docs_pin_profile_inventory_capture_scoped_fields",
        "docs/workspace/working/normalized/README.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing profile inventory field {field!r}")
            )
            for field in (
                "capture_uid",
                "source",
                "evidence_role",
                "observed_period_start",
                "observed_period_end",
                "observed_period_label",
                "statement_kind",
                "originality_class",
            )
            if f"`{field}`" not in docs_text("workspace/working/normalized/README.md")
            or field not in PROFILE_INVENTORY_HEADER
        ],
    ),
    build_rule(
        "runtime.docs_pin_flattened_provenance_locator_columns",
        "docs/workspace/working/normalized/README.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing provenance column {column!r}")
            )
            for column in (
                *provenance_locator_header(),
                *provenance_locator_header("raw"),
            )
            if f"`{column}`" not in docs_text("workspace/working/normalized/README.md")
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError(f"missing evidence provenance column {column!r}")
            )
            for column in provenance_locator_header("evidence")
            if f"`{column}`"
            not in docs_text("reference/location-inventory-artifacts.md")
        ],
    ),
    build_rule(
        "runtime.docs_pin_deterministic_source_assembly_reruns",
        "docs/status/current-state.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"{path} does not describe deterministic reruns")
            )
            for path in (
                docs_path("status/current-state.md"),
                docs_path("guides/operator-quickstart.md"),
                docs_path("guides/source-intake.md"),
                docs_path("guides/normalize-screen-stage.md"),
                docs_path("guides/full-operator-workflow.md"),
                docs_path("workspace/working/normalized/README.md"),
            )
            if "rerun" not in (text := path.read_text(encoding="utf-8").lower())
            or "rewrite" not in text
        ],
    ),
    build_rule(
        "runtime.docs_pin_workspace_replay_expected_difference_limits",
        "docs/status/current-state.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing expected difference field {field!r}")
            )
            for field in ("issue_count_delta", "review_count_delta", "reason")
            if f"`{field}`" not in docs_text("status/current-state.md")
        ]
        + (
            [
                (_ for _ in ()).throw(
                    AssertionError(
                        "fact_count_delta must stay out of expected-difference fixtures"
                    )
                )
            ]
            if "fact_count_delta" in docs_text("status/current-state.md")
            else []
        ),
    ),
    build_rule(
        "runtime.manual_balance_submission_docs_mention_checkpoint_commands",
        "docs/reference/manual-balance-submission-artifacts.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"{path} is missing manual balance submission commands")
            )
            for path in (
                docs_path("reference/manual-balance-submission-artifacts.md"),
                docs_path("guides/operator-quickstart.md"),
                docs_path("guides/normalize-screen-stage.md"),
            )
            if "checkpoint scaffold-balance-submission"
            not in (text := path.read_text(encoding="utf-8"))
            or "checkpoint submit-balances" not in text
        ],
    ),
    build_rule(
        "runtime.workspace_docs_reference_manual_balance_submission_paths",
        "docs/workspace/README.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "workspace docs do not route to manual balance submission paths"
                )
            )
            for condition in (
                "working/supporting_artifacts/balance_submissions/README.md"
                not in docs_text("workspace/README.md"),
                "balance_submissions/README.md"
                not in docs_text("workspace/working/supporting_artifacts/README.md"),
                "working/supporting_artifacts/balance_submissions/<source>/"
                not in docs_text(
                    "workspace/working/supporting_artifacts/balance_submissions/README.md"
                ),
            )
            if condition
        ],
    ),
    build_rule(
        "runtime.reconciliation_workspace_docs_mention_cross_source_sidecars",
        "docs/workspace/analysis/reconciliation/README.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing cross-source sidecar {artifact!r}")
            )
            for artifact in (
                "cross_source_assertions.csv",
                "cross_source_issues.csv",
                "cross_source_summary.json",
            )
            if artifact not in docs_text("workspace/analysis/reconciliation/README.md")
        ],
    ),
    build_rule(
        "runtime.evidence_claim_contract_pins_all_retained_compatibility_surfaces",
        "docs/reference/evidence-claim-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing upstream compatibility needle {needle!r}")
            )
            for needle in (
                "`translation_input_plan.json` content",
                "`EconomicActivityDraft` ordering and content for evidence in this slice",
                "`SourceTranslationBatch` content for evidence in this slice",
                "Retained compatibility views are part of the slice parity bar.",
                "legacy readers remain active.",
            )
            if needle not in docs_text("reference/evidence-claim-contract.md")
        ],
    ),
    build_rule(
        "runtime.economics_reconciliation_checkpoint_contract_pins_fact_csv_projection_parity",
        "docs/reference/economics-reconciliation-checkpoint-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing downstream compatibility needle {needle!r}")
            )
            for needle in (
                "`TransactionFact` and `facts.csv` derived from `EconomicFacts`",
                "`facts.csv` content for evidence in this slice",
                "Retained compatibility views are part of the slice parity bar.",
                "legacy readers remain active.",
            )
            if needle
            not in docs_text(
                "reference/economics-reconciliation-checkpoint-contract.md"
            )
        ],
    ),
    build_rule(
        "runtime.docs_audit_seed_issue_log_header_matches_template",
        "src/tallylot/infrastructure/workspace/layout.py",
        lambda: (
            None
            if _seed_header("analysis/issues/issue_log.csv")
            == docs_text(
                "workspace/analysis/issues/issue-log-template.csv"
            ).splitlines()[0]
            else (_ for _ in ()).throw(
                AssertionError("workspace issue log seed header is out of sync")
            )
        ),
    ),
    build_rule(
        "runtime.docs_audit_seed_source_inventory_header_matches_template",
        "src/tallylot/infrastructure/workspace/layout.py",
        lambda: (
            None
            if _seed_header("analysis/issues/source_inventory.csv")
            == docs_text(
                "workspace/analysis/issues/source-inventory-template.csv"
            ).splitlines()[0]
            else (_ for _ in ()).throw(
                AssertionError("workspace source inventory seed header is out of sync")
            )
        ),
    ),
    build_rule(
        "runtime.docs_audit_seed_source_captures_header_matches_template",
        "src/tallylot/infrastructure/workspace/layout.py",
        lambda: (
            None
            if _seed_header("analysis/inventory/source_captures.csv")
            == docs_text(
                "workspace/analysis/inventory/source-captures-template.csv"
            ).splitlines()[0]
            else (_ for _ in ()).throw(
                AssertionError("workspace source captures seed header is out of sync")
            )
        ),
    ),
    build_rule(
        "runtime.docs_audit_seed_source_label_map_header_matches_template",
        "src/tallylot/infrastructure/workspace/layout.py",
        lambda: (
            None
            if _seed_header("analysis/issues/source_label_map.csv")
            == docs_text(
                "workspace/analysis/issues/source-label-map-template.csv"
            ).splitlines()[0]
            else (_ for _ in ()).throw(
                AssertionError("workspace source label map seed header is out of sync")
            )
        ),
    ),
    build_rule(
        "runtime.transaction_classification_matrix_describes_runtime_projection_values",
        "docs/concepts/transaction-classification.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing projection matrix row {needle!r}")
            )
            for needle in (
                "| `trade` | `trade` | `spot_trade` | `capital_exchange` | `asset_exchange` |",
                "| `deposit` | `deposit` | `asset_deposit` | `non_taxable_transfer_in` | `funding_inflow` |",
                "| `withdrawal` | `withdrawal` | `asset_withdrawal` | `non_taxable_transfer_out` | `funding_outflow` |",
                "enum members such as `ProjectionHint.TRADE`",
                "stored/runtime values such as `trade`",
                "renderer labels such as `Trade`",
            )
            if needle not in docs_text("concepts/transaction-classification.md")
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError("projection hint runtime values changed unexpectedly")
            )
            for condition in (
                ProjectionHint.TRADE.value != "trade",
                ProjectionHint.DEPOSIT.value != "deposit",
                ProjectionHint.WITHDRAWAL.value != "withdrawal",
            )
            if condition
        ],
    ),
)
