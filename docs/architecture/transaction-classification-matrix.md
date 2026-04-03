# Transaction Classification Matrix

Use this document to lock classification behavior before deeper implementation
work lands. The core system must classify facts in layered, platform-agnostic
terms and only project to CoinTracking types at the compatibility edge.

## Classification Layers

- `EconomicKind`: provider-neutral semantic meaning
- `TaxTreatmentCode`: default tax intent used by policy layers
- `JournalIntent`: default accounting intent used by journal renderers
- `CoinTrackingType`: optional compatibility projection only

Core services must not depend on `CoinTrackingType` as the primary driver of
behavior.

## Support Tiers

- `T1`: planned MVP behavior for current filing path
- `T2`: deterministic parse and explicit unsupported or review-required output
- `T3`: compatibility enum only until evidence and policy support are added

## Trade Types

| CoinTrackingType | Default EconomicKind | Default TaxTreatmentCode | Default JournalIntent | Tier | Notes |
| ---- | ---- | ---- | ---- | ---- | ---- |
| `Trade` | `spot_trade` | `taxable_disposition_or_acquisition` | `trade_exchange` | `T1` | Main spot trade path |
| `Margin Trade` | `margin_trade` | `review_required_financing_trade` | `margin_trade` | `T1` | Requires borrow, collateral, and realized PnL semantics |
| `Derivatives / Futures Trade` | `derivative_trade` | `review_required_derivative_trade` | `derivative_trade` | `T1` | Trade lifecycle may remain partially unsupported while realized PnL is supported |

## Incoming Types

| CoinTrackingType | Default EconomicKind | Default TaxTreatmentCode | Default JournalIntent | Tier | Notes |
| ---- | ---- | ---- | ---- | ---- | ---- |
| `Deposit` | `asset_receipt` | `review_required_receipt` | `asset_inflow` | `T1` | Often becomes non-taxable transfer after linking |
| `Income` | `income_receipt` | `income_on_receipt` | `income_receipt` | `T1` | Generic fallback income |
| `Gift / Tip` | `gift_receipt` | `review_required_gift_receipt` | `owner_equity_increase` | `T2` | Treatment depends on facts |
| `Reward / Bonus` | `reward_receipt` | `income_on_receipt` | `income_receipt` | `T1` | Rewards from platforms and promos |
| `Mining` | `mining_receipt` | `income_on_receipt` | `income_receipt` | `T2` | Capital vs business ambiguity may apply |
| `Airdrop` | `airdrop_receipt` | `income_on_receipt` | `income_receipt` | `T2` | Facts may vary by jurisdiction |
| `Staking` | `staking_reward` | `income_on_receipt` | `income_receipt` | `T1` | MVP support required |
| `Masternode` | `masternode_reward` | `income_on_receipt` | `income_receipt` | `T2` | Support later if evidence exists |
| `Minting` | `mint_receipt` | `review_required_minting` | `asset_inflow` | `T2` | NFT or token creation needs explicit policy |
| `Mining (commercial)` | `commercial_mining_receipt` | `review_required_business_income` | `income_receipt` | `T2` | High business-income risk |
| `Dividends Income` | `dividend_receipt` | `income_on_receipt` | `income_receipt` | `T2` | Rare in current dataset |
| `Lending Income` | `lending_income` | `income_on_receipt` | `income_receipt` | `T2` | Requires financing semantics |
| `Interest Income` | `interest_income` | `income_on_receipt` | `income_receipt` | `T1` | Useful for lending and cash products |
| `Derivatives / Futures Profit` | `derivative_realized_pnl` | `realized_pnl_income_or_gain` | `pnl_realization` | `T1` | Supported as realized result |
| `Margin Profit` | `margin_realized_pnl` | `realized_pnl_income_or_gain` | `pnl_realization` | `T1` | Supported as realized result |
| `LP Rewards` | `liquidity_reward` | `income_on_receipt` | `income_receipt` | `T2` | DeFi-specific support later |
| `Airdrop (non taxable)` | `airdrop_receipt` | `non_taxable_receipt` | `asset_inflow` | `T2` | Compatibility-only until policy confirms treatment |
| `Receive Loan` | `loan_proceeds` | `non_taxable_financing_inflow` | `liability_increase` | `T1` | Needed for margin and financing flows |
| `Remove Collateral` | `collateral_release` | `non_taxable_financing_transfer` | `collateral_release` | `T1` | Needed for margin and lending flows |
| `Remove Liquidity` | `liquidity_exit` | `review_required_liquidity_exit` | `liquidity_exit` | `T2` | DeFi lifecycle support later |
| `Receive LP Token` | `lp_token_receipt` | `review_required_lp_receipt` | `liquidity_receipt` | `T2` | Compatibility support only at first |
| `Other Income` | `income_receipt` | `income_on_receipt` | `income_receipt` | `T2` | Generic fallback with review |
| `Income (non taxable)` | `non_taxable_receipt` | `non_taxable_receipt` | `asset_inflow` | `T2` | Requires clear provenance |

