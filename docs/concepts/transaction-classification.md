---
title: "Transaction Classification"
summary: "Bridge-only classification vocabulary for the current fact-path bridge."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 40
---

Use this document to lock the current layered classification vocabulary on the
fact-path bridge before deeper claim, checkpoint, accounting, and tax work
lands.

This page owns the current bridge classification vocabulary only.

Current runtime note:

- the current runtime writes `TransactionFact` artifacts
- the layered bridge terms live in `domain/transactions/classification.py`
- adapters should populate bridge classifications only when those
  classifications are safe and deterministic
- output adapters own the mapping from bridge metadata into external row types
  such as the CoinTracking `Type` column

Target-direction note:

- bridge classifications remain important now, but they are not the full
  long-term ontology
- future target-layer naming and ontology rules belong in
  [Domain Ontology](domain-ontology.md), not here
- this docs-only slice does not rename the live bridge symbols

Naming convention:

- enum members such as `ProjectionHint.TRADE` stay Python-style uppercase names
- stored/runtime values such as `trade` stay lowercase snake_case machine
  identifiers
- renderer labels such as `Trade` stay adapter-local presentation strings

## Classification Layers

- `EconomicKind`: provider-neutral bridge semantic meaning
- `TaxTreatmentHint`: bridge tax intent used only when it is already safe to
  say on the current fact path
- `AccountingIntentHint`: bridge accounting intent used only when it is already
  safe to say on the current fact path
- `ProjectionHint`: output projection metadata for concrete renderers

Bridge behavior should not key primarily on the legacy normalized `category`
string.

## Support Tiers

- `T1`: implemented and supported in the current runtime
- `T2`: explicitly planned, but not yet part of the current runtime enum set
- `T3`: output-specific or future-policy work

## Current Runtime Mapping

These are the currently implemented bridge mappings. Code and docs must stay
aligned on these values exactly.

| Normalized Category | ProjectionHint | EconomicKind | TaxTreatmentHint | AccountingIntentHint | Tier | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `trade` | `trade` | `spot_trade` | `capital_exchange` | `asset_exchange` | `T1` | Main spot trade path |
| `deposit` | `deposit` | `asset_deposit` | `non_taxable_transfer_in` | `funding_inflow` | `T1` | Compatibility deposit before later transfer-linking |
| `withdrawal` | `withdrawal` | `asset_withdrawal` | `non_taxable_transfer_out` | `funding_outflow` | `T1` | Compatibility withdrawal before later transfer-linking |
| `interest_income` | `interest_income` | `interest_income` | `ordinary_income` | `income_recognition` | `T1` | Generic interest or similar income receipt |
| `reward` | `reward_bonus` | `platform_reward` | `ordinary_income` | `income_recognition` | `T1` | Platform and promotional rewards |
| `expense` | `expense_non_taxable` | `cash_expense` | `non_taxable_expense` | `expense_recognition` | `T1` | Current non-taxable expense bridge path |
| `swap` | `swap_non_taxable` | `asset_swap` | `non_taxable_asset_migration` | `asset_exchange` | `T1` | Current non-taxable asset migration bridge path |
| `staking_reward` | `staking` | `staking_reward` | `staking_income` | `income_recognition` | `T1` | MVP staking-reward support |
| `derivatives_profit` | `derivatives_futures_profit` | `derivative_realized_profit` | `derivative_realized_gain` | `income_recognition` | `T1` | Current realized profit bridge path |
| `derivatives_loss` | `derivatives_futures_loss` | `derivative_realized_loss` | `derivative_realized_loss` | `expense_recognition` | `T1` | Current realized loss bridge path |

## Runtime Rules

- adapters populate layered classifications on the current bridge path only
  when the classification is safe and deterministic
- if an adapter cannot determine a safe bridge classification, it must emit an
  explicit blocking issue or review instead of guessing
- missing tax or accounting intent must not force lower layers to guess
- runtime consumers operate on bridge `legs` only; there is no split
  `fee_legs` lane and no first-leg compatibility view on `TransactionFact`
- leg-level semantics live on the leg through `LegKind`; fact classification
  remains a separate fact-level layer
- `ProjectionHint` is output metadata, not the long-term driver of
  business behavior
- output adapters map bridge classifications into concrete external row
  families when they need them

## Review Triggers

Require explicit review when:

- the fact could be either a transfer or a taxable disposition
- the fact changes beneficial ownership but not obvious tax treatment
- the economic meaning is safe enough for reconciliation, but tax treatment
  still depends on later policy-owned determinants
- a provider row collapses financing, trading, and fee semantics into one
  record
- a future activity type would require a new bridge classification value
  instead of a safe mapping into the current bridge set

## Future Expansion Rules

- do not add near-duplicate names for the same concept
- add new bridge enum values only when the behavior, tests, and adapter
  mappings land together
- keep future unsupported or planned semantics explicit in docs or roadmap
  notes rather than preloading duplicate bridge enum names into the runtime
- when later bridge work needs a richer bridge classification set, update this
  document and `domain/transactions/classification.py` in the same checkpoint
