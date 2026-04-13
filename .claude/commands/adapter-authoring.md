# Adapter Authoring

Read `docs/status/adapter-delivery-plan.md` first for the filing-window
decision rules, then read `docs/concepts/unified-adapter-architecture.md` for
the forward design target, and use `docs/guides/write-an-adapter.md` as the
current contract.

When repairing or extending an adapter:

1. keep metadata, code, and tests aligned
2. keep the adapter work aligned with the core pipeline in
   `docs/concepts/reconciliation-tax-architecture.md` without turning adapter
   work into a second architecture center
3. prefer current-contract hardening for filing-critical adapters over
   speculative future-contract scaffolding
4. keep ambiguous data explicit as issues or review records
5. keep output rendering and source normalization concerns separated
6. rerun the full quality gate before considering the adapter ready
