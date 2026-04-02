# Wallet Inventory

This repo now maintains a canonical wallet inventory under:

`analysis/inventory/`

Use it as the compact machine-readable answer to "what wallet identifiers do we know about, where did they come from, and do any need review?"

## Files

| File | Purpose |
| ---- | ------- |
| `analysis/inventory/wallet_inventory.csv` | One row per known wallet identifier or public account key |
| `analysis/inventory/wallet_inventory_evidence.csv` | Source-level evidence rows showing exactly where each identifier came from |
| `analysis/inventory/wallet_inventory_issues.csv` | Deterministic review items such as partial aliases or missing identifiers |
| `analysis/inventory/wallet_inventory_summary.json` | Small summary for scripts and AI agents |

## Current scope

The inventory currently extracts and normalizes identifiers from:

- chain-scoped EVM explorer exports
- Ledger Live operations exports
- NEAR raw export filenames
- Ronin raw export filenames
- MetaMask app state logs
- GTrade report aliases

Supported identifier families include:

- EVM addresses
- Bitcoin xpubs and addresses
- Cardano account keys from Ledger Live
- NEAR account identifiers
- Tron addresses
- Solana addresses
- truncated aliases when a source does not expose the full address

## Generation

Refresh the repo inventory with:

```bash
python3 06_scripts/wallet_inventory.py --repo-root .
```

`profile_source.py` also writes per-source wallet artifacts into `working/normalized/<source>/` and automatically refreshes the repo-wide inventory when the profile output lives inside this repo.

## Review rules

- Treat `wallet_inventory.csv` as the compact lookup table.
- Use `wallet_inventory_evidence.csv` when you need the exact raw file that supports an identifier.
- Do not promote a truncated alias to a full wallet address without companion evidence.
- Keep app-wide wallet evidence such as MetaMask state logs separate from chain-scoped explorer evidence.
- If a chain-scoped explorer capture yields multiple owned addresses, treat that as a capture integrity issue and resolve it before import prep.

## AI usage

For AI work, prefer the summary or inventory CSV before opening raw exports. That keeps context small while preserving the audit trail back to the exact capture file when needed.
