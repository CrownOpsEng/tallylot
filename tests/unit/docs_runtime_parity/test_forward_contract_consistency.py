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

HELPER_REF_DOC = docs_root() / "reference" / "target-ids-and-refs.md"

BRIDGE_MATRIX_HEADER = (
    "Current bridge surface",
    "Target authoritative product(s)",
    "Derived compatibility view",
    "Derived compatibility sidecar",
    "Current readers",
    "Target readers after cutover",
    "Cutover gate",
    "Retirement gate",
)

COMPLETION_GATE_TABLE_HEADER = (
    "Exit criterion",
    "Authoritative doc section(s)",
    "Automated proof",
)

EXPECTED_COMPLETION_GATE_ROWS = (
    (
        "no owner concept is defined in two competing places",
        "`docs/status/migration-sequence.md` `## Roadmap Ownership`; `docs/concepts/bridge-to-target-mapping.md` `## Scope And Related Contract Pages`; `docs/concepts/reconciliation-tax-architecture.md` `## Related Contract Pages`",
        "`test_owner_contract_pages_do_not_compete_for_the_same_authority`",
    ),
    (
        "no target product references an undefined record family or ref type",
        "`docs/concepts/pipeline-stage-contracts.md` `## Shared Contract References`; `docs/concepts/domain-ontology.md` `## Identity And Ref Seams`; `docs/concepts/gaps-and-reviews.md` `## SubjectRef`; `docs/reference/target-ids-and-refs.md` `## Origin Ref`; `docs/reference/target-ids-and-refs.md` `## Journal Refs`",
        "`test_forward_contracts_do_not_reference_undefined_record_families_or_refs`",
    ),
    (
        "no cross-stage support record or sidecar masquerades as a claim kind",
        "`docs/concepts/pipeline-stage-contracts.md` `Canonical ClaimRecord.kind values`; `docs/concepts/pipeline-stage-contracts.md` `### First-Slice Critical-Path Claim Kinds`; `docs/concepts/pipeline-stage-contracts.md` `### Derived Compatibility Sidecars`; `docs/reference/first-upstream-slice-contract.md` `## ClaimSet Coverage`",
        "`test_critical_path_claim_field_tables_are_unique_and_complete`",
    ),
    (
        "claim-stage blockers can attach to `claim_scope_id` before subject identity resolves, and later-stage blockers can attach to truthful journal or tax subjects without collapsing to kernel-scope attachment only",
        "`docs/concepts/gaps-and-reviews.md` `## SubjectRef`; `docs/concepts/gaps-and-reviews.md` `## Non-Subject Scope Ids`; `docs/concepts/pipeline-stage-contracts.md` `## ClaimSet`; `docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState`",
        "`test_gap_and_review_attachment_rules_use_truthful_scopes`",
    ),
    (
        "no target id or helper id bakes bridge-era naming into target identity",
        "`docs/concepts/pipeline-stage-contracts.md` `## EvidenceSet` stable ids; `docs/concepts/pipeline-stage-contracts.md` `## ClaimSet` stable ids; `docs/reference/first-upstream-slice-contract.md` `## Id And Fingerprint Rules`",
        "`test_downstream_identity_recipes_do_not_embed_bridge_nouns`",
    ),
    (
        "no canonical target contract keeps source-specific crypto nouns such as `wallet` when a repo-owned domain noun already owns that seam",
        "`docs/concepts/domain-ontology.md` `## Generic Model Requirements`; `docs/reference/first-upstream-slice-contract.md` observation and claim tables",
        "`test_forward_target_contracts_keep_source_specific_crypto_nouns_out_of_canonical_fields`",
    ),
    (
        "no bridge surface is left without an authority and retirement rule",
        "`docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix`; `docs/status/migration-sequence.md` `## Bridge Retirement Rules`",
        "`test_bridge_cutover_matrix_rows_are_complete`",
    ),
    (
        "no hot-path field points to an undefined value ref or sidecar",
        "`docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState`; `docs/concepts/pipeline-stage-contracts.md` `## Checkpoint`; `docs/reference/first-downstream-slice-contract.md` `## In-Scope Record Families`",
        "`test_reconciliation_and_checkpoint_hot_path_fields_use_direct_values`",
    ),
    (
        "every critical-path observation and claim kind has one authoritative kernel field table",
        "`docs/concepts/pipeline-stage-contracts.md` `### First-Slice Critical-Path Observation Kinds`; `docs/concepts/pipeline-stage-contracts.md` `### First-Slice Critical-Path Claim Kinds`; `docs/reference/first-upstream-slice-contract.md` matching field-table sections",
        "`test_critical_path_observation_field_tables_are_unique_and_complete`; `test_critical_path_claim_field_tables_are_unique_and_complete`",
    ),
    (
        "no target product ref in a product header uses `kernel_scope_id` where a product id exists",
        "`docs/concepts/pipeline-stage-contracts.md` `### Product Id And Upstream Ref Rules`; `docs/reference/first-downstream-slice-contract.md` `## Product Header And Downstream Inputs`; `docs/concepts/reconciliation-tax-architecture.md` `## Authoritative Persistence Model`",
        "`test_product_headers_use_product_ids_not_kernel_scope_id`",
    ),
    (
        "non-critical observation and claim kinds are explicitly deferred rather than left implicit",
        "`docs/concepts/pipeline-stage-contracts.md` critical-path sections; `docs/reference/first-upstream-slice-contract.md` out-of-scope and valuation-measure rules",
        "`test_noncritical_observation_and_claim_work_is_explicitly_deferred`",
    ),
    (
        "implementation placement is mechanical rather than interpretive",
        "`docs/concepts/domain-ontology.md` `## Required Package Ownership`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality`",
        "`test_forward_contracts_keep_placement_mechanical`",
    ),
    (
        "`TaxOutputs` can land without requiring a separate read-side architecture first",
        "`ROADMAP.md` `## Deferred Read-Model Activation Triggers`; `docs/concepts/architecture-overview.md` `## Runtime Posture`; `docs/concepts/reconciliation-tax-architecture.md` `## Authoritative Persistence Model`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality`",
        "`test_tax_outputs_contract_does_not_require_general_read_side_activation`",
    ),
    (
        "no shared application assessment center or shared grouped-readiness family is left as the default home for later grouped consumers",
        "`docs/concepts/domain-ontology.md` `## Required Package Ownership`; `docs/concepts/gaps-and-reviews.md` `## Readiness Locality`; `docs/concepts/reconciliation-tax-architecture.md` `### Assessment, Product-Local Detail, Compatibility, And Derived Outputs`",
        "`test_forward_contracts_keep_placement_mechanical`",
    ),
    (
        "the first upstream slice and first downstream slice can be implemented without inventing ids, claim bundles, values, or reader cutovers",
        "`docs/reference/first-upstream-slice-contract.md` `## Id And Fingerprint Rules` and `## Bridge Compatibility Views`; `docs/reference/first-downstream-slice-contract.md` `## Id And Fingerprint Rules` and `## Bridge Compatibility Views`",
        "`test_slice_contracts_freeze_ids_values_and_reader_cutovers`",
    ),
    (
        "every active bridge surface has one authoritative target owner",
        "`docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix`",
        "`test_bridge_cutover_matrix_rows_are_complete`",
    ),
    (
        "every active bridge surface has one derived compatibility rule",
        "`docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix`",
        "`test_bridge_cutover_matrix_rows_are_complete`",
    ),
    (
        "every active bridge surface names concrete current readers and concrete target readers",
        "`docs/status/migration-sequence.md` `## Canonical Current-Reader Inventory`; `docs/concepts/bridge-to-target-mapping.md` `## Cutover Matrix`",
        "`test_bridge_cutover_matrix_matches_declared_reader_inventory`; `test_bridge_cutover_matrix_target_readers_name_capability_and_authoritative_product`; `test_bridge_cutover_matrix_rows_are_complete`",
    ),
    (
        "no Phase 1 or Phase 2 doc claims authority over `TransactionFact`, `facts.csv`, `balance_snapshots.csv`, `balance_references.csv`, or `cointracking_csv`",
        "`ROADMAP.md` Phase 1. Land EvidenceSet; `ROADMAP.md` Phase 2. Land ClaimSet; `docs/status/migration-sequence.md` `### 3. First Downstream Slice`",
        "`test_early_stage_docs_do_not_claim_authority_over_later_bridge_outputs`",
    ),
    (
        "`EventLinkRecord` status is aligned between this roadmap and the first downstream slice contract",
        "`ROADMAP.md` Phase 4. Land ReconciliationState; `docs/concepts/pipeline-stage-contracts.md` `## ReconciliationState`; `docs/reference/first-downstream-slice-contract.md` `## In-Scope Record Families`",
        "`test_event_link_scope_is_consistent_across_forward_contracts`",
    ),
    (
        "the intentional looseness of Phases 6 and later is explicit and is non-blocking for Phase 0 to Phase 5 implementation",
        "`ROADMAP.md` post-Phase 5 transition note; `docs/status/migration-sequence.md` `### 5. Later Downstream Products`",
        "`test_later_phase_docs_remain_explicitly_high_level`; `test_completion_gate_maps_exit_criteria_to_authoritative_docs_and_automated_proof`",
    ),
)

