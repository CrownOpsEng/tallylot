# Round Verification

Use this route once a rendered candidate must move through oracle screening,
staging, source diff, or round-close verification.

1. `make oracle ARGS='batch screen'`
2. stop when the screen artifacts report a blocking failure
3. `make oracle ARGS='batch stage'` only after the screen passes
4. `make oracle ARGS='source diff'` when a candidate or reference slice needs
   deterministic row comparison before import
5. `make oracle ARGS='round scaffold'`
6. save the fresh verification export set under `working/verification/<round_id>/`
7. `make oracle ARGS='verification compare'`
8. review the comparison package
9. update issue, source, and round-log records

Use `docs/guides/normalize-screen-stage.md` for the candidate preparation,
screen, and stage procedure, `docs/guides/verify-a-round.md` for the detailed
round procedure, and `docs/reference/export-checklist.md` for the verification
export set.
