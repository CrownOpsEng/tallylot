from __future__ import annotations

from tallylot.infrastructure.workspace.layout import SEED_FILES

from tests.support.docs_runtime_parity import (
    adapter_packs_root,
    agents_root,
    architecture_doc_paths,
    docs_root,
    forward_target_doc_paths,
    repo_root,
)


def _joined(*parts: str) -> str:
    return "".join(parts)


def test_docs_do_not_reference_retired_service_or_model_buckets() -> None:
    forbidden = (
        "application/services",
        "application/models",
        "domain/models",
        "source diff",
        "baseline validate",
        "verification compare",
        "batch stage",
        "batch screen",
        "round scaffold",
        "supporting extract-pdf-balances",
        "wallet inventory rebuild",
    )
    for path in architecture_doc_paths():
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references retired surface {needle!r}"
            )


def test_docs_use_lowercase_filenames_except_readmes() -> None:
    for path in sorted(docs_root().rglob("*")):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        assert path.name == path.name.lower(), f"doc filename is not lowercase: {path}"


def test_repo_docs_do_not_reference_personal_workspace_roots() -> None:
    forbidden = (
        "/home/user/",
        "Documents/",
        "~/Documents/",
    )
    paths = (
        repo_root() / "README.md",
        repo_root() / "AGENTS.md",
        repo_root() / "tallylot.toml",
        *sorted(docs_root().rglob("*.md")),
        *sorted(agents_root().rglob("*.md")),
        *sorted((repo_root() / ".claude").rglob("*.md")),
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references personal workspace path {needle}"
            )


def test_private_oracle_manifest_is_not_checked_in() -> None:
    assert not (
        docs_root() / "reference" / "cointracking-full-export-manifest.csv"
    ).exists()


def test_workspace_issue_log_seed_header_matches_template() -> None:
    template_header = (
        (docs_root() / "workspace" / "analysis" / "issues" / "issue-log-template.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/issue_log.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_inventory_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-inventory-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_inventory.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_captures_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "inventory"
            / "source-captures-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/inventory/source_captures.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_label_map_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-label-map-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_label_map.csv"
    )

    assert seeded_header == template_header


def test_commit_standards_require_explicit_lint_amend_reverification() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")

    assert "Do not describe `mypy` or `pyright` as covering `pylint` findings." in text
    assert "make pylint ARGS='<touched-file>'" in text
    assert "make pytest ARGS='-q --no-cov <touched-test-file>'" in text
    assert "git show HEAD:<path>" in text


def test_human_docs_retire_role_first_naming_phrases() -> None:
    forbidden = (
        "human-facing entrypoint",
        "owning concept page",
        "owning contract",
        "helper reference",
        "single authority",
        "design anchor",
        "implementation anchor",
        "owner pages",
        "primary owners",
        "authoritative owners",
    )
    paths = (repo_root() / "ROADMAP.md", *sorted(docs_root().rglob("*.md")))

    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still uses retired role-first naming phrase {needle!r}"
            )


def test_human_docs_retire_selected_target_tokens() -> None:
    forbidden = (
        "coinbase_retail_export",
        "coinbase_statement_document",
        "custodial_position",
        "support_kind",
        "missing_observation",
    )
    paths = (repo_root() / "ROADMAP.md", *sorted(docs_root().rglob("*.md")))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still uses retired target token {needle!r}"
            )


def test_target_docs_use_market_measurement_while_origin_ref_keeps_market_input() -> (
    None
):
    domain_text = (docs_root() / "concepts" / "domain-ontology.md").read_text(
        encoding="utf-8"
    )
    ids_text = (docs_root() / "reference" / "target-ids-and-refs.md").read_text(
        encoding="utf-8"
    )

    assert "`market_measurement`" in domain_text
    assert "`market_reference`" not in domain_text
    assert "`market_input`" in ids_text


def test_target_docs_use_support_shape_and_retire_checked_journal_value() -> None:
    pipeline_text = (
        docs_root() / "concepts" / "pipeline-stage-contracts.md"
    ).read_text(encoding="utf-8")
    roadmap_text = (repo_root() / "ROADMAP.md").read_text(encoding="utf-8")

    assert "support_shape" in pipeline_text
    assert "support_shape" in roadmap_text
    assert "`checked`" not in pipeline_text
    assert "Prefer `checked` over" not in (
        docs_root() / "standards" / "engineering.md"
    ).read_text(encoding="utf-8")


