---
title: "Engineering Standards"
summary: "Code placement, typing, modularity, and naming rules for the typed application."
doc_type: standard
audience: human
owner: repo
status: active
naming_scope: repo_policy
nav_order: 10
---

Use this document for code-focused decisions only: placement, typing,
modularization, and naming.

**Current runtime note:** CoinTracking references in this standard describe
current output-adapter or oracle-local edges, not canonical target naming.

**Exception rationale:** When this standard names `assessment/` or
`domain/assessment/`, it is calling out the intentional shared root for the
nested `gap/`, `review/`, and `readiness/` families rather than endorsing a
generic catch-all boundary.

**Migration-only root rationale:** When this standard names
`application/compatibility/`, it is pointing to the bridge-only migration root
for derived compatibility views, not a durable application center.

**Locality rule:** When this standard names `source_slug`, `activity_label`, or
`provider_operation_key`, it is restating allowed bridge-local or
reporting-local terms so later contracts keep those exceptions explicit instead
of promoting them into downstream canonical naming.

## Layer Placement

Place code by responsibility, not by convenience:

- `domain/`: pure business models, value objects, enums, and shared typed
  aliases. No infrastructure, CLI, config-loader, filesystem, or network
  imports.
- `application/`: use-case orchestration, DTO assembly, and service logic over
  `domain` plus `ports`.
- `ports/`: `Protocol` contracts and narrow boundary types only.
- `infrastructure/`: implementations of `ports`, config loading, serialization,
  discovery, and workspace persistence details.
- `adapters/`: source and output adapters plus their adapter-local helpers.
- `interfaces/`: thin entry points such as the CLI. Interfaces orchestrate
  services; they do not own business rules.
- `repo_support/`: the current live shared support boundary for repo-native tooling
  and repo-side tests. Keep this outside `src/tallylot/` because it is not
  production/runtime code.

If a change crosses layer boundaries, refactor the boundary instead of
importing through it.

Repo-native support boundaries:

- `src/tallylot/` remains production/runtime code only.
- `tools/` remains the home for repo-native entry points and task-specific
  dev-only modules.
- `repo_support/` is the current live shared support boundary for repo-native tooling and
  repo-side tests.
- later implementation should rename that dev-only package area to `dev_support/`
  so the boundary is explicit.
- until that rename lands, `repo_support/` must stay narrow, typed,
  stdlib-first, and named by concept.
- do not let `repo_support/` become a generic catch-all while the repo is
  still on the current live name.

## Typing Rules

- Fully type all new and edited production code.
- Keep financial values in `Decimal`. Never introduce `float` for ledger or
  amount handling.
- Avoid `Any`. Only allow it at an unavoidable external boundary, then narrow
  it immediately.
- Annotate return types explicitly for public functions, service methods, and
  adapter entry points.
- Prefer typed DTOs, domain models, `Protocol`s, `Literal`s, and `NewType`s
  over loose `dict[str, object]` payloads.
- Model unsupported or ambiguous data as explicit issues or exceptions rather
  than widening types until everything fits.
- Tests inherit a narrower exception in `mypy` config, but test helpers should
  still stay typed unless doing so adds no value.
- Tests may exercise private helpers when the internal behavior is the thing
  under test. Import the private implementation directly from the module that
  owns it. Do not add package-root re-export shims, wrapper aliases, or widened
  production visibility for tests; use narrow, tool-supported test-side
  exclusions instead.
- Prefer the smallest available exclusion scope:
  - repo config for broad test-only policy
  - per-file config when an entire test module needs an exception
  - line-level suppression when only one access or one diagnostic needs relief

## Modularization Rules

Default to one responsibility per module.

- Keep most modules under roughly 300 lines.
- Start a split review once a module approaches 400 lines.
- Refactor before extending beyond 500 lines unless the file is mostly
  declarative models, typed schemas, or protocol definitions.
- Treat `500` lines as the official repo refactor limit.
- Enforced limit is `600` lines as the hard-stop lint ceiling.
- Keep the repo standard tighter than the enforcement ceiling so refactor
  expectations stay ahead of the hard-stop lint cap.
- Refactor by bounded concept, not by arbitrary suffixes.
- Do not add new dumping-ground modules such as `helpers.py`, `utils.py`,
  `misc.py`, or another catch-all `common.py`.
- Existing generic modules should shrink over time, not absorb more unrelated
  behavior.
- Apply the same rule to the current live `repo_support/` package area and the
  later target `dev_support/` package area. Shared repo-only support must be
  split by named boundaries, not collected under generic support modules.

When a capability grows, split by stable boundaries:

- `domain/`: separate models, value objects, and typed aliases by concept.
  Forward-looking target work should keep identity families split under
  roots such as `domain/instrument/`, `domain/location/`,
  `domain/ownership/`, `domain/counterparty/`, `domain/contract/`,
  `domain/position/`, `domain/evidence/`, `domain/claim/`,
  `domain/assessment/`, `domain/reconciliation/`, `domain/checkpoint/`,
  `domain/journal/`, and `domain/tax/` rather than recreating umbrella roots such as
  `domain/entities/`.
- `application/`: organize by bounded capability packages such as
  `application/intake/`, `application/profiling/`, `application/evidence/`,
  `application/claim/`, `application/economics/`,
  `application/compatibility/`, `application/normalization/`,
  `application/reconciliation/`, `application/assessment/`,
  `application/checkpoint/`, `application/journal/`, `application/tax/`, and
  `application/rendering/`. Keep request and response contracts in
  capability-local `contracts.py` files and keep orchestration entry points in
  explicitly named use-case modules such as `build_profile.py`,
  `normalize_source.py`, or `render_export.py`.
- `interfaces/`: keep command parsing and command execution thin; move real work
  into application use cases.
- `adapters/`: move larger adapters to package-style modules with an
  `adapter.py` entry point, a docstring-only package `__init__.py`, and local
  parser, mapper, issue, and fixture modules.
