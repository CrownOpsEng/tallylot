# Test Suite Follow-Ups

Track only the remaining work that was intentionally left out of the current adapter-pack consolidation.

## Pack Tooling

- Add a small scaffold helper that creates `tests/fixtures/adapter_packs/<adapter>/<scenario>/` with the right metadata and expected-file layout.
- Add an explicit golden-refresh command so fixture authors do not need ad-hoc local scripts to regenerate expected JSON after adapter changes.

## Refactor Alignment

- When the repo refactor begins, colocate adapter packs with the adapter modules or a first-class plugin package instead of keeping them under the current monorepo test tree.
- Split adapter-pure tests from pipeline-orchestration tests so future plugin extraction can happen without reworking the golden fixtures again.

## CI Profiles

- Add a CI matrix that runs adapter-pack unit coverage separately from broader CLI/e2e coverage so failures localize faster.
