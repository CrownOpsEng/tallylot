from __future__ import annotations

import re
from pathlib import Path

from tests.support.docs_runtime_parity import docs_root, repo_root

OWNER_DOCS = (
    repo_root() / "ROADMAP.md",
    docs_root() / "status" / "migration-sequence.md",
    docs_root() / "concepts" / "bridge-to-target-mapping.md",
    docs_root() / "concepts" / "pipeline-stage-contracts.md",
    docs_root() / "concepts" / "domain-ontology.md",
    docs_root() / "concepts" / "gaps-and-reviews.md",
    docs_root() / "concepts" / "reconciliation-tax-architecture.md",
    docs_root() / "reference" / "first-upstream-slice-contract.md",
    docs_root() / "reference" / "first-downstream-slice-contract.md",
)

FORWARD_TARGET_DEPENDENTS = (
    docs_root() / "concepts" / "architecture-overview.md",
    docs_root() / "reference" / "target-ids-and-refs.md",
    docs_root() / "reference" / "target-persistence-reference.md",
    docs_root() / "status" / "adapter-delivery-plan.md",
    docs_root() / "concepts" / "oracle-boundaries.md",
    docs_root() / "concepts" / "unified-adapter-architecture.md",
    docs_root() / "concepts" / "transaction-classification.md",
)

EXPECTED_OWNER_DOCS = (
    "ROADMAP.md",
    "docs/status/migration-sequence.md",
    "docs/concepts/bridge-to-target-mapping.md",
    "docs/concepts/pipeline-stage-contracts.md",
    "docs/concepts/domain-ontology.md",
    "docs/concepts/gaps-and-reviews.md",
    "docs/concepts/reconciliation-tax-architecture.md",
    "docs/reference/first-upstream-slice-contract.md",
    "docs/reference/first-downstream-slice-contract.md",
)

