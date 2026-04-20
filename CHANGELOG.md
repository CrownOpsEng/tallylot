# Changelog

This project uses a lightweight mainline changelog.

Until tagged releases exist, completed work is recorded here as dated
milestones on `main`.

## [Unreleased]

### Docs And Control Plane

- Reset durable contract and sequencing authority onto the owned docs and
  removed planning-coupled semantic docs-audit proof from durable control-plane
  checks.
- Moved completed `EvidenceSet` delivery truth out of future-tense planning
  language and tightened durable doc checks against ephemeral delivery labels.
- Added planner-enabled Coinbase `ClaimSet` authority, deterministic
  claim-stage gap and review sidecars, and `draft_projection_fields.json`
  compatibility output under `working/products/claim_sets/`.
- Added derived `EconomicActivityDraft` and `SourceTranslationBatch`
  compatibility rebuilding from authoritative `ClaimSet` plus the declared
  bridge-only claim sidecar fields.
- Added authoritative `EconomicFacts`, `ReconciliationState`, and `Checkpoint`
  kernels for the bounded planner-enabled Coinbase slice, with normalization
  persisting those product roots and mirroring target-derived
  compatibility `facts.csv`, `balance_snapshots.csv`, and
  `balance_references.csv` back into the existing capture output tree.
- Split live repo docs enforcement between `docs-maintenance`,
  `target-naming`, and `docs-audit` as script-owned checks instead of pytest.
- Hardened repo-native PR review routing, quality-gate selection, and current
  runtime delivery guardrails around the rebuilt typed architecture.

## 2026-04-01

### Rebuild Milestones

- Restored the deterministic workflow baseline and typed intake routing.
- Packaged intake and output workflow seams and grouped source adapters by kind.
- Reset the typed architecture around neutral core boundaries and tightened the
  fact model.
- Hardened external `uv` bootstrap, source verification and routing, and merge
  verification policy.

### Docs

- Hardened public docs and sanitized fixtures.

## 2026-03-26

### Workspace And Docs

- Externalized live workspace artifacts and restored repo-owned docs.
