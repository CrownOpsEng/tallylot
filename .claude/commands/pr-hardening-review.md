# PR Hardening Review

Use this route for repeatable review passes on an active branch or draft PR.

1. Reload only the narrow facts first:
   - `git status`
   - current diff and recent commits
   - current PR title, body, and changed files when PR work is active
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/commits.md`
   - latest targeted verification results
2. Review this fixed matrix:
   - design and ownership
   - correctness and behavior
   - complexity and over-engineering
   - tests and regression value
   - naming and public terminology
   - documentation and control-plane alignment
   - delivery controls, PR metadata, and issue handling
   - compaction and context-loss recovery
3. Re-check every prior fix surface first.
4. Add one adjacent surface group per pass.
5. Report up to 5 new evidence-backed findings.
6. Stop early when fewer real findings exist. Do not invent findings to hit a
   quota.
7. Keep scratch notes untracked. Do not create tracked issue ledgers, review
   logs, or temporary bookkeeping files.
8. Keep the PR draft until a full clean pass is complete. Mark ready for review
   only as a separate later action.