- `infrastructure/`: host reusable primitives only when they are genuinely
  cross-capability concerns such as filesystem guards, serialization, workspace
  persistence, or composition-root wiring. Do not push application policy down
  here just to share code.
- `repo_support/`: host reusable repo-only support only when it is shared by
  multiple repo-native areas such as `tools/` and `tests/`. This is the
  current live name for a later `dev_support/` target. Do not move
  production/runtime concerns here.

Mirror that structure in tests:

- place unit tests under the matching package path when a feature owns a
  package
- prefer `tests/unit/application/intake/...` over scattering
  `test_intake_*` files across unrelated directories

### Package Escalation Rules

Do not keep flattening files forever once a feature package exists.

- Use a feature package when a flat layer directory would otherwise collect
  more than 2 same-prefix files for one capability.
- Treat this as a hard refactor trigger, not a style preference. The third
  same-prefix sibling is the trigger. Regroup the capability in the same task
  instead of leaving a flat prefix cluster behind.
- Inside an existing feature package, create a nested subpackage when one
  bounded sub-capability meets any of these conditions:
  - 3 or more files share the same concept or repeated prefix
  - the cluster has its own models, decision rules, and entry point
  - the tests naturally group under that sub-capability rather than under the
    parent feature as a whole
- Do not create a nested package on the first split. Keep 2 tightly related
  files flat unless they already represent a stable subdomain.
- Prefer one clear level of nesting over long flat prefixes. `intake/packages/`
  is better than `intake/package_*.py` once the package-rule cluster becomes a
  subsystem.
- Prefer at most 2 package levels below the layer root unless a deeper tree is
  clearly justified by external contracts or provider boundaries.

Current application of this rule:

- `application/intake/` is the correct top-level feature package for intake.
- `application/profiling/` is the correct top-level feature package for source
  profiling workflows and profile file helpers.
- `intake/packages/`, `intake/archive/`, `intake/file_facts/`, and
  `intake/routing/` are the correct nested packages for the intake subdomains
  that now own their own models, rules, and entry points.
- `intake/plan/` is the correct nested package for intake planning workflows,
  planned-item models, review assembly, and report rendering.
- Normalization window and derived-balance helpers belong under
  `application/normalization/` rather than as nearby flat siblings.
- Forward-looking cross-stage gap, review, and readiness reducers plus
  readiness rollups and assessment views belong under
  `application/assessment/` rather than being buried under
  `application/reconciliation/`.
- Forward-looking journal expansion and entry checks belong under
  `application/journal/` rather than under a broader `accounting/` umbrella or
  as extra checkpoint-side helpers.
- Rendering belongs under `application/rendering/`; CoinTracking is one
  output adapter, not an application-center compatibility lane.
- Dev-only oracle tooling must live outside `src/tallylot/`.

## Naming Rules

- Name modules after the bounded responsibility they own.
- Keep public names and commands simple, neutral, and ergonomic. Prefer short
  names that match the user-visible operation over long implementation labels,
  and only add qualifiers when a real naming collision or ambiguity exists.
- For domain and contract surfaces, prefer the shortest accurate noun phrase.
  Cut migration, workflow, or implementation adjectives before cutting the
  owning noun that tells readers what the thing is.
- Apply that same content-first rule to doc frontmatter summaries and sync-
  managed docs-home blurbs. Lead with the held contract or content, not the
  page's governance role. Avoid role-first summary phrasing that leads with a
  page role or authority label instead of the held contract.
- In forward-looking summaries and docs-home blurbs, keep provider and custody
  nouns out of canonical target naming. If a page needs a provider-scoped
  exception, keep that wording in the labeled scope paragraph or example rather
  than in the summary or generated navigation blurb.
- Keep one stem aligned across the whole family. If the repo chooses
  `CheckpointProposal`, keep that stem in the record family, id fields,
  ref fields, slice contracts, roadmap, and package ownership docs. Do not
  let one target family mix competing stems.
- Keep sibling families parallel in style as well as stem. If one family uses
  short names such as `EvidenceFacet`, `ClaimFacet`, and `RenderFacet`, do not
  mix in a longer alternate or a different boundary noun for one sibling unless
  the whole family intentionally changes style.
- `StatementFacet` is the one sanctioned content-specific exception in that
  facet family because statement parsing is a distinct document boundary rather
  than a generic downstream stage.
- Keep the repo's `render` versus `rendering` split intentional. Use `render`
  for executable surfaces such as CLI verbs, facets, and operation modules, and
  use `rendering` for the bounded package or orchestration surface such as
  `application/rendering/`.
- Prefer the shortest stable stage noun for stage-owned package stems. Use a
  plural package stem only when the plural is itself the natural domain noun;
  do not pluralize a package just because it holds several records. For
  example, `application/checkpoint/` and `domain/checkpoint/` are clearer than
  looser collection labels.
- Keep that package-stem rule aligned with the contract family. For example,
  `application/claim/` and `domain/claim/` stay aligned with `ClaimSet`,
  `claim_scope_id`, `claim_bundle_id`, and `claim_id` better than a pluralized
  `claims/` package stem.
- Natural domain-noun package roots such as `economics/`, `profiling/`, and
  `rendering/` are allowed when the shorter adjective form would be less clear.
  Treat those as narrow exceptions, not permission for loose plural package
  names.
- When a stage, package root, and shared stage vocabulary all name the same
  boundary, use the same noun form across them. Prefer `economics` over
  `economic` for stage labels and shared stage vocabularies because the repo
  already owns `domain/economics/` and `application/economics/`.
- Once the repo has chosen `economics` for the stage and package noun, reserve
  `economic` for adjectival use inside that family rather than as a competing
  stage, package, or product-root stem.
