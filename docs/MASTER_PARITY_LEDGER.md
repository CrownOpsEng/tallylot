# Master Parity Ledger

This ledger tracks the typed replacement status for workflows that existed on
`master`. Every capability should end in one of three states only:
`present`, `restored`, or `superseded`.

## Present

| Capability | Status | Notes |
| ---- | ---- | ---- |
| `workspace init` | `present` | Seeds the external workspace layout and repo-owned docs/templates |
| `baseline validate` | `present` | Typed baseline validation artifact package |
| `source manifest` | `superseded` | Now archive-aware by default and emits `manifest_issues.csv` |
| `source profile` | `superseded` | Now archive-aware by default and emits `profile_issues.csv` plus archive member provenance |
| `source normalize` | `superseded` | Preserves typed canonical outputs and now scans ZIP evidence by default |
| `source reconcile` | `present` | Typed reconciliation service remains active |
| `wallet inventory rebuild` | `present` | Typed aggregate inventory workflow remains active |
| `output render cointracking` | `present` | CoinTracking CSV renderer remains active |
| `verification compare` | `present` | Typed verification comparison remains active |
| `batch screen` | `restored` | Overlap summary and flagged-row artifacts are back |
| `batch stage` | `restored` | Normalization window enforcement and optional import-ready copy are back |
| `round scaffold` | `present` | Typed round scaffolding remains active |
| PDF balance extraction | `present` | Supported typed extraction workflow remains active |

## Restored

| Capability | Status | Notes |
| ---- | ---- | ---- |
| Universal ZIP inspection | `restored` | Shared scan layer now powers manifest, profile, normalize, and intake |
| Archive safety limits | `restored` | Enforces max archive size, expanded size, member size/count, and nesting depth |
| Archive issue surfacing | `restored` | Unsafe paths, encrypted members, unsupported compression, symlinks, and unsupported archive types emit explicit issues |
| `source intake plan` | `restored` | Typed intake planning with archive-aware inventory and reports |
| `source intake apply` | `restored` | Typed intake apply path for loose-file copies plus archive inspection-only reporting |
| Adapter-pack golden refresh tooling | `restored` | `tools.refresh_adapter_goldens` runs the typed services and refreshes JSON goldens |
| Adapter scaffold tooling | `restored` | `tools.scaffold_adapter` seeds package-style adapter modules with colocated tests and fixtures |

## Still Narrower Than Master

| Capability | Current State | Required Follow-up |
| ---- | ---- | ---- |
| Real source adapter breadth | Only `structured_csv` is fully implemented | Recover typed adapters for Coinbase, Wealthsimple, Binance, Crypto.com, Shakepay, Ledger Live, Near, GTrade, EVM explorer, and MetaMask/state logs |
| Intake/package resolution intelligence | Generic typed routing exists | Port source-aware duplicate resolution, same-cycle merges, mixed-cycle review, and supporting-artifact classification into typed intake services |
| Adapter-pack coverage breadth | Golden-pack workflow exists for `structured_csv` | Add pack fixtures and contract coverage for every restored real source adapter |

## Rules

- Do not close parity gaps by reviving the removed flat-script entrypoints,
  wrappers, or migration helpers.
- Recover behavior inside the typed package and keep layer boundaries intact.
- Keep archive inspection opt-out at the command boundary only.
