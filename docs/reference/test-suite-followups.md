# Test Suite Follow-Ups

Track only the remaining work that was intentionally left out of the current adapter-pack consolidation.

## Pack Tooling

- Keep the scaffold and golden-refresh commands aligned with any future pack-layout move so fixture authors still have one stable toolchain.

## Refactor Alignment

- Continue moving adapter packs toward adapter-owned layout so plugin extraction can happen without another test-tree rewrite.
- Keep adapter-pure tests and pipeline-orchestration tests separated as the suite grows.

## CI Profiles

- Expand the current split test profiles when additional CI infrastructure is introduced.