## Outgoing Types

| CoinTrackingType | Default EconomicKind | Default TaxTreatmentCode | Default JournalIntent | Tier | Notes |
| ---- | ---- | ---- | ---- | ---- | ---- |
| `Withdrawal` | `asset_send` | `review_required_send` | `asset_outflow` | `T1` | Often becomes non-taxable transfer after linking |
| `Spend` | `spend` | `taxable_disposition` | `expense_disposal` | `T1` | Goods/services spend |
| `Donation` | `donation` | `review_required_donation` | `owner_equity_decrease` | `T2` | Jurisdiction-specific treatment |
| `Gift` | `gift_send` | `review_required_gift_send` | `owner_equity_decrease` | `T2` | Facts matter |
| `Stolen` | `loss_event` | `review_required_loss_event` | `asset_writeoff` | `T2` | Needs explicit policy |
| `Lost` | `loss_event` | `review_required_loss_event` | `asset_writeoff` | `T2` | Needs explicit policy |
| `Borrowing Fee` | `financing_fee` | `deductible_or_capitalizable_fee` | `financing_expense` | `T1` | Margin and loan support |
| `Settlement Fee` | `settlement_fee` | `deductible_or_capitalizable_fee` | `settlement_expense` | `T1` | Applies to derivative settlement or platform closeout |
| `Margin Loss` | `margin_realized_pnl` | `realized_pnl_loss` | `pnl_realization` | `T1` | Supported as realized result |
| `Margin Fee` | `margin_fee` | `deductible_or_capitalizable_fee` | `financing_expense` | `T1` | Needed for margin accounting |
| `Derivatives / Futures Loss` | `derivative_realized_pnl` | `realized_pnl_loss` | `pnl_realization` | `T1` | Supported as realized result |
| `Provide Liquidity` | `liquidity_entry` | `review_required_liquidity_entry` | `liquidity_entry` | `T2` | DeFi lifecycle support later |
| `Return LP Token` | `lp_token_return` | `review_required_lp_return` | `liquidity_return` | `T2` | DeFi lifecycle support later |
| `Other Fee` | `other_fee` | `deductible_or_capitalizable_fee` | `expense` | `T1` | Generic fallback fee |
| `Other Expense` | `other_expense` | `review_required_expense` | `expense` | `T2` | Generic fallback expense |
| `Expense (non taxable)` | `non_taxable_expense` | `non_taxable_outflow` | `expense` | `T2` | Requires explicit facts |
| `Add Collateral` | `collateral_post` | `non_taxable_financing_transfer` | `collateral_post` | `T1` | Needed for margin and lending flows |
| `Repay Loan` | `loan_repayment` | `non_taxable_financing_outflow` | `liability_decrease` | `T1` | Needed for financing flows |
| `Liquidation` | `forced_liquidation` | `review_required_liquidation` | `forced_closeout` | `T2` | Requires explicit closeout handling |

## Runtime Rules

- Adapters should populate `EconomicKind` first.
- `CoinTrackingType` is optional metadata or derived projection.
- Tax policy operates on facts plus `TaxTreatmentCode`, never directly on
  CoinTracking labels.
- Journal rendering operates on facts plus `JournalIntent`, never directly on
  CoinTracking labels.
- If an adapter cannot determine a safe default, it must emit an explicit issue
  instead of guessing.

## Review Triggers

Require explicit review when:

- the fact could be either a transfer or a taxable disposition
- the fact changes beneficial ownership but not obvious tax treatment
- a platform-specific row collapses financing, trading, and fee semantics into
  one record
- an adapter has only CoinTracking labels but not enough raw evidence to assign
  a safe provider-neutral meaning
