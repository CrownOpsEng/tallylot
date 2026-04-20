---
title: "Journal Contract"
summary: "Contract for the bounded `Journal` increment, including entry expansion, repo-owned entry checks, backend handoff, and downstream tax boundary rules."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 19
related:
  - docs/reference/economics-reconciliation-checkpoint-contract.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/bridge-to-target-mapping.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/reference/target-ids-and-refs.md
  - docs/reference/target-persistence-reference.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when implementing or reviewing the bounded `Journal` increment
after the bounded `EconomicFacts -> ReconciliationState -> Checkpoint`
contract. This document freezes scope, ids, backend boundaries, cutovers,
parity, replay, and allowed drift for the first journal slice over accepted
downstream truth.

**Contract-local example:** This contract still uses the bounded
planner-enabled Coinbase slice and its accepted checkpoint truth only to pin
the first journal parity boundary. Those source examples are contract-local
examples, not canonical target naming.

## Slice Scope

This slice is:

- journal expansion over authoritative `EconomicFacts` and `Checkpoint`
  kernels from the bounded downstream contract
- deterministic entry expansion for accepted event truth and accepted
  opening-state truth when the upstream checkpoint contract intentionally makes
  that opening truth authoritative
- explicit `EntryCheckRecord` emission and journal-owned gaps for unsupported
  mappings or blocked entries
- repo-owned backend orchestration over a replaceable journal backend seam,
  with `ledger_cli` as the first backend id and `ledger-cli` as the first
  downstream tool
- continued coexistence with current `cointracking_csv` compatibility
  rendering, which remains outside this slice

This slice is not:

- a repo-wide ledger redesign
- a replacement for `EconomicFacts`, `ReconciliationState`, or `Checkpoint`
  authority
- a cutover of `cointracking_csv` from its current compatibility path
- a tax-policy implementation or a hidden upstream authority for `TaxInputs`
- user-configurable chart selection or external chart-definition ingestion

## In-Scope Record Families

| Product | Record family | In-scope constraints |
| --- | --- | --- |
| `Journal` | `JournalEntryRecord` | `event` entries are required for supported accepted economic events in this slice; `opening` entries are canonically defined now and may remain zero-row until the upstream checkpoint contract intentionally emits accepted opening-state truth |
| `Journal` | `PostingRecord` | only postings derived from `economic_leg` or `checkpoint_assertion` origins in this slice, with deterministic account and unit mapping |
| `Journal` | `EntryCheckRecord` | only `balanced`, `unit_balance`, and `unsupported_mapping`, with explicit blocked posture on journal-owned gaps when expansion cannot proceed |

`JournalEntryRecord.kind = adjustment` is intentionally out of scope for this
first journal slice.

## Product Header And Downstream Inputs

Product header fields in this slice:

- `Journal` carries `journal_id`, `schema_version`, `checkpoint_ref`, and
  `economic_facts_refs`

Downstream-input rules:

- journal construction consumes authoritative `CheckpointRecord`,
  `CheckpointAssertionRecord`, `EconomicEventRecord`, and `EconomicLegRecord`
  rows
- journal construction may read accepted opening-state detail only when the
  upstream checkpoint contract declares that opening truth authoritative for
  the slice
- journal construction must not depend on `TransactionFact`, `facts.csv`,
  `balance_snapshots.csv`, `balance_references.csv`, `cointracking_csv`, or
  undeclared bridge hints as peer meaning inputs
- later tax work may inspect declared journal detail or backend findings only
  as non-authoritative downstream detail; they must not add `journal_ref`,
  backend file hashes, or backend-local ids to tax product identity,
  fingerprints, or product headers

## Backend Seam And Ownership

This slice freezes one replaceable journal backend boundary:

- `application/journal/` owns canonical journal expansion, repo-owned entry
  checks, backend orchestration, and backend-neutral journal detail generation
- `ports/journal_backends.py` owns `JournalBackend` and
  `JournalBackendRegistryPort`
- `infrastructure/journal_backends/ledger_cli/` owns the first backend
  implementation
