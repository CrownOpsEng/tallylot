---
title: "Canadian Crypto Tax Guide"
summary: "Working CRA-aligned tax reference for the repo's Canadian crypto workflow."
doc_type: reference
audience: human
owner: repo
status: active
---

This document replaces the imported 2022 article as the repo's working tax reference.

Purpose:

- keep the reconciliation workflow aligned with current CRA guidance
- identify where the law or CRA guidance is clear
- identify where treatment is fact-specific or still ambiguous enough that the repo must not guess

Scope:

- Canadian federal income tax alignment for crypto-asset users
- recordkeeping and classification rules relevant to this reconciliation project
- emphasis on the 2023 to 2025 period covered by this repo

This is not legal advice. When this guide conflicts with primary CRA guidance, follow the CRA source.

This guide is intentionally not exhaustive. Use it for the default working position, then escalate to `docs/reference/tax-source-map.md` when a fact pattern falls outside the ordinary path.

## Current status

Verified against CRA primary sources on `2026-03-22`.

Key update:

- for individuals, the CRA is currently administering the enacted capital gains inclusion rate of **one-half** for dispositions before `2026-01-01`
- the proposed increase to two-thirds was deferred to `2026-01-01`

For this repo's historical closeout through `2025-12-31`, that means:

- capital gains treatment still uses the one-half inclusion rate
- business income treatment remains fully taxable
- the real compliance risk is usually not the inclusion rate itself, but bad classification, missing records, broken transfer history, and unsupported CAD values

## Foundational CRA rules

### 1. Crypto-assets are not legal tender

CRA treats crypto-assets as property, not government-issued currency.

Practical effect:

- selling crypto for CAD is a disposition
- swapping one crypto-asset for another is a disposition
- using crypto to buy goods or services is generally a barter transaction and a disposition
- transfers between wallets you own are generally not dispositions

### 2. You must determine values in Canadian dollars

CRA expects transaction values to be determined in Canadian dollars at the time of each transaction.

Practical effect:

- each acquisition, disposition, reward, and fee needs a supportable CAD value
- valuation method must be reasonable and used consistently
- if direct CAD pricing is unavailable, use a documented, repeatable method

### 3. Records must be reliable, complete, and supported

CRA requires adequate books and records for each transaction.

For crypto-asset users, that includes:

- units and type of asset
- date and time
- CAD value at the time of the transaction
- nature of the transaction and counterparty
- wallet addresses
- beginning and ending balances
- trade ledgers
- transfer ledgers for both crypto-assets and traditional currency

Repo implication:

- unexplained negative fiat balances are not acceptable just because they are analytically convenient
- if the fiat leg exists outside the portfolio-tracker export, it still must be documented well enough to support the tax record

## Capital vs. business treatment

The most important tax classification question is whether activity is on capital account or on income account.

### Capital treatment

If a disposition is capital in nature:

- only half of the capital gain is included in income for the years covered by this repo
- only half of a capital loss is allowable
- allowable capital losses can generally only offset taxable capital gains

Adjusted cost base must be tracked by identical property.

For crypto-assets, practical working assumption:

- each asset ticker or economically identical property pool must be tracked separately
- pooled ACB / weighted-average costing applies within each identical-property group

### Business treatment

If activity is business income:

- profits are fully taxable
- losses may be business losses
- inventory valuation and business-income rules may apply instead of capital-gain mechanics

CRA looks at facts, not labels. Relevant indicators include:

- frequency and turnover
- commercial manner of operation
- time spent
- financing
- level of market knowledge
- whether the activity resembles a trader or dealer

Repo implication:

- this workspace must not invent a capital-treatment assumption for ambiguous activity
- if classification is genuinely uncertain, log it and get facts or professional advice

## Common transaction treatments

### Dispositions that usually trigger tax consequences

These generally require gain, loss, or income analysis:

- sale for CAD or other fiat
- crypto-to-crypto swap
- spending crypto on goods or services
- gift or donation that transfers ownership
- some DeFi events where beneficial ownership changes

### Movements that generally should not be taxable by themselves

These are usually non-taxable if beneficial ownership does not change:

- transfer between wallets you own
- transfer between exchanges you own
- internal movement between your own sub-accounts

Important:

- fees paid during a transfer can still matter
- broken transfer pairing is a recordkeeping problem even if the underlying move is non-taxable

## Mining and staking

This area is more developed than the imported 2022 guide suggests.

### Mining

CRA now states that in most cases mining activities will be considered carrying on a business because of the scale and resources involved.

Working implication:

- do not default mining to a casual hobby treatment
- assume mining requires explicit classification review
- if it is business income, the value of crypto-assets received is included in business income when earned

### Staking

CRA now has direct guidance for staking.

Important CRA position:

- rewards received from staking on a centralized platform will generally be income when credited to the taxpayer's wallet on the platform

Repo implication:

- staking receipts should not be treated as automatically non-taxable until disposition
- platform staking rewards need explicit treatment review and consistent records

## Airdrops, hard forks, DeFi, NFTs, bankruptcies, scams

This is where the imported guide was too confident.

