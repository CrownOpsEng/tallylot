# PR Review

Use this route for repeatable review passes on an active branch or draft PR.

1. Reload only the narrow facts first:
   - `git status`
   - current diff and recent commits
   - current PR title, body, and changed files when PR work is active
   - `AGENTS.md` so the repo's task-routing table is back in context
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - latest targeted verification results
2. Use
   `make audit-pr-review`
   to identify the current diff's applicable surface groups, review domains,
   selected verification mode, selected and suppressed checks, and any
   unmapped paths before deciding the current pass found no new meaningful
   findings.
3. Re-check every prior fix surface first, then inspect the next applicable
   changed surface group that has not yet been re-checked in the current full
   loop.
4. Repair every finding from that pass before starting the next pass.
   - reload the narrow repo guidance for each repair surface using `AGENTS.md`,
     its task-routing table, and the owning roadmap, architecture, migration,
     or delivery docs surfaced by that route or by repo search hints
   - add or tighten tests, docs, automation, and validation where the fix
     belongs instead of leaving the repair in prose alone
   - when a meaningful finding should stay out of the active PR, search for an
     existing issue first and open or link the follow-up issue immediately
5. Rerun the required review checks for the repaired slice with
   `make pr-review`
   or, for CI, packaging, release, or workflow-sensitive repairs, with
   `make pr-review-full`,
   then create a bounded checkpoint commit before starting the next pass. Do not start another red-team pass with
   uncommitted repaired findings unless the pass is still in a very small
   in-progress slice.
   Do not describe an upcoming pass as clean, final, or publish-ready; every
   pass is issue-finding with open outcome.
   Do not treat a green `tools.run_pr_review_checks` result as a no-findings
   decision by itself; it is only the verification evidence for the current
   red-team pass.
6. Continue steps 1 through 5 until every applicable changed surface group has
   been revisited and a full applicable-surface loop yields no new meaningful
   findings. When a pass finds fewer than 5 findings, report only those
   findings. Do not invent findings to hit a quota.
7. If the only remaining item is a very minor finishing touch, repair it and
   finish once no other meaningful issues surface.
8. Keep scratch notes untracked. Do not create tracked issue ledgers, review
   logs, or temporary bookkeeping files.
9. Keep the PR draft until the full applicable-surface issue-finding loop
   yields no new meaningful findings. Before updating the PR state or marking
   it ready for review, finish with a clean working tree and reload the
   relevant delivery guidance or skills. Ensure any remaining out-of-scope repo
   findings are captured as linked follow-up issues rather than left in review
   prose alone.