- the first backend implementation is subprocess-backed and invokes
  `ledger-cli`; it is not an embedded journal authority
- the current fact-output rendering path remains the output boundary over
  facts and compatibility views
- `ports/output_adapters.py` remains the current output-adapter seam and is
  not reused for `Journal`
- the journal backend seam is intentionally replaceable so later repo-owned
  code or another backend can plug in without redefining journal authority,
  journal ids, or tax identity

## Chart, Unit, And Origin Restrictions

This slice freezes one deterministic journal-mapping posture:

- one emitted `Journal` kernel uses exactly one repo-owned `chart_id` across
  all `JournalAccountRef` values
- account codes in this slice come only from repo-owned journal mapping tables
  keyed to declared journal entry kind, economic leg role, checkpoint
  assertion kind, and acceptance basis
- `chart_id` is not a user namespace, renderer namespace, or journal backend
  namespace
- `JournalUnitRef.unit_kind` in this slice may be only `instrument` or
  `currency`
- `OriginRef.origin_kind` in this slice may be only `economic_leg` or
  `checkpoint_assertion`
- `event` entries carry one or more `event_refs` and zero `assertion_refs`
- `opening` entries carry one or more `assertion_refs` and zero `event_refs`

Not allowed in this slice:

- `JournalUnitRef.unit_kind = synthetic_unit`
- `OriginRef.origin_kind` values `claim`, `evidence_observation`,
  `market_input`, or `basis_adjustment`
- adapter-local account codes, renderer-local account codes, backend-owned
  account codes, or per-user chart namespaces as authoritative journal inputs

## Declared Journal Detail And Backend Artifacts

This slice freezes the journal-owned detail families and backend-specific
generated artifacts that downstream readers may inspect without turning them
into new authorities.

Backend-neutral journal files:

- `working/products/journals/<journal_id>/journal.json`
- `working/products/journals/<journal_id>/journal_posting_explanations.json`
- `working/products/journals/<journal_id>/journal_entry_check_reports.json`

Backend-specific `ledger_cli` files:

- `working/products/journals/<journal_id>/backends/ledger_cli/journal.ledger`
- `working/products/journals/<journal_id>/backends/ledger_cli/validation_findings.json`
- `working/products/journals/<journal_id>/backends/ledger_cli/report.xml`
  when the first backend emits a machine-readable report export

Rules:

- `journal.json` is the authoritative kernel; the other files in this section
  are generated detail
- backend-neutral detail files are product-local detail families, not kernel
  content, shared assessment outputs, compatibility views, or derived
  read-models
- backend-specific artifacts are generated detail, not kernel content,
  compatibility views, tax inputs, or product identity inputs
- `backends/` is allowed only because it splits immediately into backend-id
  families
- no generic root-level backend findings file survives beside the journal
  kernel
- `journal_posting_explanations.json` keys detail by `posting_id` and may
  repeat `entry_id` or `origin_ref` only for explanation
- `journal_entry_check_reports.json` keys detail by `entry_check_id` and
  `entry_id` and may explain why a check passed or blocked without becoming
  the only copy of blocked posture
- `journal.ledger` is the deterministic backend input generated for
  `ledger-cli`
- `validation_findings.json` keys detail by `entry_id` plus optional
  `posting_id` and records backend-local findings only after the authoritative
  kernel already names the checked scope
- `report.xml` is the optional machine-readable backend export when structured
  backend output is needed; scraped human-readable report text is not a
  contract surface
- persisted detail rows sort lexicographically by their owning stable ids and
  remain reproducible from authoritative `Journal` kernels plus declared
  upstream refs

## Validation Lanes

This slice uses two explicit validation lanes:

- Lane A is repo-owned entry checking over the canonical `Journal` kernel
- Lane B is `ledger_cli` validation over generated backend artifacts produced
  from that same `Journal`

Lane rules:

- Lane A is authoritative for journal-owned check outcomes
- Lane B is corroborating and backend-local
- Lane B must replay from `Journal` alone; `journal.ledger`,
  `validation_findings.json`, and `report.xml` are generated outputs of that
  replay, not extra meaning inputs
- Lane B may emit findings without changing `journal_id`, `entry_id`,
  `posting_id`, `entry_check_id`, or any `EntryCheckRecord` outcome
- backend-local balance assertions, formatting requirements, or rendering
  mechanics remain backend-local and do not redefine canonical `Journal`
  semantics
- repo-owned entry checks and backend validation may catch different failure
  modes, but backend findings do not replace journal-owned gaps or entry checks

## Kernel Cardinality And Ownership

Slice cardinality rules:

- one `Journal` is emitted per `[checkpoint_ref, economic_facts_refs]`
- one or more `JournalEntryRecord` rows may exist per `journal_id`
- one or more `EntryCheckRecord` rows may exist per `entry_id`
- an `expanded` entry must emit two or more `PostingRecord` rows
- a `blocked` entry emits zero `PostingRecord` rows in this slice; blocker
  meaning stays on `EntryCheckRecord` rows and journal-owned gaps

Ownership rules:

- `JournalEntryRecord` owns entry grouping, temporal placement, and upstream
  refs only
- `PostingRecord` owns account, unit, amount, side, and immediate origin only
- `EntryCheckRecord` owns entry-check outcome and blocking-gap refs only
- journal-owned gaps may explain unsupported mapping or blocked expansion, but
  they do not replace `EntryCheckRecord` rows
- backend findings may corroborate blocked or invalid backend output, but they
  do not replace `EntryCheckRecord` rows or journal-owned gaps

## Id And Fingerprint Rules

Use the stable-id and fingerprint rules from
[Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) unchanged.
This slice freezes the first journal cutover and backend bounds.

Slice-specific rules:

- `journal_id = [checkpoint_ref, economic_facts_refs]`
- `entry_id = [journal_id, kind, effective_at, event_refs, assertion_refs]`
- `posting_id = [entry_id, account_ref, unit_ref, amount, side, origin_ref]`
- `entry_check_id = [entry_id, kind]`

Not allowed in this slice:

- ids that hash renderer rows, backend files, explanation text, or
  compatibility files
- ids keyed only by account ordering, posting slot counters, or output row
  numbers
- `journal_id` components that include `journal_backend_id`, `tax_inputs_ref`,
  `tax_policy_id`, or renderer names

## In-Scope Journal Vocabulary

This slice allows only:

- `JournalEntryRecord.kind`:
  - `event`
  - `opening`
- `JournalEntryRecord.status`:
  - `expanded`
  - `blocked`
- `side`:
  - `debit`
  - `credit`
- `EntryCheckRecord.kind`:
  - `balanced`
  - `unit_balance`
  - `unsupported_mapping`
- `EntryCheckRecord.status`:
  - `passed`
  - `blocked`

Additional rules:

- `event` entries are required for supported accepted economic events in this
  slice
- `opening` entries are defined now but may remain zero-row until the upstream
  checkpoint contract intentionally widens to accepted opening-state truth
- `JournalEntryRecord.status` tracks expansion only; entry-check outcomes stay
  on `EntryCheckRecord.status`

Not allowed in this slice:

- `JournalEntryRecord.kind = adjustment`
- additional `EntryCheckRecord.kind` values

## Reader Cutover And Downstream Handoff

There is no same-scope bridge journal kernel to retire in this slice, but
reader cutovers are still required.

Rules:

- `Journal` becomes the authoritative product for in-scope journal entry
  expansion and entry-check results as soon as it is persisted
- journal-native renderers or journal inspection outputs introduced in this
  slice must read `Journal` directly and must not rebuild postings from
  `EconomicFacts`, `Checkpoint`, or compatibility bridge views
- `ledger_cli` is the first backend reader of `Journal`, and later backends
  must read through the declared journal backend seam rather than through
  fact-output adapters or output-rendering helpers