Current repo rule:

- do not use broad categorical rules unless CRA has clearly said so
- do not state that all airdrops or hard forks are automatically zero-cost and non-taxable on receipt as a universal rule
- do not state that all DeFi events are automatically taxable dispositions
- do not state that all bankrupt exchange losses follow one standard election path

Instead:

- classify the legal and economic substance of the event
- collect source records
- determine whether there was income, a disposition, a debt loss, an abandonment, or some other event
- if CRA guidance is not direct, document the treatment rationale and escalate when material

Repo implication:

- ambiguous DeFi, airdrop, hard fork, NFT, insolvency, and scam events should be logged as issues, not guessed

## Superficial loss rule

If activity is on capital account, superficial loss rules can apply to crypto-assets that are identical property.

Practical implication:

- selling at a loss and reacquiring the same or identical property within the 30-day window can deny the immediate loss
- the denied loss is generally added to the adjusted cost base of the substituted property when the rule applies

Repo implication:

- if there are tax-loss-harvesting style patterns, they need to be reviewed explicitly
- this repo should not assume every capital loss is immediately usable

## T1135 foreign reporting

The imported guide was too definitive here.

Current safe rule:

- Form T1135 may be required if the taxpayer owned specified foreign property costing more than `CAD 100,000` at any time during the year
- whether a particular crypto holding is reportable depends on the facts and how the property is situated, deposited, or held
- do not decide T1135 solely from a simple hot-wallet versus cold-wallet slogan

Repo implication:

- if foreign reporting may be in play, document the custody pattern and platform locations
- do not mark T1135 as required or not required without a fact-based review

## When this guide is not enough

Do not treat this guide as final authority for these situations:

- activity may be business income rather than capital
- staking is not simple centralized-platform reward crediting
- DeFi changes beneficial ownership or legal rights in a non-obvious way
- bridge, wrap, unwrap, token migration, or re-denomination events
- airdrops, hard forks, scams, bankruptcies, thefts, abandoned assets, or bad-debt style losses
- foreign custody raises possible T1135 reporting
- GST/HST may matter because the activity is commercial rather than personal investment

When one of those appears:

1. log the issue in `analysis/issues/issue_log.csv`
2. collect the raw records first
3. use `docs/reference/tax-source-map.md` to jump to the relevant CRA source
4. keep the issue open until the treatment is supportable

## Repo execution rules derived from tax compliance

These are the operational tax rules this repo should follow:

1. CRA primary sources outrank exchange guidance, vendor blogs, and AI heuristics.
2. Every material transaction needs supportable CAD valuation.
3. Transfer ledgers for fiat are part of the required books and records, not optional nice-to-haves.
4. Negative fiat balances must be reconciled or explicitly documented with supporting records.
5. If capital versus business treatment is unclear, keep the issue open rather than forcing a classification.
6. If an event is economically unusual, classify the facts first and tax-label it second.
7. Preserve raw exports and evidence because CRA recordkeeping obligations outlive any one platform.

## Official CRA sources used

- Information for crypto-asset users and tax professionals  
  <https://www.canada.ca/cra-crypto-assets>
- Keeping books and records of crypto-assets for tax filing  
  <https://www.canada.ca/en/revenue-agency/programs/about-canada-revenue-agency-cra/compliance/cryptocurrency-guide/books-records-crypto.html>
- Determining the value of crypto-assets for tax filing  
  <https://www.canada.ca/en/revenue-agency/programs/about-canada-revenue-agency-cra/compliance/cryptocurrency-guide/value-crypto.html>
- Reporting income from crypto-asset transactions  
  <https://www.canada.ca/en/revenue-agency/programs/about-canada-revenue-agency-cra/compliance/cryptocurrency-guide/income-crypto-transactions.html>
- Reporting income from crypto-asset mining and staking activities  
  <https://www.canada.ca/en/revenue-agency/programs/about-canada-revenue-agency-cra/compliance/cryptocurrency-guide/income-crypto-mining-staking-activities.html>
- Reporting your capital gains as a crypto-asset user  
  <https://www.canada.ca/en/revenue-agency/news/newsroom/tax-tips/tax-tips-2024/reporting-your-capital-gains-as-crypto-asset-user.html>
- Foreign Income Verification Statement  
  <https://www.canada.ca/en/revenue-agency/services/tax/international-non-residents/information-been-moved/foreign-reporting/foreign-income-verification-statement.html>
- Questions and answers about Form T1135  
  <https://www.canada.ca/en/revenue-agency/services/tax/international-non-residents/information-been-moved/foreign-reporting/questions-answers-about-form-t1135.html>
- Superficial loss  
  <https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/personal-income/line-12700-capital-gains/capital-losses-deductions/what-a-superficial-loss.html>
- Identical properties  
  <https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/personal-income/line-12700-capital-gains/shares-funds-other-units/identical-properties.html>
- Update on the CRA's administration of the proposed capital gains taxation changes  
  <https://www.canada.ca/en/revenue-agency/news/newsroom/tax-tips/tax-tips-2025/update-cra-administration-proposed-capital-gains-taxation-changes.html>