- Prefer explicit identity-family package roots over umbrella containers once
  the owned families are already known. Use roots such as `instrument/`,
  `location/`, `ownership/`, `counterparty/`, `contract/`, `position/`,
  `assertion/`, and `journal/` instead of broader labels such as `entities/`,
  `assertions/`, or `accounting/` when the repo already owns the narrower
  boundary.
- Use `journal` for the end-state downstream stage, package, and
  product-adjacent family noun. Reserve `accounting` for broader prose,
  external schemas, or current bridge hints such as `AccountingIntentHint`.
- Name bounded-slice references by direction rather than by a bare ordinal.
  Prefer `First Upstream Slice Contract` and `First Downstream Slice Contract`
  over a generic `First Slice Contract`, and avoid repeating `current` in
  forward-looking slice names unless live runtime truth is the subject.
- When a helper ref belongs to one downstream stage rather than to a shared
  domain identity family, keep the stage noun on the helper type and keep the
  field name concise inside the owning record. Prefer
  `JournalAccountRef` with `PostingRecord.account_ref` and
  `JournalUnitRef` with `PostingRecord.unit_ref` over broader helper types such
  as `AccountRef` or `CommodityRef`.
- When sibling helper refs belong to the same stage-owned family, mirror the
  family stem across the whole sibling set. Prefer `JournalAccountRef` and
  `JournalUnitRef` over mixed stems that alternate between a stage-owned noun
  and one child-record noun.
- When a broad shared root is genuinely needed, keep the immediate children
  concrete and mirrored. `assessment/` is acceptable only when it is split into
  families such as `gap/`, `review/`, and `readiness/` rather than flattened
  into one catch-all boundary.
- Apply that same rule to persisted sidecar layout. Prefer paths such as
  `assessment/gap/gap_records.json` and
  `assessment/readiness/readiness_records.json` over one flat
  `assessment/` directory full of unrelated sidecar families.
- In forward-looking prose, prefer explicit family names such as `gap`,
  `review`, and `readiness` over the looser umbrella `shared assessment`
  when
  those are the actual owned families. Reserve generic `assessment` for
  intentional roots or bounded field names such as `domain/assessment/`,
  `assessment/`, or `support_shape`.
- When cross-stage support logic needs its own application boundary, give it
  the family noun directly, such as `application/assessment/`, rather than
  burying it under a neighboring stage package.
- `application/compatibility/` is acceptable only for migration-era bridge
  compatibility views and view writers. When a page or package uses that root,
  state directly that it is migration-only rather than a durable application
  center.
- Follow the same naming approach for modules, functions, classes, and commands:
  choose concise descriptive names over decorative jargon.
- Keep shape and casing aligned by role:
  - concepts use PascalCase nouns such as `BasisPool`
  - stable id helper types use `ThingId`
  - tuple helpers use `ThingRef`
  - persisted record families use `ThingRecord`
  - persisted fields and filenames use snake_case such as `thing_id`,
    `thing_ref`, `thing_refs`, and `thing.json`
- Reject verbose pattern-label suffixes such as `UseCase`, `Manager`, or
  `Handler` unless they disambiguate a real collision in the surrounding
  namespace.
- Reserve suffixes precisely:
  - `Ref` for canonical identity tuples or stable pointers
  - `Id` and `*_id` for stable identifiers only
  - `Key` and `*_key` when one slot may hold either a stable id or a canonical
    ref tuple
  - `Record` for persisted record families
  - `Explanation` for explanatory sidecars keyed to one kernel or support record
  - `View` for compatibility outputs or other reshaped reader-facing surfaces
  - `Projection` for transformation or mapping concepts rather than the
    persisted or emitted reader surface itself
  - `Rollup` for derived grouped records over subject or scope truth
  - `Summary` for reader-facing or compatibility aggregates that do not define a
    stable grouped kernel contract
  - `Sidecar` for attached non-kernel detail
- Reserve `rollup` for canonical target-layer grouped records and their ids.
  Reserve `summary` for current-state, presentation, or compatibility
  aggregates that are not the canonical grouped record family. Inside
  explanation or review sidecars, prefer concrete prose-field names such as
  `headline`, `known_facts`, or `follow_up` over `*_summary`.
- Do not use bare `summary` as a target-stage controlled-vocabulary value or
  package responsibility label when a more concrete output noun would say what
  the surface holds. Prefer names such as `policy_summary`,
  `supporting_schedule`, `filing_form`, `validation_report`, or
  `readiness_rollup` when those are the real shapes.
- When describing the fixed top-level fields that travel with every emitted
  product kernel, prefer `product header` over the more abstract `metadata`.
  Reserve `metadata` for looser descriptive prose, not for the canonical
  per-product field set.
- Prefer concrete owning nouns over abstract containers. Avoid names such as
  `Core`, `Data`, `Info`, `Context`, `Payload`, or `Item` when `Record`,
  `Explanation`, `View`, or the domain noun would say what the surface
  actually holds.
- Avoid abstract boundary labels such as `core` or `main` for forward-looking
  package, product, or concept names when the owning stage, layer, or domain
  boundary is already known. Prefer the explicit owner such as `domain`,
  `reconciliation`, `checkpoint`, `journal`, or `tax`.
- Keep record-family stems and id stems aligned. Prefer `GapRecord` plus
  `gap_id` or `ReadinessRecord` plus `readiness_id` over longer names that
  repeat context the record family already supplies, unless a real sibling
  family would make the shorter stem ambiguous.
- When a record-family noun would become generic out of context, keep the
  owning concept in the record-family stem even if child ids stay short.
  Prefer `EvidenceSelectionRecord` and `ClaimBundleDecisionRecord` over
  `SelectionRecord` or `BundleDecisionRecord` when the shorter record family
  would not reveal its owner cleanly across docs or code.
- Apply the same rule to downstream stage families whose local noun would stay
  generic outside the product. Prefer `TaxCarryForwardRecord` and
  `TaxUnsupportedInputRecord` over bare `CarryForwardRecord` or
  `UnsupportedInputRecord`.
