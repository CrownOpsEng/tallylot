# Source Intake

Use this route for a full typed intake pass:

1. update `analysis/issues/source_label_map.csv` first when the incoming capture should preserve a stable operator-managed source label across source-scoped raw or working paths
2. `source intake plan` before touching the workspace to see routing, package, overlap, source-resolution, and review decisions
3. review `intake_plan.csv`, `intake_issues.csv`, and `intake_summary.json`
4. `source intake apply` only when the plan is acceptable
5. `source manifest` for the settled capture path when you need a deterministic capture manifest
6. `source profile`
7. review `profile.json`, `profile_inventory.csv`, `timezone_issues.csv`
8. `source normalize`
9. review `facts.csv`, `exceptions.csv`, `normalization_reviews.csv`, and `normalization_summary.json`
10. `checkpoint rebuild-location-inventory` when normalization emitted wallet evidence
11. `output render file` when the round needs an external output artifact such as `cointracking_candidate.csv`

Use `docs/guides/operator-quickstart.md` for the short operator route,
`docs/guides/source-intake.md` for the detailed intake procedure, and
`docs/guides/normalize-screen-stage.md` for the next stage after profiling.