def test_target_docs_use_neutral_upstream_kind_tokens_and_position_key_example() -> (
    None
):
    upstream_text = (
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    ).read_text(encoding="utf-8")
    downstream_text = (
        docs_root() / "reference" / "first-downstream-slice-contract.md"
    ).read_text(encoding="utf-8")
    ontology_text = (docs_root() / "concepts" / "domain-ontology.md").read_text(
        encoding="utf-8"
    )

    assert "retail_activity_export_file" in upstream_text
    assert "statement_document_file" in upstream_text
    assert "held_position" in downstream_text
    assert "held_position" in ontology_text


def test_forward_target_docs_use_subject_key_and_no_placeholder_measure_field() -> None:
    governed_paths = (
        docs_root() / "concepts" / "gaps-and-reviews.md",
        docs_root() / "concepts" / "pipeline-stage-contracts.md",
        docs_root() / "reference" / "first-downstream-slice-contract.md",
        docs_root() / "reference" / "first-upstream-slice-contract.md",
        docs_root() / "standards" / "engineering.md",
        repo_root() / "ROADMAP.md",
    )

    for path in governed_paths:
        text = path.read_text(encoding="utf-8")
        assert "subject_id" not in text, f"{path} still uses subject_id"
        assert "measure_kind" not in text, f"{path} still uses measure_kind"


def test_forward_target_docs_freeze_new_titles_and_reference_grouping() -> None:
    docs_home = (docs_root() / "README.md").read_text(encoding="utf-8")
    gaps_text = (docs_root() / "concepts" / "gaps-and-reviews.md").read_text(
        encoding="utf-8"
    )
    recon_text = (
        docs_root() / "concepts" / "reconciliation-tax-architecture.md"
    ).read_text(encoding="utf-8")

    assert 'title: "Gap, Review, And Shared Attachment"' in gaps_text
    assert (
        'title: "Reconciliation, Checkpoint, Journal, And Tax Architecture"'
        in recon_text
    )
    assert "### Target References" in docs_home
    assert "### Current-State References" in docs_home
    assert "### Oracle References" in docs_home
    assert docs_home.index("[First Upstream Slice Contract]") < docs_home.index(
        "### Current-State References"
    )
    assert docs_home.index("[Manual Balance Submission Packages]") > docs_home.index(
        "### Current-State References"
    )
    assert docs_home.index("[CoinTracking Oracle Artifacts]") > docs_home.index(
        "### Oracle References"
    )


def test_forward_target_docs_use_kernel_scope_and_assessment_roots() -> None:
    governed_paths = (
        repo_root() / "ROADMAP.md",
        docs_root() / "concepts" / "gaps-and-reviews.md",
        docs_root() / "concepts" / "pipeline-stage-contracts.md",
        docs_root() / "concepts" / "reconciliation-tax-architecture.md",
        docs_root() / "reference" / "target-ids-and-refs.md",
        docs_root() / "reference" / "target-persistence-reference.md",
        docs_root() / "reference" / "first-downstream-slice-contract.md",
        docs_root() / "standards" / "engineering.md",
    )

    for path in governed_paths:
        text = path.read_text(encoding="utf-8")
        assert "kernel_scope_id" in text, f"{path} must use kernel_scope_id"
        assert "product_scope_id" not in text, f"{path} still uses product_scope_id"
        assert "domain/support/" not in text, f"{path} still uses domain/support/"
        assert "application/assessment/" not in text, (
            f"{path} still uses application/assessment/"
        )
        assert "application/readiness/" not in text, (
            f"{path} still uses application/readiness/"
        )
        assert "application/query/" not in text, f"{path} still uses application/query/"
        assert "application/read_models/" not in text, (
            f"{path} still uses application/read_models/"
        )


