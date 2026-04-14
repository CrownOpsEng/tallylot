---
title: "Architecture Overview"
summary: "High-level map of the current bridge, final pipeline, and the documents that own each boundary."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 10
---

TallyLot ships a typed Python package and CLI for source-backed intake,
reconciliation, checkpointing, accounting validation, output rendering, and
tax-oriented work.

## Core Shape

- `domain/` owns business models, enums, and value objects
- `application/` owns use-case orchestration over domain models and ports
- `ports/` defines narrow typed boundaries
- `infrastructure/` implements filesystem and other operational details
- `adapters/` translate source and output formats
- `interfaces/` exposes CLI entry points over application capabilities

## Operating Model

- Raw evidence and live operator artifacts live in an external workspace, not
  in the repo.
- The repo owns code, tests, docs, templates, automation, and workspace
  guidance.
- Financial values stay in `Decimal`.
- Unsupported or ambiguous facts stay explicit as issues or review artifacts.

## Current Direction

- `EconomicActivityDraft`, `TransactionFact`, `balance_snapshots.csv`, and
  `balance_references.csv` are the current runtime bridge.
- CoinTracking remains an edge output adapter and an oracle family for
  comparison tooling, not the core ledger model.
- Reconciliation and checkpoint trust gates come before tax policy.
- The target pipeline now converges on
  `EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`.
- Forward-looking docs use those final product names, while current-state docs
  keep current implementation terms where accuracy requires them.

## Read Next

- `docs/concepts/reconciliation-tax-architecture.md`
- `docs/concepts/oracle-boundaries.md`
- `docs/concepts/transaction-classification.md`
- `docs/concepts/workspace-model.md`
- `docs/standards/engineering.md`
