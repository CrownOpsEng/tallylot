# PR Hardening Review

Use this route for repeatable review passes on an active branch or draft PR.

1. Reload only the narrow facts first:
   - `git status`
   - current diff and recent commits
   - current PR title, body, and changed files when PR work is active
   - `AGENTS.md` so the repo's task-routing table is back in context
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/commits.md`
   - latest targeted verification results
2. Red-team this fixed matrix and find up to 5 new unique findings for the
   current pass:
   - design and ownership
   - correctness and behavior
   - complexity and over-engineering
   - tests and regression value
   - naming and public terminology
   - documentation and control-plane alignment
   - delivery controls, PR metadata, and issue handling
   - compaction and context-loss recovery
3. Re-check every prior fix surface first, then add one adjacent surface group
   for the new pass.
4. Repair every finding from that pass before starting the next pass.
   - reload the narrow repo guidance for each repair surface using `AGENTS.md`,
     its task-routing table, and the owning roadmap, architecture, migration,
     or delivery docs surfaced by that route or by repo search hints
   - add or tighten tests, docs, automation, and validation where the fix
     belongs instead of leaving the repair in prose alone
5. Verify the repaired slice and create bounded checkpoint commits during the
   loop, following the repo's normal commit and checkpoint rules. Do not start
   another red-team pass with uncommitted repaired findings unless the pass is
   still in a very small in-progress slice.
6. Continue steps 1 through 5 until a full pass yields no new meaningful
   findings. When a pass finds fewer than 5 findings, report only those
   findings. Do not invent findings to hit a quota.
7. If the only remaining item is a very minor finishing touch, repair it and
   finish once no other meaningful issues surface.
8. Keep scratch notes untracked. Do not create tracked issue ledgers, review
   logs, or temporary bookkeeping files.
9. Keep the PR draft until a full clean loop has completed with no new
   meaningful findings. For a final PR review, finish with a clean working tree
   and reload the relevant delivery guidance or skills before updating the PR
   state or marking it ready for review.
