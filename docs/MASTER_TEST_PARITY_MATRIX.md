# Master Test Parity Matrix

This matrix tracks the behavioral parity status of the `master` test suite
against the typed architecture on this branch. It records behavior, not old
file paths or legacy script names.

Statuses:

- `covered`: current tests already prove the behavior
- `ported`: old test intent was rewritten into typed-service or typed-CLI tests
- `superseded-with-proof`: legacy script coupling or old layout was removed, but
  the underlying capability is still proven in the new architecture

| Master Test File | Status | Current Proof |
| ---- | ---- | ---- |
| `tests/adapters/test_adapter_protocol.py` | `covered` | `tests/contract/test_adapter_registry.py` |
| `tests/e2e/test_scripts.py` | `ported` | `tests/e2e/test_cli.py`, `tests/unit/adapters/test_adapter_tooling.py`, `tests/unit/application/services/test_workflow_services.py` |
| `tests/pipeline/test_intake_sort.py` | `ported` | `tests/unit/application/services/test_intake_service.py`, `tests/unit/test_intake_packages.py`, `tests/unit/application/services/test_intake_routing.py`, `tests/unit/application/services/test_intake_file_facts.py` |
| `tests/unit/test_baseline_check.py` | `ported` | `tests/unit/application/services/test_baseline_service.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_binance_unwrap.py` | `superseded-with-proof` | `tests/unit/application/services/test_archive_scan.py`, `tests/unit/application/services/test_intake_service.py`, `tests/unit/adapters/test_binance_adapter.py` |
| `tests/unit/test_coinbase_common.py` | `ported` | `tests/unit/adapters/test_coinbase_adapter.py`, `tests/unit/application/services/test_supporting_services.py` |
| `tests/unit/test_inspection.py` | `ported` | `tests/unit/application/services/test_archive_scan.py`, `tests/unit/application/services/test_intake_file_facts.py`, `tests/unit/application/services/test_intake_routing.py` |
| `tests/unit/test_normalization_common.py` | `superseded-with-proof` | `tests/unit/adapters/test_shared_support.py`, `tests/unit/test_hardening.py` |
| `tests/unit/test_overlap_check.py` | `ported` | `tests/unit/application/services/test_workflow_services.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_package_resolution.py` | `covered` | `tests/unit/test_intake_packages.py` |
| `tests/unit/test_pdf_balance_extract.py` | `ported` | `tests/unit/application/services/test_supporting_services.py` |
| `tests/unit/test_pipeline_common.py` | `ported` | `tests/unit/application/services/test_archive_scan.py`, `tests/unit/application/services/test_intake_file_facts.py`, `tests/unit/application/services/test_intake_routing.py` |
| `tests/unit/test_reconcile_source.py` | `ported` | `tests/unit/application/services/test_supporting_services.py` |
| `tests/unit/test_render_cointracking.py` | `ported` | `tests/contract/test_cointracking_output.py`, `tests/unit/application/services/test_render_service.py` |
| `tests/unit/test_round_scaffold.py` | `ported` | `tests/unit/application/services/test_supporting_services.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_routing.py` | `ported` | `tests/unit/application/services/test_intake_routing.py`, `tests/unit/application/services/test_intake_service.py` |
| `tests/unit/test_script_common.py` | `superseded-with-proof` | `tests/unit/test_domain_value_objects.py`, `tests/unit/application/services/test_baseline_service.py`, `tests/unit/application/services/test_verification_service.py`, `tests/unit/test_config_loader.py` |
| `tests/unit/test_source_adapters.py` | `ported` | `tests/contract/test_source_adapter_packs.py`, `tests/unit/adapters/test_coinbase_adapter.py`, `tests/unit/adapters/test_binance_adapter.py`, `tests/unit/adapters/test_near_adapter.py` |
| `tests/unit/test_source_adapters_fixtures.py` | `ported` | `tests/contract/test_source_adapter_packs.py`, `tests/unit/adapters/test_coinbase_adapter.py`, `tests/unit/adapters/test_evm_wallet_adapter.py` |
| `tests/unit/test_source_fixture_packs.py` | `superseded-with-proof` | `tests/contract/test_source_adapter_packs.py` |
| `tests/unit/test_source_manifest.py` | `ported` | `tests/unit/application/services/test_workflow_services.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_stage_import_batch.py` | `covered` | `tests/unit/application/services/test_workflow_services.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_verification_compare.py` | `ported` | `tests/unit/application/services/test_workflow_services.py`, `tests/unit/application/services/test_verification_service.py`, `tests/e2e/test_cli.py` |
| `tests/unit/test_wallet_inventory.py` | `ported` | `tests/unit/application/services/test_workflow_services.py`, `tests/unit/adapters/test_evm_wallet_adapter.py`, `tests/unit/adapters/test_near_adapter.py` |
| `tests/unit/test_wallet_inventory_fixtures.py` | `ported` | `tests/contract/test_source_adapter_packs.py`, `tests/unit/adapters/test_evm_wallet_adapter.py`, `tests/unit/adapters/test_near_adapter.py` |

## Relocation Drift Notes

- `master` failures caused only by moved docs, fixtures, or external-workspace
  paths are treated as layout drift, not capability loss.
- The old flat script entrypoints remain intentionally removed. Their
  capabilities must stay proven through `src/crypto_reconciliation/` services
  and the current CLI only.