EXPECTED_MATRIX_ROWS = (
    "translation_input_candidates.json",
    "translation_input_plan.json",
    "EconomicActivityDraft",
    "SourceTranslationBatch",
    "TransactionFact and facts.csv",
    "balance_snapshots.csv",
    "balance_references.csv",
    "exceptions.csv and IssueRecord outputs",
    "normalization_reviews.csv and NormalizationReviewRecord outputs",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, f"missing section {start_heading!r}"
    return tuple(
        bullet.strip()
        for bullet in re.findall(
            r"^- `(.*?)`$", match.group("body"), flags=re.MULTILINE
        )
    )


def _bridge_matrix_rows() -> tuple[tuple[str, ...], ...]:
    text = _text(docs_root() / "concepts" / "bridge-to-target-mapping.md")
    lines = text.splitlines()
    table_lines: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("| Current bridge surface |"):
            capture = True
        if capture:
            if not line.startswith("|"):
                break
            table_lines.append(line)
    assert len(table_lines) >= 3, "bridge cutover matrix is missing or truncated"
    rows: list[tuple[str, ...]] = []
    for line in table_lines[2:]:
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        rows.append(cells)
    return tuple(rows)


def _canonical_matrix_value(text: str) -> str:
    return text.replace("`", "").strip()


def _section(text: str, start_heading: str, end_heading: str) -> str:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, f"missing section {start_heading!r}"
    return match.group("body")


def test_owner_contract_pages_are_exactly_listed_in_roadmap_gate() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    assert (
        _extract_bullets(
            roadmap_text,
            "Owner docs that must align before broad implementation begins:",
            "Exit criteria:",
        )
        == EXPECTED_OWNER_DOCS
    )


def test_completion_gate_maps_exit_criteria_to_authoritative_docs_and_automated_proof() -> (
    None
):
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    normalized = _normalized(roadmap_text)

    assert (
        "| Exit criterion | Authoritative doc section(s) | Automated proof |"
        in roadmap_text
    )
    assert (
        "test_owner_contract_pages_do_not_compete_for_the_same_authority"
        in roadmap_text
    )
    assert "test_bridge_cutover_matrix_rows_are_complete" in roadmap_text
    assert "test_product_headers_use_product_ids_not_kernel_scope_id" in roadmap_text
    assert (
        "test_event_link_scope_is_consistent_across_forward_contracts" in roadmap_text
    )
    assert "test_later_phase_docs_remain_explicitly_high_level" in roadmap_text
    assert "Exit criteria:" in normalized


def test_owner_contract_pages_do_not_compete_for_the_same_authority() -> None:
    migration_text = _text(docs_root() / "status" / "migration-sequence.md")
    bridge_text = _text(docs_root() / "concepts" / "bridge-to-target-mapping.md")
    recon_text = _text(docs_root() / "concepts" / "reconciliation-tax-architecture.md")

    assert _normalized(
        "[ROADMAP.md](../../ROADMAP.md) is the only numbered implementation program of\nrecord."
    ) in _normalized(migration_text)
    assert (
        "It does not redefine target product contracts or recreate roadmap phase detail."
        in _normalized(migration_text)
    )
    assert (
        "It does not redefine live bridge truth or target product contracts."
        in _normalized(bridge_text)
    )
    assert "This page does not redefine every lower-level contract." in _normalized(
        recon_text
    )
    assert "The authoritative cutover matrix lives in" in migration_text


def test_bridge_cutover_matrix_matches_declared_reader_inventory() -> None:
    migration_text = _text(docs_root() / "status" / "migration-sequence.md")
    bridge_text = _text(docs_root() / "concepts" / "bridge-to-target-mapping.md")
    reader_labels = tuple(
        label
        for label in re.findall(
            r"^- `([^`]+)`",
            _section(
                migration_text,
                "## Canonical Current-Reader Inventory",
                "## Landing Order",
            ),
            flags=re.MULTILINE,
        )
    )

    for label in reader_labels:
        assert f"`{label}`" in bridge_text, (
            f"bridge mapping is missing reader label {label!r}"
        )


def test_bridge_cutover_matrix_rows_are_complete() -> None:
    rows = _bridge_matrix_rows()
    assert (
        tuple(_canonical_matrix_value(row[0]) for row in rows) == EXPECTED_MATRIX_ROWS
    )
    for row in rows:
        assert row[4], f"bridge row is missing current readers: {row[0]}"
        assert row[5], f"bridge row is missing target readers: {row[0]}"
        assert row[6], f"bridge row is missing cutover gate: {row[0]}"
        assert row[7], f"bridge row is missing retirement gate: {row[0]}"


def test_forward_contracts_do_not_reference_undefined_record_families_or_refs() -> None:
    authoritative_text = "\n".join(_text(path) for path in OWNER_DOCS)
    required_tokens = (
        "EvidenceSelectionRecord",
        "EvidenceMemberRecord",
        "EvidenceObservationRecord",
        "ClaimRecord",
        "ClaimBundleRecord",
        "ClaimBundleDecisionRecord",
        "EconomicEventRecord",
        "EconomicLegRecord",
        "ValuationRecord",
        "ContinuitySegmentRecord",
        "EventLinkRecord",
        "BalanceTargetRecord",
        "CheckpointProposalRecord",
        "CheckpointRecord",
        "CheckpointAssertionRecord",
        "GapRecord",
        "GapExplanation",
        "ReviewRecord",
        "ReviewExplanation",
        "AssertionValue",
        "PositionRef",
        "ContractRef",
        "SubjectRef",
    )
    for token in required_tokens:
        assert token in authoritative_text, f"forward contracts never define {token}"


def test_critical_path_observation_field_tables_are_unique_and_complete() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    upstream_text = _text(
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    )
    pipeline_table = _section(
        pipeline_text,
        "### First-Slice Critical-Path Observation Kinds",
        "Stable ids:",
    )
    upstream_table = _section(
        upstream_text,
        "Frozen kind-specific observation fields:",
        "Observation-field rules:",
    )

    for text in (pipeline_table, upstream_table):
        assert text.count("| `statement_document` |") == 1
        assert text.count("| `statement_balance_row` |") == 1
        assert "statement_kind" in text
        assert "location_group_label" in text
        assert "price_currency" in text


def test_critical_path_claim_field_tables_are_unique_and_complete() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    upstream_text = _text(
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    )
    pipeline_table = _section(
        pipeline_text,
        "### First-Slice Critical-Path Claim Kinds",
        "`leg_specs` entry shape:",
    )
    upstream_table = _section(
        upstream_text,
        "Frozen kind-specific claim fields:",
        "`leg_specs` entry shape:",
    )

    required_rows = (
        "| `activity` |",
        "| `balance` |",
        "| `instrument` |",
        "| `location` |",
        "| `beneficial_owner` |",
        "| `valuation` |",
    )
    for row in required_rows:
        assert pipeline_table.count(row) == 1
        assert upstream_table.count(row) == 1
    assert "`leg_specs` entry shape:" in pipeline_text
    assert "`leg_specs` entry shape:" in upstream_text


def test_noncritical_observation_and_claim_work_is_explicitly_deferred() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    upstream_text = _text(
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    )

    assert (
        "no new observation kind may be implemented until this page or the owning\n  slice page defines its kernel field table explicitly"
        in pipeline_text
    )
    assert (
        "no non-critical claim kind may be implemented until this page or the\n  owning slice page defines its kernel field table explicitly"
        in pipeline_text
    )
    assert "valuation-measure taxonomy is intentionally deferred" in pipeline_text
    assert "valuation-measure taxonomy remains intentionally deferred" in upstream_text
    assert "`valuation` claims remain zero-row by default" in upstream_text


def test_reconciliation_and_checkpoint_hot_path_fields_use_direct_values() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    downstream_text = _text(
        docs_root() / "reference" / "first-downstream-slice-contract.md"
    )

    assert "`expected_value`" in pipeline_text
    assert "`observed_value`" in pipeline_text
    assert "`accepted_value`" in pipeline_text
    assert (
        "use value refs that point to undefined sidecar values outside the kernel"
        in pipeline_text
    )
    assert "`expected_value_ref`" in downstream_text
    assert "`observed_value_ref`" in downstream_text
    assert "Not allowed in this slice:" in downstream_text


def test_gap_and_review_attachment_rules_use_truthful_scopes() -> None:
    gaps_text = _text(docs_root() / "concepts" / "gaps-and-reviews.md")
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")

    for token in (
        "`selection_id`",
        "`claim_scope_id`",
        "`continuity_segment_id`",
        "`balance_target_id`",
        "`checkpoint_proposal_id`",
        "`kernel_scope_id`",
    ):
        assert token in gaps_text
    assert "do not attach a gap or review to `kernel_scope` when" in gaps_text
    assert (
        "claim-stage gaps and reviews may attach to `claim_scope_id`" in pipeline_text
    )
    assert (
        "reconciliation-stage gaps and reviews may attach to `balance_target_id`"
        in pipeline_text
    )


def test_forward_contracts_keep_placement_mechanical() -> None:
    ontology_text = _text(docs_root() / "concepts" / "domain-ontology.md")
    gaps_text = _text(docs_root() / "concepts" / "gaps-and-reviews.md")

    for package_path in (
        "`domain/assessment/`",
        "`application/compatibility/`",
        "`application/claim/`",
        "`application/economics/`",
        "`application/reconciliation/`",
        "`application/checkpoint/`",
        "`application/journal/`",
        "`application/tax/`",
    ):
        assert package_path in ontology_text
    assert "Readiness is not a shared assessment family." in gaps_text
    assert "do not create a shared readiness record family" in gaps_text


def test_product_headers_use_product_ids_not_kernel_scope_id() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    downstream_text = _text(
        docs_root() / "reference" / "first-downstream-slice-contract.md"
    )
    recon_text = _text(docs_root() / "concepts" / "reconciliation-tax-architecture.md")

    assert (
        "upstream product refs use product ids only; they never use\n  `kernel_scope_id`"
        in pipeline_text
    )
    assert "store target product ids, never\n  `kernel_scope_id`" in downstream_text
    assert (
        "upstream `*_ref` fields in the product header store product ids, never `kernel_scope_id`"
        in recon_text
    )


def test_downstream_identity_recipes_do_not_embed_bridge_nouns() -> None:
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    upstream_text = _text(
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    )

    assert (
        "source_slug` and `adapter_id` remain evidence-local identity inputs and do\n  not reappear in downstream product ids once `evidence_set_ref` is available"
        in pipeline_text
    )
    assert (
        "downstream products keep claim lineage through `claim_set_ref` or\n  `claim_set_refs`; they do not copy `source_slug`, `adapter_id`, or\n  `emitter_id` into later product ids"
        in pipeline_text
    )
    assert (
        "`source_slug` is evidence-local only; it must not become a downstream product\n  id component"
        in upstream_text
    )


def test_slice_contracts_freeze_ids_values_and_reader_cutovers() -> None:
    upstream_text = _text(
        docs_root() / "reference" / "first-upstream-slice-contract.md"
    )
    downstream_text = _text(
        docs_root() / "reference" / "first-downstream-slice-contract.md"
    )

    for text in (upstream_text, downstream_text):
        assert "## Id And Fingerprint Rules" in text
        assert "## Bridge Compatibility Views" in text
        assert "## Parity Gates" in text
        assert "## Replay Gates" in text


def test_forward_target_contracts_keep_source_specific_crypto_nouns_out_of_canonical_fields() -> (
    None
):
    texts = "\n".join(_text(path) for path in (*OWNER_DOCS, *FORWARD_TARGET_DEPENDENTS))
    assert "wallet_label" not in texts
    assert "account_label" not in texts
    assert "location_group_label" in texts
    assert "location_label" in texts
    ontology_text = _text(docs_root() / "concepts" / "domain-ontology.md")
    assert (
        "source-specific crypto nouns such as `wallet`, `exchange`, `address`,"
        in ontology_text
    )


def test_early_stage_docs_do_not_claim_authority_over_later_bridge_outputs() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    phase_1 = _section(
        roadmap_text, "## Phase 1. Land `EvidenceSet`", "## Phase 2. Land `ClaimSet`"
    )
    phase_2 = _section(
        roadmap_text, "## Phase 2. Land `ClaimSet`", "## Phase 3. Land `EconomicFacts`"
    )

    forbidden = (
        "TransactionFact",
        "facts.csv",
        "balance_snapshots.csv",
        "balance_references.csv",
        "cointracking_csv",
    )
    for needle in forbidden:
        assert needle not in phase_1
        assert needle not in phase_2


def test_event_link_scope_is_consistent_across_forward_contracts() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    pipeline_text = _text(docs_root() / "concepts" / "pipeline-stage-contracts.md")
    downstream_text = _text(
        docs_root() / "reference" / "first-downstream-slice-contract.md"
    )

    assert (
        "`EventLinkRecord` when a later in-phase reconciliation increment needs\n  explicit event linkage"
        in roadmap_text
    )
    assert "`EventLinkRecord`" in pipeline_text
    assert (
        "`EventLinkRecord` remains out of scope for this slice and may land only in a\nlater in-phase reconciliation increment."
        in downstream_text
    )


def test_tax_outputs_contract_does_not_require_general_read_side_activation() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    overview_text = _text(docs_root() / "concepts" / "architecture-overview.md")
    recon_text = _text(docs_root() / "concepts" / "reconciliation-tax-architecture.md")
    gaps_text = _text(docs_root() / "concepts" / "gaps-and-reviews.md")

    assert "tax-output-local derived content" in _normalized(overview_text)
    assert (
        "tax-output-local, narrow rendering-local, or compatibility-local derived output"
        in _normalized(recon_text)
    )
    assert "TaxOutputs`-local grouped readiness output" in _normalized(gaps_text)
    assert "Trigger A. Second Grouped Non-Compatibility Consumer" in roadmap_text


def test_later_phase_docs_remain_explicitly_high_level() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    migration_text = _text(docs_root() / "status" / "migration-sequence.md")

    assert (
        "Phases 6 and later remain intentionally high-level in this round."
        in roadmap_text
    )
    assert (
        "Phases 6 and later remain intentionally high-level in this round. They are\nout of scope for this repair"
        in migration_text
    )
