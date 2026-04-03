# Transaction Classification Matrix

Use this document to lock the current canonical classification vocabulary
before deeper fact, checkpoint, accounting, and tax work lands.

The current runtime now writes `TransactionFact` artifacts, and the canonical
layered terms live in `domain/transactions/classification.py`. Adapters should
populate layered classifications first. Output adapters own any mapping from
fact metadata into external row types such as the CoinTracking `Type` column.

Naming convention:

- enum members such as `ProjectionType.TRADE` stay Python-style uppercase names
- stored/runtime values such as `trade` stay lowercase snake_case machine identifiers
- renderer labels such as `Trade` stay adapter-local presentation strings

## Classification Layers

- `EconomicKind`: provider-neutral semantic meaning
- `TaxTreatmentCode`: default tax intent used by later policy layers
- `JournalIntent`: default accounting intent used by later journal renderers
- `ProjectionType`: output projection metadata for concrete renderers

Core behavior should not key primarily on the legacy normalized `category`
string.

## Support Tiers

- `T1`: implemented and supported in the current runtime
- `T2`: explicitly planned, but not yet part of the canonical runtime enum set
- `T3`: output-specific or future-policy work

## Current Canonical Mapping

These are the currently implemented canonical mappings. Code and docs must stay
aligned on these values exactly.

| Normalized Category | ProjectionType | EconomicKind | TaxTreatmentCode | JournalIntent | Tier | Notes |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
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

## Future Expansion Rules

- Do not add near-duplicate names for the same concept.
- Add new enum values only when the behavior, tests, and adapter mappings land
  together.
- Keep future unsupported or planned semantics explicit in docs or roadmap
  notes rather than preloading duplicate enum names into the runtime.
- When later fact, accounting, or tax work needs a richer classification set,
  update this document and `domain/transactions/classification.py` in the same
  checkpoint.

## Runtime Rules

- Adapters populate layered classifications first.
- Output adapters map layered classifications into concrete external row
  families when they need them.
- `ProjectionType` is output metadata, not the long-term core driver of
  business behavior.
- Machine-oriented runtime values should stay lowercase snake_case even when an
  output adapter renders them as title-style labels.
- If an adapter cannot determine a safe layered classification, it must emit an
  explicit issue instead of guessing.

## Review Triggers

Require explicit review when:

- the fact could be either a transfer or a taxable disposition
- the fact changes beneficial ownership but not obvious tax treatment
- a provider row collapses financing, trading, and fee semantics into one record
- a future activity type would require a new classification value rather than a
  safe mapping into the current canonical set
