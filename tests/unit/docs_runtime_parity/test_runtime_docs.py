from __future__ import annotations

from tallylot.domain.captures import provenance_locator_header
from tallylot.ports.source_profiles import PROFILE_INVENTORY_HEADER

from tests.support.docs_runtime_parity import docs_root


def test_current_state_mentions_capture_and_assembly_runtime_surfaces() -> None:
    text = (docs_root() / "status" / "current-state.md").read_text(encoding="utf-8")

    for needle in (
        "capture registry",
        "working/normalized/captures/<capture_uid>/",
        "working/normalized/sources/<source>/",
        "shared statement extraction",
        "tools.validate_workspace_replay",
        "expected-difference fixtures",
    ):
        assert needle in text


def test_updated_workspace_and_operator_docs_drop_legacy_capture_and_normalized_paths() -> (
    None
):
    paths = (
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "source-intake.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
        docs_root() / "guides" / "full-operator-workflow.md",
        docs_root() / "workspace" / "evidence" / "raw" / "source" / "README.md",
        docs_root() / "workspace" / "working" / "normalized" / "README.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "<capture_id>" not in text
        assert "working/normalized/<source>" not in text


def test_runtime_docs_require_materialized_capture_roots_for_profile_and_normalize() -> (
    None
):
    paths = (
        docs_root() / "status" / "current-state.md",
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "source-intake.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
        docs_root() / "guides" / "full-operator-workflow.md",
        docs_root() / "workspace" / "evidence" / "raw" / "source" / "README.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "capture.json" in text
        assert ("materialized" in text and "capture root" in text) or (
            "exact capture root" in text
        )


def test_runtime_docs_pin_profile_inventory_capture_scoped_fields() -> None:
    text = (
        docs_root() / "workspace" / "working" / "normalized" / "README.md"
    ).read_text(encoding="utf-8")

    for field in (
        "capture_uid",
        "source",
        "evidence_role",
        "observed_period_start",
        "observed_period_end",
        "observed_period_label",
        "statement_kind",
        "originality_class",
    ):
        assert f"`{field}`" in text
        assert field in PROFILE_INVENTORY_HEADER


def test_runtime_docs_pin_flattened_provenance_locator_columns() -> None:
    normalized_text = (
        docs_root() / "workspace" / "working" / "normalized" / "README.md"
    ).read_text(encoding="utf-8")
    inventory_text = (
        docs_root() / "reference" / "location-inventory-artifacts.md"
    ).read_text(encoding="utf-8")

    for column in provenance_locator_header():
        assert f"`{column}`" in normalized_text
    for column in provenance_locator_header("raw"):
        assert f"`{column}`" in normalized_text
    for column in provenance_locator_header("evidence"):
        assert f"`{column}`" in inventory_text


def test_runtime_docs_pin_deterministic_source_assembly_reruns() -> None:
    paths = (
        docs_root() / "status" / "current-state.md",
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "source-intake.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
        docs_root() / "guides" / "full-operator-workflow.md",
        docs_root() / "workspace" / "working" / "normalized" / "README.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        assert "rerun" in text
        assert "rewrite" in text


def test_runtime_docs_pin_workspace_replay_expected_difference_limits() -> None:
    text = (docs_root() / "status" / "current-state.md").read_text(encoding="utf-8")

    for field in ("issue_count_delta", "review_count_delta", "reason"):
        assert f"`{field}`" in text
    assert "fact_count_delta" not in text


def test_manual_balance_submission_docs_mention_checkpoint_commands() -> None:
    paths = (
        docs_root() / "reference" / "manual-balance-submission-artifacts.md",
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "checkpoint scaffold-balance-submission" in text
        assert "checkpoint submit-balances" in text


def test_workspace_docs_reference_manual_balance_submission_paths() -> None:
    workspace_home = (docs_root() / "workspace" / "README.md").read_text(
        encoding="utf-8"
    )
    supporting_text = (
        docs_root() / "workspace" / "working" / "supporting_artifacts" / "README.md"
    ).read_text(encoding="utf-8")
    package_text = (
        docs_root()
        / "workspace"
        / "working"
        / "supporting_artifacts"
        / "balance_submissions"
        / "README.md"
    ).read_text(encoding="utf-8")

    assert (
        "working/supporting_artifacts/balance_submissions/README.md" in workspace_home
    )
    assert "balance_submissions/README.md" in supporting_text
    assert "working/supporting_artifacts/balance_submissions/<source>/" in package_text


def test_reconciliation_workspace_docs_mention_cross_source_sidecars() -> None:
    text = (
        docs_root() / "workspace" / "analysis" / "reconciliation" / "README.md"
    ).read_text(encoding="utf-8")

    for artifact in (
        "cross_source_assertions.csv",
        "cross_source_issues.csv",
        "cross_source_summary.json",
    ):
        assert artifact in text


def test_first_slice_contract_pins_all_retained_compatibility_surfaces() -> None:
    text = (docs_root() / "reference" / "first-slice-contract.md").read_text(
        encoding="utf-8"
    )

    for needle in (
        "`translation_input_plan.json` content",
        "`EconomicActivityDraft` ordering and content for evidence in this slice",
        "`SourceTranslationBatch` content for evidence in this slice",
        "Retained compatibility projections are part of the slice parity bar.",
        "legacy readers remain active.",
    ):
        assert needle in text


def test_first_downstream_slice_contract_pins_fact_csv_projection_parity() -> None:
    text = (docs_root() / "reference" / "first-downstream-slice-contract.md").read_text(
        encoding="utf-8"
    )

    for needle in (
        "`TransactionFact` and `facts.csv` derived from `EconomicFacts`",
        "`facts.csv` content for evidence in this slice",
        "Retained compatibility projections are part of the slice parity bar.",
        "legacy readers remain active.",
    ):
        assert needle in text