- Apply the same rule to child-local fields, refs, and helper names. When the
  owning product or record already supplies the parent context, prefer the
  shortest truthful child noun such as `selection_id`, `proposal_refs`, or
  `assertion_ids` over longer forms that restate the parent stem.
- Keep scope families parallel from the id to the matching kind value. If the
  stable id is `claim_scope_id`, `checkpoint_proposal_id`, or
  `kernel_scope_id`, the matching `scope_kind` or `rollup_kind` value should
  be `claim_scope`, `checkpoint_proposal`, or `kernel_scope`, not a competing
  alternate stem.
- Do not shorten a child name when that child must travel outside the owning
  family and the shorter noun would become ambiguous across stages or products.
  Keep the longer owning stem only when that broader ambiguity is real.
- When one stage's child id becomes a stable downstream dependency, keep enough
  of the owning family noun to stay unambiguous outside that source stage.
  Prefer names such as `claim_bundle_id`, `claim_bundle_decision_id`, and
  `entry_check_id` over shorter forms such as `bundle_id`,
  `bundle_decision_id`, or `check_id` once those ids cross stage boundaries.
- When the record-family stem needs the owning stage noun to stay clear, keep
  that same stem on descendant ids and persisted basenames. Prefer
  `tax_carry_forward_id` and `tax_carry_forward_records.json` alongside
  `TaxCarryForwardRecord`.
- When a record or product owns one primary as-of time, prefer `as_of`.
  Add a longer prefix only when the same record carries multiple as-of fields
  or one field is explicitly naming another concept's as-of time.
- For checkpoint proposals, accepted checkpoints, and other acceptance-time
  contracts, prefer `as_of` over workflow labels such as `checkpoint_date`
  unless the field genuinely stores a calendar label rather than the contract's
  canonical as-of scalar.
- When a record owns one obvious child-id or child-ref family, prefer the
  child noun directly, such as `assertion_ids`, `proposal_refs`, or
  `target_refs`, over repeating the full stage or product stem.
- In prose or downstream contracts outside the owning record family, keep the
  full stage-owned noun when the shorter child noun would blur the family.
  Prefer `checkpoint proposal ids` or `checkpoint proposal lineage` over bare
  `proposal ids` or `proposal lineage` once the discussion leaves
  `CheckpointProposalRecord` fields.
- Apply the same rule to one obvious upstream-ref family or review-pair field
  inside a record. Prefer `member_refs`, `observation_refs`, `event_refs`,
  `assertion_refs`, or `gap_ids` over longer forms when the owning record
  already supplies the missing context.
- Use `*_id` and `*_ids` for stable-id fields that name the owned record
  itself or enumerate owned members directly.
- Use singular `*_ref` for one pointer to another product, record family, or
  reusable tuple ref and plural `*_refs` for an ordered list of those
  pointers. This includes same-product relationship fields such as
  `claim_refs`, `proposal_refs`, or `event_refs` when the field is describing
  lineage or ordered linkage rather than simply naming the owned member ids.
- Do not use a plural name for one required ref or id, or a singular name for
  a list-shaped contract.
- For stage-owned product-emission identities, prefer `emitter_id` and
  `emitter_key` over the more abstract `producer_id` and `producer_key`.
- When a product header or a record already supplies the owner, prefer the
  bare role field, such as `emitter_id` or `side`, over longer names such as
  `claim_emitter_id` or `posting_side`. Add the owning prefix only when one
  shape carries multiple fields of that role.
- In claim-stage contracts, prefer direct stems such as `claim_scope` over more
  abstract workflow labels such as `interpretation_scope` when the claim stage
  already owns that scope boundary.
- Fingerprints are scalar values, not refs. Use `fingerprint` when a record or
  product owns one primary fingerprint. Use `*_fingerprint` when the
  fingerprint belongs to another concept or when multiple fingerprint fields
  coexist. Reserve `*_ref` for product ids, record ids, tuple refs, or other
  explicit pointer shapes.
- Product ids default to `<product>_id`. If that would collide with a
  root-record id in the same product, use `<product>_set_id`
  rather than process labels such as `*_run_id`, `*_batch_id`, or `*_job_id`
  unless the product itself is truly a run, batch, or job.
- When one product owns exactly one root record and the product id and root
  record id naturally describe the same accepted object, prefer one shared
  `<product>_id` over inventing `<product>_set_id` only to separate metadata
  from that root record.
- Apply that same rule to root-record family names. If one product owns one
  natural root record, keep the simple root family stem, such as
  `CheckpointRecord`, instead of inventing a second label only to separate the
  product from its accepted root.
- Shared cross-stage support families that are repo-owned concepts in their own
  right may also stay short. Prefer `GapRecord`, `ReviewRecord`, and
  `ReadinessRecord` over longer prefixed variants that add no new meaning.
- For shared gap/review/readiness attachment over one emitted product kernel,
  prefer the explicit `kernel_scope_id` over generic names such as
  `dataset_id`.
- Name partition scopes after the actual stable dimensions the product id
  reduces over. If `TaxOutputs` depends on `TaxInputs` lineage plus policy and
  year, prefer `tax-inputs-policy-year-scoped` over a shorter label that hides
  lineage.
- Apply that same rule to mixed-upstream products. If `Journal` or `TaxInputs`
  depend on accepted checkpoint lineage plus ordered `economic_facts_refs`,
  prefer `checkpoint-economic-facts-lineage-scoped` over a shorter label such
  as `checkpoint-lineage-scoped`.
- Keep mixed-upstream header order, id recipes, and partition labels aligned.
  For checkpoint-economic-facts-lineage-scoped products, prefer
  `checkpoint_ref` before ordered `economic_facts_refs` in the product header
  and product-id recipe so the persisted contract reads in one stable order
  everywhere.
- When prose or helper formulas need the canonical lower-snake-case emitted
  product token, prefer `product_slug` over `product_name` so the stable token
  reads in parallel with `source_slug` and does not sound like display prose.