def test_forward_target_docs_use_assessment_paths_and_partition_labels() -> None:
    recon_text = (
        docs_root() / "concepts" / "reconciliation-tax-architecture.md"
    ).read_text(encoding="utf-8")
    gaps_text = (docs_root() / "concepts" / "gaps-and-reviews.md").read_text(
        encoding="utf-8"
    )
    persistence_text = (
        docs_root() / "reference" / "target-persistence-reference.md"
    ).read_text(encoding="utf-8")

    assert "assessment/gap/gap_records.json" in recon_text
    assert "assessment/review/review_records.json" in recon_text
    assert (
        "working/products/tax_outputs/<tax_outputs_id>/derived/"
        "tax_output_grouped_readiness.json" in recon_text
    )
    assert "assessment/readiness/readiness_rollup_records.json" not in recon_text
    assert "assessment/readiness/readiness_records.json" not in recon_text
    assert "checkpoint-economic-facts-lineage-scoped" in recon_text
    assert "tax-inputs-policy-year-scoped" in recon_text
    assert "checkpoint-economic-lineage-scoped" not in recon_text
    assert "tax-input-policy-year-scoped" not in recon_text
    assert "Readiness is not a shared assessment family." in gaps_text
    assert "`kernel_scope`" in gaps_text
    assert "`product_scope`" not in gaps_text
    assert "assessment view" not in gaps_text
    assert "assessment views" not in gaps_text
    assert "assessment view" not in recon_text
    assert "assessment views" not in recon_text
    assert "assessment view" not in persistence_text
    assert "assessment views" not in persistence_text
    assert (
        "working/products/tax_outputs/<tax_outputs_id>/derived/"
        "tax_output_grouped_readiness.json" in persistence_text
    )
    assert "readiness rollup" not in gaps_text.lower()
    assert "readiness rollup" not in recon_text.lower()
    assert "readiness rollup" not in persistence_text.lower()


def test_forward_target_docs_encode_phase_10_default_read_model_activation() -> None:
    roadmap_text = (repo_root() / "ROADMAP.md").read_text(encoding="utf-8")
    overview_text = (docs_root() / "concepts" / "architecture-overview.md").read_text(
        encoding="utf-8"
    )
    migration_text = (docs_root() / "status" / "migration-sequence.md").read_text(
        encoding="utf-8"
    )
    bridge_text = (docs_root() / "concepts" / "bridge-to-target-mapping.md").read_text(
        encoding="utf-8"
    )

    assert "Phase 10" in roadmap_text
    assert "Phase 10" in overview_text
    assert "Phase 10" in migration_text
    assert "Phase 10" in bridge_text
    assert "default activation point" in overview_text
    assert "default activation point" in migration_text
    assert "activation defaults to `Phase 10`" in bridge_text


def test_forward_target_docs_reserve_specific_read_model_package_names() -> None:
    roadmap_text = (repo_root() / "ROADMAP.md").read_text(encoding="utf-8")
    ontology_text = (docs_root() / "concepts" / "domain-ontology.md").read_text(
        encoding="utf-8"
    )
    engineering_text = (docs_root() / "standards" / "engineering.md").read_text(
        encoding="utf-8"
    )

    reserved_paths = (
        "application/reporting/",
        "application/portfolio/",
        "application/visualization/",
        "application/investigation/",
    )

    for reserved_path in reserved_paths:
        assert reserved_path in roadmap_text
        assert reserved_path in ontology_text
        assert reserved_path in engineering_text


def test_forward_target_docs_retire_operator_views_and_abstract_container_labels() -> (
    None
):
    for path in forward_target_doc_paths():
        text = path.read_text(encoding="utf-8")
        assert "operator views" not in text, f"{path} still uses operator views"
        assert "operator view" not in text, f"{path} still uses operator view"
        assert "emission root" not in text, f"{path} still uses emission root"
        assert "output root" not in text, f"{path} still uses output root"


def test_repo_human_docs_retire_operator_view_term() -> None:
    paths = (repo_root() / "ROADMAP.md", *sorted(docs_root().rglob("*.md")))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "operator views" not in text, f"{path} still uses operator views"
        assert "operator view" not in text, f"{path} still uses operator view"


