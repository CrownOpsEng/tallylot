# Source Intake

Use this route for a full typed intake pass:

1. `source intake plan` before touching the workspace to see routing, package, overlap, and review decisions
2. review `intake_plan.csv`, `intake_issues.csv`, and `intake_summary.json`
3. `source intake apply` only when the plan is acceptable
4. `source manifest` for the settled capture path when you need a deterministic capture manifest
5. `source profile`
6. review `profile.json`, `profile_inventory.csv`, `timezone_issues.csv`
7. `source normalize`
8. review `exceptions.csv` and `normalization_reviews.csv`
9. `output render file` to create `cointracking_candidate.csv` when you need a compatibility candidate
10. `batch screen`
11. `batch stage` only if the screen passes
12. `source diff` when the candidate or a support slice needs a direct ledger comparison

Use `docs/operations/operations-quickstart.md` for the short operator route and
`docs/operations/mop.md` for the full workflow.
