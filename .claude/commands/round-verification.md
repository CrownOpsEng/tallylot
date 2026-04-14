# Round Verification

Use this route after a manual repair or import in the external verification tool.

1. `make oracle ARGS='round scaffold'`
2. save the fresh verification export set under `working/verification/<round_id>/`
3. `make oracle ARGS='verification compare'`
4. review the comparison package
5. update issue, source, and round-log records

Use `docs/guides/verify-a-round.md` for the detailed round procedure and
`docs/reference/export-checklist.md` for the verification export set.
