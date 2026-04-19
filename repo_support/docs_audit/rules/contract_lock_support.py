from __future__ import annotations

import re
from pathlib import Path

from repo_support.paths import repo_root
from repo_support.target_naming.catalog import load_target_naming_catalog

from ..helpers import (
    canonical_text_value,
    docs_path,
    extract_backticked_tokens,
    extract_code_bullets,
    extract_labeled_code_bullets,
    extract_markdown_table,
    extract_plain_bullets,
    normalized,
    section,
    split_matrix_clauses,
)

OWNER_DOCS = (
    repo_root() / "ROADMAP.md",
    docs_path("status/migration-sequence.md"),
    docs_path("concepts/bridge-to-target-mapping.md"),
    docs_path("concepts/pipeline-stage-contracts.md"),
    docs_path("concepts/domain-ontology.md"),
    docs_path("concepts/gaps-and-reviews.md"),
    docs_path("concepts/reconciliation-tax-architecture.md"),
    docs_path("reference/first-upstream-slice-contract.md"),
    docs_path("reference/first-downstream-slice-contract.md"),
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
HELPER_REF_DOC = docs_path("reference/target-ids-and-refs.md")
BRIDGE_MATRIX_SPEC = next(
    spec
    for spec in load_target_naming_catalog().matrix_specs
    if spec.path == "docs/concepts/bridge-to-target-mapping.md"
)
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
EXPECTED_EXIT_CRITERIA = (
    "no owner concept is defined in two competing places",
    "no target product references an undefined record family or ref type",
    "no cross-stage support record or sidecar masquerades as a claim kind",
    "claim-stage blockers can attach to `claim_scope_id` before subject identity resolves, and later-stage blockers can attach to truthful journal or tax subjects without collapsing to kernel-scope attachment only",
    "no target id or helper id bakes bridge-era naming into target identity",
    "no canonical target contract keeps source-specific crypto nouns such as `wallet` when a repo-owned domain noun already owns that seam",
    "no bridge surface is left without an authority and retirement rule",
    "no hot-path field points to an undefined value ref or sidecar",
    "every critical-path observation and claim kind has one authoritative kernel field table",
    "no target product ref in a product header uses `kernel_scope_id` where a product id exists",
    "non-critical observation and claim kinds are explicitly deferred rather than left implicit",
    "implementation placement is mechanical rather than interpretive",
    "`TaxOutputs` can land without requiring a separate read-side architecture first",
    "no shared application assessment center or shared grouped-readiness family is left as the default home for later grouped consumers",
    "the first upstream slice and first downstream slice can be implemented without inventing ids, claim bundles, values, or reader cutovers",
    "every active bridge surface has one authoritative target owner",
    "every active bridge surface has one derived compatibility rule",
    "every active bridge surface names concrete current readers and concrete target readers",
    "no Phase 1 or Phase 2 doc claims authority over `TransactionFact`, `facts.csv`, `balance_snapshots.csv`, `balance_references.csv`, or `cointracking_csv`",
    "`EventLinkRecord` status is aligned between this roadmap and the first downstream slice contract",
    "the intentional looseness of Phases 6 and later is explicit and is non-blocking for Phase 0 to Phase 5 implementation",
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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def completion_gate_rows() -> tuple[tuple[str, str, str], ...]:
    header, rows = extract_markdown_table(
        text(repo_root() / "ROADMAP.md"), "| Exit criterion |"
    )
    if header != COMPLETION_GATE_TABLE_HEADER:
        raise AssertionError("completion gate table header drifted")
    return tuple(
        (exit_criterion, sections, proofs) for exit_criterion, sections, proofs in rows
    )


def bridge_matrix_rows() -> tuple[dict[str, str], ...]:
    header, rows = extract_markdown_table(
        text(docs_path("concepts/bridge-to-target-mapping.md")),
        "| Current bridge surface |",
    )
    if header != BRIDGE_MATRIX_HEADER:
        raise AssertionError("bridge cutover matrix header drifted")
    return tuple(
        {column: value for column, value in zip(header, row, strict=True)}
        for row in rows
    )


def placeholder_text(value: str) -> bool:
    lowered = value.casefold()
    return any(token in lowered for token in ("todo", "later", "maybe", "tbd"))


def reader_inventory() -> tuple[str, ...]:
    return extract_labeled_code_bullets(
        text(docs_path("status/migration-sequence.md")),
        "## Canonical Current-Reader Inventory",
        "## Landing Order",
    )


def authoritative_contract_text() -> str:
    return "\n".join(text(path) for path in (*OWNER_DOCS, HELPER_REF_DOC))


def used_record_families() -> set[str]:
    return {
        token
        for token in extract_backticked_tokens(authoritative_contract_text())
        if re.fullmatch(r"[A-Z][A-Za-z]+Record", token)
    }


def used_ref_types() -> set[str]:
    return {
        token
        for token in extract_backticked_tokens(authoritative_contract_text())
        if re.fullmatch(r"[A-Z][A-Za-z]+Ref", token)
    }


def reader_inventory_checks() -> tuple[bool, bool]:
    inventory = reader_inventory()
    return (
        inventory != BRIDGE_MATRIX_SPEC.current_reader_inventory,
        frozenset(
            label
            for row in bridge_matrix_rows()
            for label in (
                canonical_text_value(clause)
                for clause in split_matrix_clauses(row["Current readers"])
            )
        )
        != frozenset(inventory),
    )


__all__ = [
    "ALLOWED_CURRENT_STATE_RECORD_NAMES",
    "BRIDGE_MATRIX_SPEC",
    "DEFINED_TARGET_RECORD_FAMILIES",
    "DEFINED_TARGET_REF_TYPES",
    "EXPECTED_EXIT_CRITERIA",
    "EXPECTED_MATRIX_ROWS",
    "EXPECTED_OWNER_DOCS",
    "HELPER_REF_DOC",
    "OWNER_DOCS",
    "bridge_matrix_rows",
    "canonical_text_value",
    "completion_gate_rows",
    "docs_path",
    "extract_backticked_tokens",
    "extract_code_bullets",
    "extract_labeled_code_bullets",
    "extract_plain_bullets",
    "normalized",
    "placeholder_text",
    "repo_root",
    "authoritative_contract_text",
    "reader_inventory",
    "reader_inventory_checks",
    "section",
    "split_matrix_clauses",
    "text",
    "used_record_families",
    "used_ref_types",
]