- current `cointracking_csv` and bridge compatibility outputs remain on their
  existing compatibility path; this slice does not repoint them or use
  `Journal` as an intermediate compatibility authority
- `TaxInputs` continue to derive authoritative tax input meaning from accepted
  `Checkpoint` plus `EconomicFacts`; they do not add `journal_ref` to product
  identity, fingerprint inputs, or product headers
- backend artifacts and backend findings may inform downstream rendering or
  review only as declared non-authoritative detail

## Parity Gates

There is no pre-existing authoritative journal kernel in the live bridge, so
the slice parity bar is split between deterministic journal meaning and
non-regression on downstream compatibility outputs that stay outside this
slice.

Unchanged authoritative `EconomicFacts` and `Checkpoint` inputs in this slice
must preserve all of the following:

- `journal_id` and product-root ordering
- `entry_id`, `posting_id`, and `entry_check_id`
- `JournalEntryRecord.kind`, `effective_at`, refs, and statuses
- `PostingRecord.account_ref`, `unit_ref`, `amount`, `side`, and `origin_ref`
- `EntryCheckRecord.kind`, `status`, and `blocking_gap_refs`
- declared backend-neutral detail row keys and ordering when any of this
  slice's detail files are persisted
- any `ledger_cli` validation result surface introduced with this slice
- any journal-native renderer output introduced with this slice
- unchanged `TransactionFact`, `facts.csv`, `balance_snapshots.csv`,
  `balance_references.csv`, balance inspect/check/summarize output, and
  `cointracking_csv` output, because this slice does not own or repoint those
  readers

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged authoritative
upstream products preserve:

- identical `Journal` kernel fingerprints
- identical row keys and ordering for any declared backend-neutral detail file
  introduced with this slice
- identical `ledger_cli` validation surfaces for any backend integration
  introduced with this slice
- identical journal-native renderer outputs for any renderer introduced with
  this slice
- identical zero-row or non-zero-row posture for `opening` entries on
  unchanged upstream checkpoint truth
- identical explicit blocked-entry surfaces, including `EntryCheckRecord`
  rows and journal-owned gap refs, when unchanged upstream truth still blocks
  expansion

Replay checks must also prove that incidental upstream ordering changes do not
change `journal_id`, `entry_id`, `posting_id`, `entry_check_id`, or any
declared backend or journal-native output.

## Allowed Drift

Not allowed:

- drift in `journal_id`, `entry_id`, `posting_id`, or `entry_check_id`
- drift in account mapping, unit selection, posting side, amount, or
  `origin_ref` on unchanged authoritative upstream inputs
- drift in entry-check kind, status, or `blocking_gap_refs`
- drift in declared backend-neutral detail row keying or ordering on unchanged
  authoritative upstream inputs
- drift in declared `ledger_cli` validation outcomes on unchanged
  authoritative upstream inputs
- drift in compatibility outputs that remain intentionally outside this slice

Allowed only when ids, ordering, statuses, and fingerprints stay unchanged:

- richer posting explanation text
- richer entry-check notes or annotations
- additional journal-owned gap or review sidecars
- additional backend annotations that do not change kernel meaning or declared
  validation outcomes
- additional journal-native renderer annotations that do not change kernel
  meaning

## Explicitly Out Of Scope

This slice does not:

- widen beyond the bounded
  [Economics Reconciliation Checkpoint Contract](economics-reconciliation-checkpoint-contract.md)
- require accepted opening-state truth as a first-slice success condition
- introduce `JournalEntryRecord.kind = adjustment`
- repoint balance inspect/check/summarize or `cointracking_csv`
- make `Journal` a hidden upstream authority for `TaxInputs` or `TaxOutputs`
- define tax policy execution, basis transitions, tax carry-forward rows, or
  filing outputs
- introduce external chart imports, per-user chart configuration, backend-owned
  chart namespaces, or output-adapter-owned chart namespaces
- treat `ledger-cli` as the ledger of record or as the source of authoritative
  journal ids
- route the journal backend seam through the current fact-output rendering path
  or `ports/output_adapters.py`
