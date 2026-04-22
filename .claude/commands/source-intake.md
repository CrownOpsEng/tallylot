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
9. `source normalize --update-mode auto` for the ordinary operator path
10. use `--update-mode full-update` when you need all current stage-owned
    detail refreshed from authoritative truth while unchanged kernels stay
    reused
11. use `--update-mode rebuild` when you need to bypass fast-path reuse and
    rebuild the implemented target-product chain from declared upstream truth
12. `source assemble` before reconciliation or downstream balance work; the
    assembled source dataset under `working/normalized/sources/<source>/` is
    the operator-facing handoff surface after normalization
13. review `facts.csv`, `exceptions.csv`, `normalization_reviews.csv`, and `normalization_summary.json`
14. confirm `normalization_summary.json` records automatic target-product execution details and the effective update mode
15. `checkpoint extract-pdf-balances` when supported statement PDFs need the
    standalone statement parser output that shares normalization's statement
    extraction path
16. `checkpoint scaffold-balance-submission` and
    `checkpoint submit-balances` when normalization did not already emit the
    balance outputs needed for the assembled source root
17. `reconciliation balances check` once the assembled source root contains
    the balance outputs needed for a deterministic source-level check
18. `reconciliation balances inspect`, `reconciliation balances check`, and
    `reconciliation balances summarize` when the task needs a multi-source
    balance answer instead of a source-local one
19. `output render file` when the round needs an external output artifact such
    as `cointracking_candidate.csv`
20. continue with `.claude/commands/round-verification.md` once a rendered
    candidate must move through oracle screening, staging, or round-close
    verification
21. `checkpoint rebuild-location-inventory` when normalization emitted
    per-source location inventory rows

Developer-only proof tooling:

- `tools.validate_workspace_replay` when you need to compare a rebuilt
  workspace against a reference workspace and confirm meaning parity during
  repo-side replay validation or migration proof

Use `docs/guides/operator-quickstart.md` for the short operator route,
`docs/guides/source-intake.md` for the detailed intake procedure, and
`docs/guides/normalize-screen-stage.md` for the next stage after normalization.