EXPECTED_EXIT_CRITERIA = tuple(row[0] for row in EXPECTED_COMPLETION_GATE_ROWS)

EXPECTED_CANONICAL_CLAIM_KINDS = (
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
)

EXPECTED_FIRST_SLICE_CLAIM_KINDS = (
    "activity",
    "balance",
    "instrument",
    "location",
    "beneficial_owner",
    "valuation",
)

DEFINED_TARGET_RECORD_FAMILIES = frozenset(
    {
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
        "JournalEntryRecord",
        "PostingRecord",
        "EntryCheckRecord",
        "TaxInputRecord",
        "BasisTransitionRecord",
        "TaxOutputRecord",
        "TaxCarryForwardRecord",
        "TaxUnsupportedInputRecord",
        "GapRecord",
        "ReviewRecord",
    }
)

DEFINED_TARGET_REF_TYPES = frozenset(
    {
        "InstrumentRef",
        "LocationRef",
        "LegalOwnerRef",
        "BeneficialOwnerRef",
        "CounterpartyRef",
        "ContractRef",
        "PositionRef",
        "BasisPoolRef",
        "SubjectRef",
        "OriginRef",
        "JournalAccountRef",
        "JournalUnitRef",
    }
)

ALLOWED_CURRENT_STATE_RECORD_NAMES = frozenset(
    {"IssueRecord", "NormalizationReviewRecord"}
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_plain_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, f"missing section {start_heading!r}"
    body = match.group("body").rstrip()
    return tuple(
        _normalized(item.group("body"))
        for item in re.finditer(
            r"^- (?P<body>.*?)(?=\n- |\Z)",
            body,
            flags=re.MULTILINE | re.DOTALL,
        )
    )


def _extract_code_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    return tuple(
        _canonical_text_value(bullet)
        for bullet in _extract_plain_bullets(text, start_heading, end_heading)
    )


def _extract_labeled_code_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    body = _section(text, start_heading, end_heading)
    return tuple(re.findall(r"^- `([^`]+)`:", body, flags=re.MULTILINE))


def _split_table_line(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _extract_markdown_table(
    text: str, header_prefix: str
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    lines = text.splitlines()
    table_lines: list[str] = []
    capture = False
    for line in lines:
        if line.startswith(header_prefix):
            capture = True
        if capture:
            if not line.startswith("|"):
                break
            table_lines.append(line)
    assert len(table_lines) >= 3, (
        f"missing or truncated markdown table starting with {header_prefix!r}"
    )
    header = _split_table_line(table_lines[0])
    rows = tuple(_split_table_line(line) for line in table_lines[2:])
    return header, rows


def _extract_backticked_tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]+)`", text))


def _split_matrix_clauses(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(";") if part.strip())


def _canonical_text_value(text: str) -> str:
    return text.replace("`", "").strip()


def _section(text: str, start_heading: str, end_heading: str) -> str:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, f"missing section {start_heading!r}"
    return match.group("body")


def _bridge_matrix_rows() -> tuple[dict[str, str], ...]:
    header, rows = _extract_markdown_table(
        _text(docs_root() / "concepts" / "bridge-to-target-mapping.md"),
        "| Current bridge surface |",
    )
    assert header == BRIDGE_MATRIX_HEADER
    return tuple(
        {column: value for column, value in zip(header, row, strict=True)}
        for row in rows
    )


def _completion_gate_rows() -> tuple[tuple[str, str, str], ...]:
    header, rows = _extract_markdown_table(
        _text(repo_root() / "ROADMAP.md"),
        "| Exit criterion |",
    )
    assert header == COMPLETION_GATE_TABLE_HEADER
    return tuple(
        (exit_criterion, sections, proofs) for exit_criterion, sections, proofs in rows
    )


def test_owner_contract_pages_are_exactly_listed_in_roadmap_gate() -> None:
    roadmap_text = _text(repo_root() / "ROADMAP.md")
    assert (
        _extract_code_bullets(
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
    proof_functions = {
        name
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    }

    assert (
        _extract_plain_bullets(
            roadmap_text,
            "Exit criteria:",
            "| Exit criterion | Authoritative doc section(s) | Automated proof |",
        )
        == EXPECTED_EXIT_CRITERIA
    )
    assert _completion_gate_rows() == EXPECTED_COMPLETION_GATE_ROWS

    for _, _, proof_cell in EXPECTED_COMPLETION_GATE_ROWS:
        for proof_name in _extract_backticked_tokens(proof_cell):
            assert proof_name in proof_functions, (
                f"roadmap completion gate references missing proof {proof_name!r}"
            )


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
    reader_inventory = frozenset(
        _extract_labeled_code_bullets(
            migration_text,
            "## Canonical Current-Reader Inventory",
            "## Landing Order",
        )
    )
    used_labels: set[str] = set()

    for row in _bridge_matrix_rows():
        current_reader_labels = tuple(
            _canonical_text_value(clause)
            for clause in _split_matrix_clauses(row["Current readers"])
        )
        assert current_reader_labels, (
            f"bridge row is missing current reader labels: "
            f"{row['Current bridge surface']}"
        )
        for clause, label in zip(
            _split_matrix_clauses(row["Current readers"]),
            current_reader_labels,
            strict=True,
        ):
            assert clause.startswith("`") and clause.endswith("`"), (
                "current reader cells must use canonical inventory labels, "
                f"found {clause!r}"
            )
            assert label in reader_inventory, (
                f"bridge mapping uses undeclared current reader label {label!r}"
            )
        used_labels.update(current_reader_labels)

    assert used_labels == reader_inventory


def test_bridge_cutover_matrix_rows_are_complete() -> None:
    rows = _bridge_matrix_rows()
    assert (
        tuple(_canonical_text_value(row["Current bridge surface"]) for row in rows)
        == EXPECTED_MATRIX_ROWS
    )
    for row in rows:
        for column in (
            "Target authoritative product(s)",
            "Derived compatibility view",
            "Derived compatibility sidecar",
            "Current readers",
            "Target readers after cutover",
            "Cutover gate",
            "Retirement gate",
        ):
            assert row[column], (
                f"bridge row is missing {column.lower()}: "
                f"{row['Current bridge surface']}"
            )


def test_bridge_cutover_matrix_target_readers_name_capability_and_authoritative_product() -> (
    None
):
    for row in _bridge_matrix_rows():
        authoritative_terms = set(
            _extract_backticked_tokens(row["Target authoritative product(s)"])
        )
        if "owning target product" in row["Target authoritative product(s)"]:
            authoritative_terms.add("owning target product")

        assert authoritative_terms, (
            "bridge row must name an authoritative target owner before target readers "
            f"can be validated: {row['Current bridge surface']}"
        )

        for clause in _split_matrix_clauses(row["Target readers after cutover"]):
            if " reading " in clause:
                capability, target_text = clause.split(" reading ", 1)
            else:
                assert " from " in clause, (
                    "target reader clauses must name a capability plus "
                    f"authoritative product: {clause!r}"
                )
                capability, target_text = clause.split(" from ", 1)

            assert capability.strip().strip("`"), (
                f"target reader clause is missing a concrete capability: {clause!r}"
            )

            target_terms = set(_extract_backticked_tokens(target_text))
            if "owning target product" in target_text:
                target_terms.add("owning target product")
            assert target_terms & authoritative_terms, (
                "target reader clause must name the row's authoritative target "
                f"product: {clause!r}"
            )


def test_forward_contracts_do_not_reference_undefined_record_families_or_refs() -> None:
    authoritative_text = "\n".join(
        _text(path) for path in (*OWNER_DOCS, HELPER_REF_DOC)
    )
    ontology_text = _text(docs_root() / "concepts" / "domain-ontology.md")
    gaps_text = _text(docs_root() / "concepts" / "gaps-and-reviews.md")
    ids_refs_text = _text(HELPER_REF_DOC)

    for ref_name in (
        "InstrumentRef",
        "LocationRef",
        "LegalOwnerRef",
        "BeneficialOwnerRef",
        "CounterpartyRef",
        "ContractRef",
        "PositionRef",
        "BasisPoolRef",
    ):
        assert f"| `{ref_name}` |" in ontology_text
    assert "`SubjectRef` serializes, sorts, and fingerprints as" in gaps_text
    for ref_name in ("OriginRef", "JournalAccountRef", "JournalUnitRef"):
        assert f"`{ref_name}` identifies" in ids_refs_text

    used_record_families = {
        token
        for token in _extract_backticked_tokens(authoritative_text)
        if re.fullmatch(r"[A-Z][A-Za-z]+Record", token)
    }
    unknown_record_families = (
        used_record_families
        - DEFINED_TARGET_RECORD_FAMILIES
        - ALLOWED_CURRENT_STATE_RECORD_NAMES
    )
    assert not unknown_record_families, (
        "forward contracts reference undefined record families: "
        f"{sorted(unknown_record_families)!r}"
    )

    used_ref_types = {
        token
        for token in _extract_backticked_tokens(authoritative_text)
        if re.fullmatch(r"[A-Z][A-Za-z]+Ref", token)
    }
    unknown_ref_types = used_ref_types - DEFINED_TARGET_REF_TYPES
    assert not unknown_ref_types, (
        f"forward contracts reference undefined ref types: {sorted(unknown_ref_types)!r}"
    )


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
    canonical_claim_kinds = _extract_code_bullets(
        pipeline_text,
        "Canonical `ClaimRecord.kind` values:",
        "Controlled vocabularies:",
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
    pipeline_header, pipeline_rows = _extract_markdown_table(
        pipeline_table, "| `kind` |"
    )
    upstream_header, upstream_rows = _extract_markdown_table(
        upstream_table, "| Claim kind |"
    )

    assert canonical_claim_kinds == EXPECTED_CANONICAL_CLAIM_KINDS
    assert pipeline_header == ("`kind`", "Kind-owned kernel fields")
    assert upstream_header == ("Claim kind", "Frozen kernel fields")
    assert tuple(_canonical_text_value(row[0]) for row in pipeline_rows) == (
        EXPECTED_FIRST_SLICE_CLAIM_KINDS
    )
    assert tuple(_canonical_text_value(row[0]) for row in upstream_rows) == (
        EXPECTED_FIRST_SLICE_CLAIM_KINDS
    )
    assert _normalized(
        "Bridge or output annotation sidecar detail, shared gap/review outputs, "
        "and capability-owned readiness views are not claim kinds and are never "
        "emitted by this slice."
    ) in _normalized(upstream_text)
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
    subject_ref_section = _section(
        gaps_text, "## `SubjectRef`", "## Non-Subject Scope Ids"
    )

    for token in (
        "`selection_id`",
        "`claim_scope_id`",
        "`continuity_segment_id`",
        "`balance_target_id`",
        "`checkpoint_proposal_id`",
        "`kernel_scope_id`",
    ):
        assert token in gaps_text
    for subject_kind in (
        "journal_entry",
        "posting",
        "basis_pool",
        "tax_input",
        "tax_output",
    ):
        assert f"- `{subject_kind}`" in subject_ref_section
    assert "do not attach a gap or review to `kernel_scope` when" in gaps_text
    assert _normalized(
        "later-stage gaps and reviews may attach to `journal_entry`, `posting`, "
        "`basis_pool`, `tax_input`, or `tax_output` when that later-stage record "
        "is the truthful shared pointer"
    ) in _normalized(gaps_text)
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
