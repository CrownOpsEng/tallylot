---
title: "CoinTracking Oracle Artifacts"
summary: "Repo-safe reference for CoinTracking artifact families used only for development and validation."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: oracle_local
nav_order: 70
---

Use this document as the repo-safe reference for CoinTracking oracle support.

The actual captured CoinTracking exports, report bundles, tax reports, and
manifests belong in the external workspace, not in the repo.

## Purpose

These artifacts are useful for development and validation only:

- black-box comparison against internal reconciliation and tax outputs
- regression checks against the historical portfolio-tracker baseline
- investigating mismatches that simple primary evidence cannot explain

They are not production/runtime inputs for reconstruction, checkpoint
assembly, journal work, or tax computation.

## Common Artifact Families

Current and historical workflows may use these CoinTracking export families as
comparison oracles:

- `Trade Table`
- `Trade List`
- `Current Balance`
- `Balance by Exchange`
- `Validate Transactions`
- `Missing Transactions`
- `Duplicate Transactions`
- `Average Purchase Price`
- `Roll Forward in CAD`
- `Realized Gain or Loss in CAD`
- `Double-entry`

## Storage Rule

Keep private oracle captures in the external workspace under the portfolio
evidence tree. Do not check personal oracle bundles, manifests, hashes, or
captured report filenames into the repo.

## Review Rule

If an oracle artifact is needed for tests or docs, prefer one of these:

- a generic documented artifact family list
- a sanitized schema example
- a synthetic fixture generated specifically for public testing

Do not use private export inventories as repo fixtures.
