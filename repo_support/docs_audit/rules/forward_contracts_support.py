from __future__ import annotations

import re
from pathlib import Path

from repo_support.paths import repo_root

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
EXPECTED_OWNER_DOCS = tuple(
    path.relative_to(repo_root()).as_posix() for path in OWNER_DOCS
)
OWNER_DOC_SET = frozenset(EXPECTED_OWNER_DOCS)

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
BRIDGE_MATRIX_REQUIRED_NONEMPTY_COLUMNS = (
    "Target authoritative product(s)",
    "Derived compatibility view",
    "Derived compatibility sidecar",
    "Current readers",
    "Target readers after cutover",
    "Cutover gate",
    "Retirement gate",
)
BRIDGE_MATRIX_ALLOWED_SHAPES = frozenset(
    {"compatibility view", "compatibility sidecar", "none"}
)
BRIDGE_MATRIX_TARGET_READER_PLACEHOLDER_CAPABILITIES = frozenset(
    {
        "reader",
        "readers",
        "consumer",
        "consumers",
        "capability",
        "capabilities",
        "target reader",
        "target readers",
        "future reader",
        "future readers",
        "future consumer",
        "future consumers",
        "future capability",
        "future capabilities",
        "application surface",
        "application surfaces",
        "package root",
        "package roots",
        "read model",
        "read models",
        "future read model",
        "future read models",
    }
)
BRIDGE_MATRIX_BANNED_FRAGMENTS = frozenset(
    {
        "view or sidecar",
        "optional planner review view",
        "planning sidecar",
        "statement-facing compatibility sidecar",
        "recognized statement parse outputs and balance rows",
        "source translation boundary",
        "current bridge balance reducers",
        "current bridge balance-reference path",
        "bridge/output compatibility sidecars",
        "target products",
        "target product plus shared gap/review/readiness records",
        "issue compatibility view",
        "review compatibility view",
    }
)
COMPLETION_GATE_TABLE_HEADER = (
    "Exit criterion",
    "Authoritative doc section(s)",
    "Automated proof",
)
ALLOWED_PROOF_TOKEN_PREFIXES = frozenset({"docs-audit", "target-naming"})

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

HEADING_PATTERN = re.compile(r"^(#{1,6} .+)$", re.MULTILINE)
TOKEN_PATTERN = re.compile(r"(?P<fence>`+)(?P<token>.*?)(?P=fence)")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def must_freeze_items() -> tuple[str, ...]:
    return extract_plain_bullets(
        text(repo_root() / "ROADMAP.md"),
        "Must freeze:",
        "Deliver:",
    )


def completion_gate_criteria() -> tuple[str, ...]:
    return extract_plain_bullets(
        text(repo_root() / "ROADMAP.md"),
        "Exit criteria:",
        "| Exit criterion | Authoritative doc section(s) | Automated proof |",
    )


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
    return "\n".join(text(path) for path in OWNER_DOCS)


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


def heading_occurrence_count(path_text: str, heading: str) -> int:
    return sum(
        1 for match in HEADING_PATTERN.finditer(path_text) if match.group(1) == heading
    )


def authority_entries(authority_cell: str) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for clause in split_matrix_clauses(authority_cell):
        tokens = tuple(
            match.group("token").strip() for match in TOKEN_PATTERN.finditer(clause)
        )
        if len(tokens) != 2 or TOKEN_PATTERN.sub("", clause).strip():
            raise AssertionError(
                "authority cells must use exact semicolon-separated `path` `heading` pairs only"
            )
        path, heading = tokens
        entries.append((path, heading))
    if not entries:
        raise AssertionError(
            "authority cells must list one or more exact owner-doc headings"
        )
    return tuple(entries)


def proof_tokens(proof_cell: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for clause in split_matrix_clauses(proof_cell):
        clause_tokens = tuple(
            match.group("token").strip() for match in TOKEN_PATTERN.finditer(clause)
        )
        if len(clause_tokens) != 1 or TOKEN_PATTERN.sub("", clause).strip():
            raise AssertionError(
                "proof cells must use exact semicolon-separated backticked proof tokens only"
            )
        tokens.append(clause_tokens[0])
    if not tokens:
        raise AssertionError("proof cells must list one or more proof tokens")
    return tuple(tokens)


def reader_inventory_checks() -> tuple[bool, bool]:
    inventory = reader_inventory()
    return (
        inventory
        != (
            "source normalize planner review and translation path",
            "source assemble bridge projection path",
            "operator review diagnostics",
            "reconciliation balances inspect",
            "reconciliation balances check",
            "reconciliation balances summarize",
            "cointracking_csv rendering path",
            "dev-only oracle comparison path",
        ),
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
    "ALLOWED_PROOF_TOKEN_PREFIXES",
    "BRIDGE_MATRIX_ALLOWED_SHAPES",
    "BRIDGE_MATRIX_BANNED_FRAGMENTS",
    "BRIDGE_MATRIX_HEADER",
    "BRIDGE_MATRIX_REQUIRED_NONEMPTY_COLUMNS",
    "BRIDGE_MATRIX_TARGET_READER_PLACEHOLDER_CAPABILITIES",
    "COMPLETION_GATE_TABLE_HEADER",
    "DEFINED_TARGET_RECORD_FAMILIES",
    "DEFINED_TARGET_REF_TYPES",
    "EXPECTED_MATRIX_ROWS",
    "EXPECTED_OWNER_DOCS",
    "OWNER_DOC_SET",
    "OWNER_DOCS",
    "authoritative_contract_text",
    "authority_entries",
    "bridge_matrix_rows",
    "canonical_text_value",
    "completion_gate_criteria",
    "completion_gate_rows",
    "docs_path",
    "extract_backticked_tokens",
    "extract_code_bullets",
    "extract_labeled_code_bullets",
    "extract_plain_bullets",
    "heading_occurrence_count",
    "must_freeze_items",
    "normalized",
    "placeholder_text",
    "proof_tokens",
    "reader_inventory",
    "reader_inventory_checks",
    "repo_root",
    "section",
    "split_matrix_clauses",
    "text",
    "used_record_families",
    "used_ref_types",
]
