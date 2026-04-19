# Implementation Checkpoint

Use this route before closing any non-trivial coding task.

1. Read:
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - use `markdown` for Markdown/docs work when that skill is available
   - use the shell-safe commit and PR authoring rules in
     `docs/standards/commits.md` when structured metadata is involved
2. Confirm the change still respects:
   - layer ownership
   - provider-neutral core design
   - CoinTracking tax and accounting reports stay in comparison tooling, not
     runtime state
   - `Decimal`-only financial handling
3. Check whether the task should have triggered a bounded refactor:
   - duplicate logic appeared
   - a second responsibility was added to a module
   - a hotspot module absorbed more behavior
   - tests became repetitive because the boundary is wrong
4. Confirm tests were added or updated for:
   - new decision logic
   - new parser or renderer contracts
   - fixed edge cases
   - meaningful regression prevention rather than trivial coverage
   - preserved parity when tests moved or consolidated
   - no silent assertion removal or fixture simplification that weakens
     coverage
5. Confirm tracked docs, templates, and control-plane text stayed neutral and
   did not pick up scratch workflow bookkeeping.
   Confirm durable delivery metadata stayed phase-free and roadmap-free, branch
   naming uses an approved `<root>/<slug>` root plus slug, and live docs policy
   enforcement stayed in the owning scripts rather than duplicated in pytest.
6. Confirm meaningful out-of-scope repo work is not stranded in notes:
   - search for an existing issue first
   - create the follow-up issue immediately when no suitable issue exists
   - keep issue content privacy-safe and repo-scoped
7. Run the appropriate verification path:
   - use fresh VS Code Problems diagnostics first when they are available and current
   - targeted tests while iterating
   - `make quality` before closing
     substantial work
   - reserve `make quality-full`
     for the explicit full-suite override when a specific task needs it
   - `make pr-review-full` when the change touches CI,
     packaging, release, or other workflow areas and you want the final non-draft PR suite locally
8. If architecture, schema, or sequencing changed, update:
   - `ROADMAP.md`
   - `docs/concepts/reconciliation-tax-architecture.md`
   - any boundary, matrix, or migration docs affected
   - if reconciliation, checkpoint, journal, tax, or target pipeline
     products changed, confirm the narrow routing docs still point to the right
     architecture and sequencing material:
     - `AGENTS.md`
     - `.claude/commands/reconciliation-tax-build.md`
     - `.claude/commands/adapter-authoring.md` when adapter areas are part
       of the same change
   - if forward-looking target names, ids, directory families, titles, or
     summaries changed, reload `docs/standards/engineering.md` and run
     `make naming-check`
   - if standards, docs placement, doc authoring rules, or agent-default enforcement changed, reload:
     - `AGENTS.md`
     - `docs/README.md`
     - `docs/status/current-state.md`
     - `docs/reference/repository-history.md`
     - `tools/docs_maintenance/cli.py`
     - `tools/docs_maintenance/metadata.py`
     and confirm any new material belongs in human docs rather than agent-only
     routing and still follows the docs-maintenance scaffold and metadata rules
9. After compaction or context loss, reload the narrow standards for the active
   area before more edits or commits:

   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - `docs/standards/delivery-guardrails.md` when delivery work is active

10. Create the stable checkpoint commit when the change is coherent and verified.
   If the task contains more than one separable reviewable change, split it into
   multiple bounded checkpoint commits before finishing. Do not close the task
   first and plan to commit afterward.

11. Include a short parity note in the checkpoint summary when tests changed:
    - what old behavior was covered
    - where that behavior is covered now
    - whether the assertion became stronger, weaker, or simply moved

12. Confirm branch handling stayed PR-only for protected branches: do not push
    directly to `main`; do not use branch-protection bypass for ordinary
    delivery; do not rewrite a merged `main` commit if the original pull
    request must remain attached to the merged commit and use a new repair
    pull request instead; for multi-checkpoint PR merges, use
    `<pr title> (#<pr number>)` as the merge subject; if a repair PR replaces
    an older PR, apply the repo's neutral duplicate/superseded label before
    closing the older PR; if the user explicitly requested a one-time
    protected-branch repair, verify the remote branch tip afterward and return
    to PR-only flow.
    For ordinary delivery work, confirm the active branch uses an approved root
    from `docs/standards/commits.md` and that branch names, commit messages,
    PR titles, and PR bodies stay phase-free and roadmap-free.

If a needed structural fix is already obvious and bounded, include it in the
same checkpoint instead of deferring it.
