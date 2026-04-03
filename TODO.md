# TODO

- Add a repo-local scaffold command for new adapter packs so future sources can ship raw fixtures, metadata, and golden outputs in one step.
- Add a golden-refresh command that rewrites pack expectations after intentional adapter changes and fails if uncommitted drift remains.
- Add a CI split between adapter-pack tests and broader CLI/e2e script coverage.
- During the planned repo refactor, move adapters and their packs toward a plugin layout so each adapter owns its code, fixtures, and tests together.