def test_bridge_record_names_stay_inside_compatibility_local_sections() -> None:
    gaps_text = (docs_root() / "concepts" / "gaps-and-reviews.md").read_text(
        encoding="utf-8"
    )
    bridge_text = (docs_root() / "concepts" / "bridge-to-target-mapping.md").read_text(
        encoding="utf-8"
    )

    assert "**Compatibility-only locality:**" in gaps_text
    assert "**Compatibility-only locality:**" in bridge_text
    assert "IssueRecord" in gaps_text
    assert "NormalizationReviewRecord" in gaps_text
    assert "IssueRecord" in bridge_text
    assert "NormalizationReviewRecord" in bridge_text


def test_target_docs_freeze_instrument_kind_and_claim_bundle_decision_basis() -> None:
    ontology_text = (docs_root() / "concepts" / "domain-ontology.md").read_text(
        encoding="utf-8"
    )
    pipeline_text = (
        docs_root() / "concepts" / "pipeline-stage-contracts.md"
    ).read_text(encoding="utf-8")

    for value in ("unknown", "crypto", "fiat", "equity", "derivative"):
        assert f"- `{value}`" in ontology_text
    for value in (
        "single_bundle",
        "insufficient_identity",
        "insufficient_temporal_precision",
        "conflicting_claims",
        "upstream_gap",
        "policy_decision_required",
        "later_bundle_selected",
    ):
        assert f"- `{value}`" in pipeline_text


def test_commit_standards_require_scoped_subjects() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")

    assert "type(scope): imperative summary" in text
    assert "The scope is optional" not in text
    assert "required lowercase kebab-case scope" in text


def test_commit_standards_document_hybrid_pr_merge_policy() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")
    implementation_text = (docs_root() / "standards" / "implementation.md").read_text(
        encoding="utf-8"
    )
    pr_template = (repo_root() / ".github" / "pull_request_template.md").read_text(
        encoding="utf-8"
    )

    assert "`main` is a merge-commit branch by default." in text
    assert "Use squash merges only for the narrow single-commit" in text
    assert "do not squash PRs with multiple authored commits" in text
    assert "non-pushed checkpoint commit may be amended" in text
    assert "single-checkpoint exception" in implementation_text
    assert "search existing open issues first" in implementation_text
    assert "use the repo-standard issue structure" in implementation_text
    assert "Single-checkpoint PRs must squash." in pr_template


def test_implementation_anchor_references_use_explicit_doc_paths() -> None:
    paths = (
        repo_root() / "AGENTS.md",
        docs_root() / "standards" / "implementation.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert _joined("implementation", " plan") not in text.lower(), (
            f"{path} still uses vague implementation-plan wording"
        )


def test_forward_target_contract_docs_do_not_use_transient_process_terms() -> None:
    forbidden = (
        _joined("implementation", " plan"),
        _joined("execution", " plan"),
        _joined("phase", " log"),
        _joined("review", " ledger"),
        _joined("execution", " ledger"),
        _joined("phase", " ledger"),
        _joined("handoff", " prose"),
        _joined("temporary", " bookkeeping"),
        _joined("temporary", " process bookkeeping"),
        _joined("compaction", " aids"),
    )

    for path in forward_target_doc_paths():
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still uses transient process wording {needle!r}"
            )


def test_forward_target_contract_docs_do_not_use_stepwise_handoff_labels() -> None:
    forbidden = (
        _joined("follow", " this plan"),
        _joined("step", " 1"),
        _joined("step", " 2"),
        _joined("step", " 3"),
    )

    for path in forward_target_doc_paths():
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still uses stepwise handoff wording {needle!r}"
            )


def test_reference_docs_do_not_check_in_oracle_data_files() -> None:
    forbidden_suffixes = {".csv", ".json", ".zip", ".html", ".pdf"}

    for path in sorted((docs_root() / "reference").rglob("*")):
        if not path.is_file():
            continue
        assert path.suffix not in forbidden_suffixes, (
            f"repo reference docs should not contain oracle data files: {path}"
        )


def test_adapter_pack_goldens_do_not_embed_absolute_home_paths() -> None:
    forbidden = ("/home/user/", "CoinTracking.info/tallylot-2025")

    for path in sorted(adapter_packs_root().rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still embeds absolute local path content"
            )