- For persisted files and workspace basenames, prefer the owning product or
  sidecar family in the filename. Avoid generic names such as `state.json`,
  `data.json`, `output.json`, or `results.json` when later call sites would
  need directory context alone to tell what the file holds.
- Inside `assessment/` directories that hold shared gap/review/readiness
  sidecars, split the directory first into `gap/`, `review/`, and
  `readiness/`, then make basenames mirror the stored record or explanation
  family. Prefer `assessment/gap/gap_records.json`,
  `assessment/review/review_records.json`,
  `assessment/readiness/readiness_records.json`, and
  `assessment/readiness/readiness_rollup_records.json` over one flat
  assessment directory or shorter plurals that need directory context to
  reveal shape.
- In forward-looking docs and code, reserve `artifact` for current-state bridge
  outputs, oracle/reference packages, or intentionally mixed file families.
  When the storage role is known, prefer `kernel`, `sidecar`, `view`,
  `file`, or `package`.
- In forward-looking migration prose, use `surface` for anything readers and
  writers cut over. Reserve `artifact` for current-state file families,
  oracle/reference bundles, or mixed packages where the stored shape itself is
  the point.
- In forward-looking migration docs, describe non-authoritative bridge outputs
  as derived compatibility views or compatibility sidecars. Reserve
  bridge-era process verbs such as `compiled` for live bridge implementation
  surfaces only.
- Reserve `surface` for migration, runtime-boundary, or application-boundary
  prose. For domain concepts, tuple refs, or record-family shapes, prefer
  nouns such as `state`, `shape`, `record family`, or `identity seam` over the
  looser `surface`.
- In canonical cutover matrices, use stable surface nouns or explicit file,
  view, or sidecar family names for rows and columns. Keep planner-local,
  debugger-local, or otherwise undeclared shapes in surrounding prose rather
  than presenting them as canonical matrix families.
- Prefer `kind` for a record's own primary one-of or variant field, and use
  `*_kind` when the field classifies another concept, a nested structure, or a
  sibling concept inside the same record. Reserve `family` for prose grouping
  of related record types, adapters, or artifact lines rather than for kernel
  field names.
- Prefer `kind` over `class` for controlled-vocabulary fields unless the
  contract is naming an established external taxonomy or genuinely modeling a
  class hierarchy.
- For canonical textual source identifiers, prefer `source_slug` over bare
  `source`. Reserve bare `source` for prose, for grouping dimensions whose
  enclosing field already states the role, or for source-scoped provider
  families where the contract is not storing the slug itself.
- Inside canonical target rollups, use the actual grouping identifier in
  `rollup_kind` when the key is itself a canonical identifier.
- Keep canonical target rollup families stage- and domain-oriented. If
  operators still need source-grouped views, expose them as assessment views or
  compatibility views rather than as shared target `RollupRecord`
  vocabulary members.
- Prefer concrete held-shape nouns over abstract container prose. Do not use
  labels such as `emission root`, `output root`, or `root truth container`
  when the actual kernel, record family, or persisted view already names what
  the surface holds.
- When an assessment view or compatibility view truly stores the shared
  source slug as its grouping key, prefer `source_slug` over bare `source`.
- In canonical target-layer evidence and claim contracts, use `source_*` only
  when the field truly stores source identity or another source-derived value
  that would be ambiguous without the prefix. When the stage already supplies
  that locality, prefer the shorter held-thing noun such as `activity_label`,
  `location_label`, or `statement_kind` over `source_local_*`.
- `statement_kind` and `balance_kind` are locality-preserving bounded field
  names, not shared downstream vocabulary families. Keep them only where the
  owning evidence or slice contract explicitly freezes that locality.
- When a contract page freezes an allowed locality exception such as
  `source_slug`, `activity_label`, `provider_operation_key`, or
  `AccountingIntentHint`, restate that locality at the owning field table or
  immediately adjacent prose rather than leaving the exception only in this
  standards page.
- No valuation-measure field name is frozen in this repo yet. Do not add one to
  forward-looking claim or record tables until a real shared valuation measure
  taxonomy exists.
- `SubjectRef` serializes as `[subject_kind, subject_key]`. Use `subject_key`
  because the second slot may hold either a stable record id or a canonical ref
  tuple such as `PositionRef`.
- When a record owns one primary lifecycle, decision, or resolution field,
  prefer plain `status`, `basis`, or `outcome` over repeating the record stem.
  Add a prefix only when the field describes another concept's status or basis
  rather than the record's own state.
- Keep plain `status` when a record owns one primary state axis. If one record
  is mixing comparison result, observation presence, supersession, or blocker
  posture inside one field family, split the model into distinct fields instead
  of papering over the problem with a longer `*_status` name.
- Prefer `status` over `state` for bounded field vocabularies. Reserve
  `State` for named domain concepts or broader state bundles when `status`
  would underspecify the concept.
- For materiality or weight vocabularies, prefer direct reader-facing labels
  such as `material`, `supporting`, or `informational` over murkier middle
  labels such as `contextual` when the repo means evidentiary weight rather
  than surrounding circumstances.
- Apply the same status-versus-state rule to named vocabulary concepts.
  Prefer concept names such as `SettlementStatus` when the concept is a
  bounded status family rather than a broader state bundle.
- When a record owns one primary classification, role, or intent field,
  prefer plain `kind`, `role`, `side`, or `purpose` over
  repeating the record stem. Add a longer prefix only when the same record
  carries multiple fields of that family or the field describes another
  concept's role or purpose.
- For controlled vocabularies on one record-local kind field, prefer singular
  nouns or noun phrases such as `economic_event`, `adjustment`,
  `carry_forward`, or `unsupported_mapping` unless the value truly names a
  collection artifact rather than one record-local kind.
