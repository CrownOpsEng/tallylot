from __future__ import annotations

from repo_support.docs_audit.rules import forward_contracts_support as support
from repo_support.docs_audit.rules._common import build_rule

_REQUIRED_JOURNAL_CONTRACT_HEADINGS = (
    "## Backend Seam And Ownership",
    "## Declared Journal Detail And Backend Artifacts",
    "## Validation Lanes",
    "## Idempotent Rerun Guarantees",
)
_REQUIRED_JOURNAL_CONTRACT_NEEDLES = (
    "`application/accounting/` owns canonical journal construction",
    "`ports/accounting_backends.py` owns `AccountingBackend` and\n  `AccountingBackendRegistryPort`",
    "`infrastructure/ledger_cli/` owns the first backend implementation",
    "`working/products/journals/<journal_id>/journal_posting_explanations.json`",
    "`working/products/journals/<journal_id>/journal_entry_check_reports.json`",
    "`working/products/journals/<journal_id>/backends/ledger_cli/journal.ledger`",
    "`working/products/journals/<journal_id>/backends/ledger_cli/validation_findings.json`",
    (
        "`print`, `accounts`, `balance`, and `register` outputs are generated "
        "on\n"
        "  demand for accounting inspection and verification; they are not "
        "durable\n"
        "  Phase 6 artifacts"
    ),
    "`ledger-cli` does not mint ids, define tax identity, or become authoritative\n  storage",
)


def _journal_contract_text() -> str:
    return support.text(support.docs_path("reference/journal-contract.md"))


def _journal_contract_has_required_headings() -> bool:
    text = _journal_contract_text()
    return all(heading in text for heading in _REQUIRED_JOURNAL_CONTRACT_HEADINGS)


FORWARD_CONTRACTS_JOURNAL_RULES = (
    build_rule(
        "forward_contracts.journal_contract_freezes_backend_boundary_and_artifact_scope",
        "docs/reference/journal-contract.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "journal contract headings or bounded backend rules drifted"
                )
            )
            if not _journal_contract_has_required_headings()
            else None
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError(f"journal contract is missing {needle!r}")
            )
            for needle in _REQUIRED_JOURNAL_CONTRACT_NEEDLES
            if needle not in _journal_contract_text()
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError(
                    "journal contract must not restore report.xml as a durable artifact"
                )
            )
            if "report.xml" in _journal_contract_text()
            else None
        ],
    ),
)
