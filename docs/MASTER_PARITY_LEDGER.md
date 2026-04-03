# Master Parity Ledger

This ledger records parity against `master` at the legacy test-family level.
The source of truth is the current typed package under
`src/crypto_reconciliation/`, not the removed flat scripts. Legacy command names
or file locations are not revived to satisfy parity.

## Proof Standard

- A family is only marked closed when the typed repo has direct proof for the
  same behavior or a tighter typed replacement.
- Broad workflow tests are supporting evidence, not the sole proof for narrow
  helper or edge-case rules.
- Relocated fixtures, docs, and workspace paths do not count as regressions if
  the typed workflow still exposes the behavior and tests it directly.

## Current Totals

| Metric | `master` | Current |
| ---- | ----: | ----: |
| Raw test definitions | 243 | 284 |
| Legacy test families | 25 | n/a |
| Status of legacy families | n/a | 25 closed |

## Status Keys

- `ported-direct`: the legacy behavior exists directly in a typed test family.
- `superseded-direct`: the old behavior is covered by tighter typed seams or
  richer workflow proof without restoring legacy wrappers.

## Family Ledger

| Legacy Family | Legacy Tests | Current Typed Proof | Status | Notes |
| ---- | ----: | ---- | ---- | ---- |
| `tests/adapters/test_adapter_protocol.py` | 1 | `tests/contract/test_adapter_registry.py` | `superseded-direct` | Replaced by package-style registry and contract discovery tests |
| `tests/e2e/test_scripts.py` | 13 | `tests/e2e/test_cli.py` | `superseded-direct` | CLI workflows remain active under the typed command surface |
| `tests/pipeline/test_intake_sort.py` | 17 | `tests/unit/application/services/test_intake_service.py`; `tests/unit/test_intake_packages.py`; `tests/unit/test_intake_packages_cycles.py`; `tests/unit/test_intake_packages_scope.py` | `ported-direct` | Legacy sort and grouping rules now live in typed intake planning and package-resolution seams |
| `tests/unit/test_baseline_check.py` | 19 | `tests/unit/application/services/test_baseline_service.py`; `tests/unit/application/services/test_workflow_services.py`; `tests/contract/test_runtime_artifacts.py` | `ported-direct` | Baseline validation, artifact writing, exchange-only assets, and balance-only source handling are directly covered |
| `tests/unit/test_binance_unwrap.py` | 5 | `tests/unit/adapters/test_binance_adapter.py`; `tests/contract/test_source_adapter_packs.py`; `tests/contract/test_source_pack_profiles.py` | `ported-direct` | Includes filename offset parsing, sentinel no-data handling, spot/deposit/withdraw/staking mapping, and pack-level normalization proof |
| `tests/unit/test_coinbase_common.py` | 4 | `tests/unit/adapters/test_coinbase_adapter.py`; `tests/unit/application/services/test_pdf_extract_service.py`; `tests/unit/application/services/test_supporting_services.py` | `ported-direct` | Retail parsing, renamed retail exports, transaction mapping, and statement balance extraction remain covered |
| `tests/unit/test_inspection.py` | 17 | `tests/unit/application/services/test_archive_scan.py`; `tests/unit/application/services/test_intake_file_facts.py`; `tests/unit/application/services/test_profile_inventory_details.py`; `tests/unit/application/services/test_manifest_service.py` | `ported-direct` | Archive inspection, delimiter/date inference, artifact classification, and manifest/profile inventory behavior are direct seams |
| `tests/unit/test_normalization_common.py` | 7 | `tests/unit/test_domain_value_objects.py`; `tests/unit/application/services/test_verification_summary.py`; `tests/unit/application/services/test_workflow_services.py` | `superseded-direct` | Decimal and canonical rendering helpers moved into typed domain and verification seams |
| `tests/unit/test_overlap_check.py` | 9 | `tests/unit/application/services/test_overlap_service.py`; `tests/unit/application/services/test_workflow_services.py` | `ported-direct` | Candidate overlap parsing, summaries, flagged rows, and artifact writing are directly covered |
| `tests/unit/test_package_resolution.py` | 23 | `tests/unit/test_intake_packages.py`; `tests/unit/test_intake_packages_cycles.py`; `tests/unit/test_intake_packages_scope.py`; `tests/unit/application/services/test_intake_service.py` | `ported-direct` | Same-cycle merges, mixed-cycle review, scope conflicts, subset elimination, and overlap decisions are directly covered |
| `tests/unit/test_pdf_balance_extract.py` | 3 | `tests/unit/application/services/test_pdf_extract_service.py`; `tests/unit/application/services/test_supporting_services.py` | `ported-direct` | Statement detection and supported PDF balance extraction remain present |
| `tests/unit/test_pipeline_common.py` | 12 | `tests/unit/application/services/test_export_files.py`; `tests/unit/test_serialization_io.py`; `tests/unit/application/services/test_verification_summary.py`; `tests/unit/application/services/test_rounds_service.py` | `superseded-direct` | CSV/JSON IO, required export lookup, default verification export ordering, and formatting helpers are now split into typed seams |
| `tests/unit/test_reconcile_source.py` | 3 | `tests/unit/application/services/test_supporting_services.py`; `tests/unit/application/services/test_workflow_services.py` | `ported-direct` | Reconciliation diffs and workflow outputs remain covered |
| `tests/unit/test_render_cointracking.py` | 1 | `tests/unit/application/services/test_render_service.py`; `tests/contract/test_cointracking_output.py`; `tests/unit/application/services/test_workflow_services.py` | `ported-direct` | Render behavior is covered both as a service and as an output contract |
| `tests/unit/test_round_scaffold.py` | 11 | `tests/unit/application/services/test_rounds_service.py`; `tests/e2e/test_cli.py` | `ported-direct` | Round-id validation, README generation, phase goals, idempotence, log preservation, and CLI wiring are covered |
| `tests/unit/test_routing.py` | 12 | `tests/unit/application/services/test_intake_routing.py`; `tests/unit/application/services/test_intake_inventory_service.py`; `tests/unit/application/services/test_intake_service.py` | `ported-direct` | Routing now includes capture inference, sidecar handling, supporting artifacts, and inventory-backed wallet routing |
| `tests/unit/test_script_common.py` | 23 | `tests/unit/test_serialization_io.py`; `tests/unit/application/services/test_export_files.py`; `tests/unit/application/services/test_verification_summary.py`; `tests/unit/application/services/test_rounds_service.py`; `tests/unit/test_domain_value_objects.py` | `superseded-direct` | Legacy helper rules were split across typed serialization, export lookup, verification formatting, round defaults, and domain value helpers |
| `tests/unit/test_source_adapters.py` | 17 | `tests/unit/adapters/test_adapter_matching_parity.py`; `tests/unit/adapters/test_coinbase_adapter.py`; `tests/unit/adapters/test_binance_adapter.py`; `tests/unit/adapters/test_near_adapter.py`; `tests/unit/adapters/test_evm_explorer_adapter.py`; `tests/unit/adapters/test_evm_wallet_adapter.py` | `ported-direct` | Direct adapter coverage now exists per adapter instead of through a single flat test module |
| `tests/unit/test_source_adapters_fixtures.py` | 12 | `tests/contract/test_source_adapter_packs.py`; `tests/contract/test_source_pack_profiles.py`; `tests/unit/adapters/test_wallet_inventory_parity.py` | `ported-direct` | Fixture-pack and wallet-evidence expectations remain covered as contracts |
| `tests/unit/test_source_fixture_packs.py` | 5 | `tests/contract/test_source_adapter_packs.py`; `tests/contract/test_source_pack_profiles.py` | `ported-direct` | Pack-driven normalization and profile expectations remain direct contract tests |
| `tests/unit/test_source_manifest.py` | 8 | `tests/unit/application/services/test_archive_scan.py`; `tests/unit/application/services/test_manifest_service.py`; `tests/contract/test_runtime_artifacts.py` | `ported-direct` | Source manifesting is archive-aware and relocation-safe in the typed workflow |
| `tests/unit/test_stage_import_batch.py` | 5 | `tests/unit/application/services/test_normalization_window.py`; `tests/unit/application/services/test_overlap_service.py`; `tests/unit/application/services/test_workflow_services.py` | `ported-direct` | Stage-window filtering, overlap screening, and staged workflow behavior remain covered |
| `tests/unit/test_verification_compare.py` | 7 | `tests/unit/application/services/test_verification_service.py`; `tests/unit/application/services/test_verification_summary.py`; `tests/unit/application/services/test_verification_artifacts.py`; `tests/unit/application/services/test_workflow_services.py` | `ported-direct` | Required exports, summary math, diff artifacts, and verification workflow behavior are directly covered |
| `tests/unit/test_wallet_inventory.py` | 6 | `tests/unit/application/services/test_intake_inventory_service.py`; `tests/unit/application/services/test_wallet_inventory_summary.py`; `tests/unit/adapters/test_wallet_inventory_parity.py`; `tests/unit/adapters/test_evm_wallet_adapter.py`; `tests/unit/adapters/test_near_adapter.py` | `ported-direct` | Wallet extraction, conflict surfacing, summary generation, and inventory routing remain covered |
| `tests/unit/test_wallet_inventory_fixtures.py` | 3 | `tests/unit/adapters/test_wallet_inventory_parity.py`; `tests/contract/test_source_adapter_packs.py`; `tests/contract/test_source_pack_profiles.py` | `ported-direct` | Wallet fixture behavior is covered by direct adapter parity tests and pack contracts |

## Gaps Closed During This Parity Pass

- Restored archive inspection and safety-limit parity through direct service
  tests and typed issue surfacing.
- Restored intake routing and package-resolution parity, including sidecars,
  capture inference, supporting artifacts, mixed-cycle review, and
  inventory-backed wallet routing.
- Restored adapter-local proof for Coinbase, Binance, NEAR, EVM explorer, and
  EVM wallet-state instead of relying only on aggregate golden packs.
- Fixed a real Binance regression where transaction-history sentinel rows
  created false unsupported-group issues.
- Restored parity-friendly JSON artifact writing with parent creation, sorted
  keys, and a trailing newline.
- Updated agent command docs and operations docs so typed workflows remain
  discoverable and usable by Codex/Claude-style agents.

## Deliberate Non-Recoveries

- Removed flat-script entrypoints stay removed.
- Legacy path assumptions stay removed.
- Migration helpers, compatibility wrappers, and one-off repair scripts stay
  out of scope.

Parity is satisfied by typed workflow proof, direct adapter/service tests, and
contract coverage, not by reintroducing the old repo shape.