- When a `kind` field already supplies the owning family, keep the value as a
  lower-snake noun phrase and do not repeat the owner noun. Prefer values such
  as `activity`, `instrument`, `beneficial_owner`, or `statement_document`
  over pseudo-type labels such as `instrument_identity`,
  `ActivityClaim`, or `StatementObservation`.
- When one emitted product already gives a persisted concept its own sibling
  record family, do not repeat that sibling family as a `kind` value inside a
  different record family. Prefer distinct output-group kinds over values that
  merely restate sibling families such as tax carry-forward or tax
  unsupported-input records.
- Keep all members of one bounded vocabulary on the same semantic axis. Use
  trust or readiness tiers for `trust_level`, support shapes for
  `support_shape`, and acceptance reasons for `basis` instead of mixing those
  dimensions inside one field family.
- Apply that same rule to claim-bundle decisions. `ClaimBundleDecisionRecord`
  keeps posture on `outcome` and reason on `basis`; do not mix defer or
  supersession posture back into the `basis` vocabulary.
- When adjacent vocabularies live on different semantic axes, do not reuse one
  slice-local label across all of them if that would blur reason, support
  shape, and continuity shape. Prefer reason labels such as
  `document_support`, `reported_support`, `manual_support`, and
  `reconciled_continuity` in `basis`, observation-shape labels such as
  `document_observation`, `reported_observation`, and `manual_assertion` in
  `support_shape`, and continuity-shape labels such as
  `observed_continuity`, `reconciled_rollforward`,
  `opening_rollforward`, and `partial_rollforward` in `continuity_kind`.
- Do not reuse a label such as `reported_observation` or `manual_assertion`
  across both `basis` and `support_shape` just because one slice happens to
  allow both; keep the reason axis and the support-shape axis distinct.
- For bounded `basis` or similar reason vocabularies, drop redundant suffixes
  such as `_match`, `_preferred`, or `_duplicate` when the field already
  establishes that the value is the decision basis.
- Reserve `proof` for proof artifacts or explicit proof-bearing detail.
  When a bounded field selects one continuity or support classification from a
  vocabulary, prefer `*_kind` or `*_basis` over `*_proof`.
- In forward-looking target kernels, avoid `*_hint` for fields that are part of
  the declared emitted claim or record shape. Reserve `*_hint` for current
  bridge surfaces, compatibility sidecars, or genuinely non-authoritative
  adapter-local hints.
- In forward-looking target kernels, avoid actor-specific canonical names such
  as `operator_*` when the concept is a generic manual or user-supplied input.
  Prefer neutral names such as `manual_assertion` unless the actor identity is
  itself the owned business concept.
- Apply the same naming rules to observation kinds and controlled-vocabulary
  members. Name the held thing or decision shape directly instead of hiding it
  behind abstract labels such as `identity` or `anchor` when the canonical
  noun is already known.
- For canonical target observation kinds and claim kinds, keep provider labels
  and redundant `Observation` or `Assertion` qualifiers out of the canonical
  name when the owning stage already supplies that context and the shorter
  name stays unambiguous. Reserve provider prefixes for adapter-local or
  genuinely provider-exclusive kinds.
- In issue, review, and check vocabularies, prefer direct required-decision or
  unsupported-shape names over long nominalizations such as
  `*_required_determination` when a shorter label stays explicit.
- Keep controlled-vocabulary members parallel inside one field family. If a
  balance-target vocabulary names balance shapes, prefer values such as
  `exact_balance`, `range_balance`, and `boundary_balance` over mixing balance
  shapes with support metaphors.
- In kind vocabularies for emitted records, drop only truly redundant
  output-surface suffixes when the record family already tells the reader they
  are looking at an output or emitted state surface. Keep shape nouns such as
  `schedule` or `form` when they distinguish the held output from sibling
  kinds.
- Do not encode nullability in canonical target field names. Use the base noun
  or ref name and state optionality in the field contract rather than in
  suffixes that spell out nullability.
- Do not encode canonical ordering or record-local support role in a target
  field name when the enclosing contract already provides that meaning.
  Drop redundant ordering prefixes and contextual support adjectives when the
  record already establishes the relationship.
- Prefer `key` or `locator` when a record owns one primary discriminator or
  one primary locator. Use `*_key` or `*_locator` when the field belongs to
  another concept or when one record carries multiple fields of that shape.
  Avoid more abstract labels such as `*_anchor` or redundant labels such as
  `*_discriminator` when the field simply holds the stable key for that parent
  scope.
- For reusable ref tuples that serialize or flatten across many products, keep
  explicit slot names such as `subject_kind`, `origin_kind`, `policy_key`, or
  `position_key` when bare `kind` or `key` would become ambiguous outside the
  owning type declaration.
- When one record or nested entry carries one primary precision or slot field,
  prefer `precision` or `slot`. Add a longer prefix only when multiple
  precision or slot fields coexist in the same shape.
- Prefer `name` over `display_name` in forward-looking target contracts unless
  the same shape also carries a distinct canonical name, legal name, or other
  parallel naming field that makes `display_name` materially clearer.
- When a product header carries an ordered set of upstream refs, keep any
  matching product-id component array in that same canonical order unless the
  contract page documents a stronger reason to differ.
- Inside aggregate rollup records, use `rollup_kind` and `rollup_key` for the
  grouping dimensions so `rollup` remains the record shape instead of becoming
  a second generic field prefix.
- Inside aggregate rollup records, drop repeated subject or entity nouns from
  count fields when the rollup already establishes that context. Prefer
  `ready_count` over `ready_subject_count`.
- Prefer `Proposal` for stage-owned pre-acceptance records that later become
  accepted truth. Reserve `Candidate` for raw search-space options or other
  unmanaged alternatives that the owning stage has not yet shaped into a
  proposal.
- When a record links or checks another owned concept, include that concept in
  the stem when the shorter noun would be generic across stages. Prefer
  `EventLinkRecord` or `EntryCheckRecord` over ambiguous cross-stage names such
  as `LinkRecord` or `ValidationRecord`.
