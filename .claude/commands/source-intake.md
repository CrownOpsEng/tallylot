# Source Intake

Use this route for a full typed intake pass:

1. `source intake plan` before touching the workspace to see routing, package, overlap, and review decisions
2. review `intake_plan.csv`, `intake_issues.csv`, and `intake_summary.json`
3. `source intake apply` only when the plan is acceptable
4. `source manifest` for the settled capture path when you need a deterministic capture manifest
5. `source profile`
6. review `profile.json`, `profile_inventory.csv`, `timezone_issues.csv`
7. `source normalize`
8. review `facts.csv`, `exceptions.csv`, `normalization_reviews.csv`, and `normalization_summary.json`
9. `checkpoint rebuild-location-inventory` when normalization emitted wallet evidence
10. `output render file` when the round needs an external output artifact such as `cointracking_candidate.csv`

Use `docs/guides/operator-quickstart.md` for the short operator route,
`docs/guides/source-intake.md` for the detailed intake procedure, and
`docs/guides/normalize-screen-stage.md` for the next stage after profiling.
