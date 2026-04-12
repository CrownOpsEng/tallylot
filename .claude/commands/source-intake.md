# Source Intake

Use this route for a full typed intake pass:

1. update `analysis/issues/source_label_map.csv` first when the incoming capture should preserve a stable operator-managed source label across source-scoped raw or working paths
2. make sure the source already exists in `analysis/issues/source_inventory.csv`; the planner uses the incoming directory name as the capture scope, so a scoped label-map row can target the exact staging directory
3. `source intake plan` before touching the workspace to see routing, package, overlap, source-resolution, and review decisions
4. review `intake_plan.csv`, `intake_issues.csv`, and `intake_summary.json`
5. `source intake apply` only when the plan is acceptable
6. `source manifest` for the settled capture path when you need a deterministic capture manifest
7. `source profile`
8. review `profile.json`, `profile_inventory.csv`, `timezone_issues.csv`
9. `source normalize`
10. review `facts.csv`, `exceptions.csv`, `normalization_reviews.csv`, and `normalization_summary.json`
11. `checkpoint rebuild-location-inventory` when normalization emitted wallet evidence
12. `output render file` when the round needs an external output artifact such as `cointracking_candidate.csv`
13. `tools.validate_workspace_replay` when you need to compare a rebuilt workspace against a reference workspace and confirm semantic parity

Use `docs/guides/operator-quickstart.md` for the short operator route,
`docs/guides/source-intake.md` for the detailed intake procedure, and
`docs/guides/normalize-screen-stage.md` for the next stage after profiling.