- When owner docs or bounded-slice refs describe a stored record family in
  prose, reuse the stored family noun instead of swapping to a looser nearby
  synonym. Prefer `entry checks`, `checkpoint proposals`, and `readiness
  rollups` when those are the persisted families, and reserve broader prose
  such as `validation`, `proposal`, or `summary` for the surrounding stage
  behavior rather than for the stored shape itself.
- When a stage owns a dedicated check record family, prefer that family noun in
  forward-looking prose for stage-owned persisted outputs and sidecars.
  Reserve broader `validation` wording for human review, workflow posture, or
  adapter-edge rules rather than for the canonical target check family.
- Once `Journal` owns `EntryCheckRecord`, prefer `entry check` or
  `entry-check` wording over generic `validation` when naming target-stage
  journal records, prose, or package responsibilities.
- Apply that same rule to controlled vocabularies. Keep journal-entry expansion
  status separate from entry-check results. Prefer `expanded` or `blocked` on
  `JournalEntryRecord.status`, and reserve `passed` or `blocked` for
  `EntryCheckRecord.status`.
- In target controlled vocabularies, keep the stage noun and held-thing noun
  aligned once the target stage owns the boundary. Prefer
  `economic_measurement`, `checkpoint_measurement`, `journal_measurement`, and
  `tax_measurement` over mixed-purpose labels, and `unit_balance` over
  `commodity_balance` on end-state target surfaces.
- When one `kind` family mixes quantities, amounts, and state, keep those
  suffixes parallel across the sibling values. Prefer families such as
  `position_quantity`, `cash_amount`, `basis_amount`, `owner_state`, and
  `location_state` over mixing bare nouns or generic `*_value` labels into the
  same target-controlled vocabulary.
- When a target-layer `kind` is naming one shared domain concept and the
  narrower detail lives in the fields, keep the shared domain noun as the kind.
  Prefer `contract` over `contract_term` when the kind still belongs to the
  shared `Contract` family.
- Use generic shared nouns only for intentionally repo-owned cross-stage seams.
  Names such as `SubjectRef` or `OriginRef` are allowed only when the
  abstraction itself is the owned contract. Everywhere else, prefer the
  narrowest truthful concept name over a broader shared label.
- Do not fork parallel helper-ref families when one shared tuple already owns
  the same meaning. Reuse repo-owned seams such as `OriginRef` instead of
  minting stage-prefixed variants for the same `[origin_kind, origin_id]`
  shape.
- Prefer the base noun when a field already stores the locator or ref itself.
  Avoid extra suffixes such as `_identity` when `locator` or
  `origin_ref` already says what the value holds.
- In explanation sidecars, drop guidance adjectives once the field role already
  implies them. Prefer `possible_meanings`, `resolution_options`,
  `next_action`, or `follow_up` over `candidate_meanings`,
  `allowed_resolution_methods`, `recommended_next_action`, or
  `recommended_follow_up` unless the longer form changes the contract.
- For compatibility-only material that is not a target concept, name it by
  boundary and role rather than promoting it to a pseudo-domain type.
  Prefer `bridge annotation sidecar detail`, `output annotation sidecar`, or
  `compatibility sidecar` over introducing a new canonical-seeming type name in
  forward-looking docs or code.
- Name the held thing separately from its identity seam or persistence shell:
  `BasisPool` is a concept, `BasisPoolRef` is its ref, and
  `BasisTransitionRecord` is a kernel row family.
- When prose is naming one persisted emitted family rather than the broader
  concept, use the record-family noun. Prefer `checkpoint proposal records`,
  `readiness records`, or `tax carry-forward records` over looser prose such as
  `proposals`, `readiness`, or `carry-forward state` when the stored shape is
  the point.
- Prefer specific names such as `csv_parser.py`, `balance_mapper.py`, or
  `issue_rules.py` over generic names.
- Match package structure to the architecture first and the external provider
  second.
- New domain and application names should avoid crypto-exclusive language
  unless the concept is genuinely adapter-local or asset-class-specific.
- In forward-looking target-layer names, keep source or asset-class nouns such
  as `wallet`, `exchange`, `address`, `token`, `lot`, `chain`, and `tx_hash`
  on source-evidence, adapter-local, compatibility, or current-state surfaces
  unless the target concept is genuinely that specific. Prefer repo-owned
  canonical nouns such as `Location`, `Instrument`, `Position`, `Contract`,
  `EventLink`, or `CheckpointAssertion` when those are the broader end-state
  seams.
- Once the pipeline moves past evidence-local products such as `EvidenceSet`
  and `ClaimSet`, do not keep provider or source-system nouns in later product
  record names, helper refs, stable ids, or partition labels unless those
  nouns are themselves the persisted concept. Prefer lineage-, origin-, or
  subject-owned names over carry-through source labels in downstream kernels.
- When a forward-looking contract page needs a provider-scoped or slice-scoped
  exception, keep that provider noun in the scope paragraph, example, or
  bounded-slice section rather than in canonical target record names, helper
  refs, stable ids, or directory stems.
- Apply that same locality rule to titles, frontmatter summaries, and sync-
  managed docs-home blurbs. Forward-looking navigation copy should remain
  provider- and custody-neutral unless the page itself is intentionally local
  current-state, bridge-only, oracle-only, or adapter-local documentation.
- Assessment views and compatibility views may still group by
  `source_slug` where operators need that reporting lens, but that dimension
  must not leak into downstream product ids, record ids, authoritative
  directory stems, or canonical readiness-rollup vocabularies.
- When a canonical target contract must preserve a source-provided label,
  preserve the value without freezing the source noun into the field name.
  Prefer target-aligned names such as `location_label` over
  source-specific names such as `wallet_label` when `Location` already owns
  the shared boundary.
- When one canonical target contract must preserve both a higher-scope and a
  lower-scope source-provided location label, prefer
  `location_group_label` and `location_label` over source-era pairs such as
  `account_label` and `wallet_label`.
- For stable keys and default directory stems, prefer the shortest durable
  domain noun that preserves identity. Do not carry venue-, market-, or
  asset-class-specific qualifiers into default keys such as `position_key`
  when the broader noun already owns the slice.
- In forward-looking prose, use `primary evidence`, `evidence-backed`, or the
  concrete corroboration noun when describing trust or corroboration quality.
  Reserve
  `source_*` names for actual source identity such as `source_slug`,
  source-scoped adapter families, or current-state/source-local surfaces.
- Prefer product-aligned nouns over abstract process jargon when the product
  already owns the boundary. For example, `TaxInputRecord` is clearer than a
  more abstract tax-record noun when the record is the kernel row inside
  `TaxInputs`, and `JournalEntryRecord` is clearer than a more abstract
  accounting-entry noun once `Journal` is the owned product family.
- In forward-looking workflow prose, use the emitted product name once the
  contract page already freezes that boundary. Prefer phrases such as
  `build EconomicFacts`, `build ReconciliationState`, or `emit TaxOutputs`
  over looser process wording such as `compile accepted economics`.
- In forward-looking target persistence, authoritative directory stems should
  follow the owning product or sidecar family. Keep source- or checkpoint-local
  directory stems only for current-state, compatibility, or genuinely
  source-owned or checkpoint-owned surfaces.
- Do not bake migration qualifiers such as `bridge`, `legacy`, `current`, or
  `compat` into canonical target-layer concepts, helper ids, or product ids
  unless the name is intentionally current-state or adapter-local.
- Under `adapters/sources/`, group packages by source kind before the provider:
  `platforms/<provider>/`, `wallets/<provider>/`, `explorers/<provider>/`,
  `portfolio/<input_kind>/`, `generic/<contract>/`, or `stubs/<reserved>/`.
- Keep naming stable across implementation, tests, adapter metadata, and owner
  docs.
- When `domain/`, `application/`, and tests each own the same capability
  family, keep the package stem aligned across those layers unless the layers
  truly own different concepts.
- In prose, prefer the canonical owning noun once a target product or record
  family already exists. Use phrases such as `claim bundle`, `claim scope`,
  `evidence-local meaning`, and `product scope` over looser labels such as
  `semantic bundle`, `semantic scope`, or `whole-kernel` unless the extra
  abstraction is the point.
- Prefer the shortest boundary noun that still distinguishes the seam. When one
  package exists only to host migration compatibility views,
  `compatibility/` is clearer than `bridge_compatibility/` unless another
  compatibility boundary would make the shorter name ambiguous.

### Ten-View Naming And Congruency Audit

Run this audit before freezing or renaming any forward-looking product, record
family, ref, id, package, or file name.

1. Concept view: does the name say what the thing is in end-state domain terms,
   not just when it is used in the workflow, and would it still read correctly
   if the source were not crypto-specific?
2. Shape view: does the noun match the held shape exactly: concept, id, ref,
   record, rollup, summary, sidecar, view, projection, file, package, observation
   kind, or controlled-vocabulary value?
3. Ownership view: does the name point at the owning stage, layer, or
   boundary instead of a generic cross-stage label?
4. Persistence view: do field names, filenames, and package paths make the
   held truth obvious without relying on directory context alone, and do local
   discriminators use keys rather than anchors or other abstract stand-ins?
5. Migration view: are bridge, current, legacy, compat, oracle, output, and
   source-specific qualifiers or nouns kept only on intentionally
   non-canonical surfaces?
6. Family view: do record families, ids, refs, filenames, and bounded
   vocabulary members keep one shared stem and mirrored role naming across the
   whole family?
7. Kind-value view: do `kind` values name the held thing directly without
   repeating the owning family or drifting into pseudo-type labels?
8. Source-bleed view: are source-system, provider, asset-class, bridge-era,
   or oracle nouns kept only on intentionally local, compatibility, or
   current-state surfaces?
9. Parallel-family view: do sibling products, record families, helper refs,
   and package stems mirror each other in suffix, role naming, and vocabulary
   style?
10. Paired-axis view: do paired fields or vocabulary families such as
    `basis`, `support_shape`, and `continuity_kind` stay on distinct semantic
    axes without overlapping or drifting into synonyms?

When one canonical target name changes, update every primary contract page,
bounded-slice reference, roadmap phase, contract reference, and control-plane
routing page that uses that family in the same patch. Do not leave competing
target names alive in parallel.

### Catalog-First Target Naming Governance

`tools/target_naming_catalog.yaml` is the operational authority for
forward-looking end-state naming on the enforced target surfaces.

Rules:

- update the catalog before introducing or renaming a canonical target term
- update every affected detailed contract page, bounded-slice reference,
  roadmap surface, and standards surface in the same patch
- keep frontmatter summaries and generated `docs/README.md` blurbs
  content-first; do not lead with page-role or authority-first labels that
  foreground governance instead of the held contract
- keep provider, custody, and other source-local nouns out of forward-looking
  titles and summaries unless the summary is intentionally local to a bounded
  slice
- run `python -m tools.target_naming check` or `make naming-check` before
  landing a naming change
- use `python -m tools.target_naming report --json` when a PR, script, or
  future dashboard needs machine-readable findings
- treat the blocking `target-naming` review check as the repo-native guard
  against new undocumented target names or renamed families

## Refactor-First Hotspots

Split these modules before adding materially new behavior:

- `src/tallylot/application/intake/packages/resolution.py`
- `src/tallylot/adapters/sources/platforms/binance/adapter.py`

Preserve these shared package boundaries instead of collapsing them back
into single modules:

- `src/tallylot/domain/transactions/`
- `src/tallylot/interfaces/cli/`
- `src/tallylot/infrastructure/discovery/adapters/`
