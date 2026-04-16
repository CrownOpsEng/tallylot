---
title: "Engineering Standards"
summary: "Code placement, typing, modularity, and naming rules for the typed application."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 10
---

Use this document for code-focused decisions only: placement, typing,
modularization, and naming.

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
- `application/`: organize by bounded capability packages such as
  `application/intake/`, `application/profiling/`, `application/normalization/`,
  `application/checkpoints/`, and `application/outputs/`. Keep request and
  response contracts in capability-local `contracts.py` files and keep
  orchestration entry points in explicitly named use-case modules such as
  `build_profile.py`, `normalize_source.py`, or `render_output.py`.
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
  profiling workflows and profile artifact helpers.
- `intake/packages/`, `intake/archive/`, `intake/file_facts/`, and
  `intake/routing/` are the correct nested packages for the intake subdomains
  that now own their own models, rules, and entry points.
- `intake/plan/` is the correct nested package for intake planning workflows,
  planned-item models, review assembly, and report rendering.
- Normalization window and derived-balance helpers belong under
  `application/normalization/` rather than as nearby flat siblings.
- Output rendering belongs under `application/outputs/`; CoinTracking is one
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
- Keep one stem aligned across the whole family. If the repo chooses
  `CheckpointProposal`, keep that stem in the record family, id fields,
  ref fields, slice contracts, roadmap, and package ownership docs. Do not
  let one target family mix competing stems.
- Follow the same naming approach for modules, functions, classes, and commands:
  choose concise descriptive names over decorative jargon.
- Keep shape and casing aligned by role:
  - concepts use PascalCase nouns such as `BasisPool`
  - stable id helper types use `ThingId`
  - tuple helpers use `ThingRef`
  - kernel families use `ThingRecord`
  - persisted fields and filenames use snake_case such as `thing_id`,
    `thing_ref`, `thing_refs`, and `thing.json`
- Reject verbose pattern-label suffixes such as `UseCase`, `Manager`, or
  `Handler` unless they disambiguate a real collision in the surrounding
  namespace.
- Reserve suffixes precisely:
  - `Ref` for canonical identity tuples or stable pointers
  - `Id` and `*_id` for stable identifiers only
  - `Record` for persisted kernel families
  - `Explanation` for explanatory sidecars keyed to one kernel or support record
  - `Projection` for compatibility outputs or reshaped reader-facing views
  - `Summary` for aggregate rollups over subject or scope truth
  - `Sidecar` for attached non-kernel detail
- Reserve `summary` for aggregate rollups or their ids. Inside explanation or
  review sidecars, prefer concrete prose-field names such as `headline`,
  `known_facts`, or `recommended_follow_up` over `*_summary`.
- Prefer concrete owning nouns over abstract containers. Avoid names such as
  `Core`, `Data`, `Info`, `Context`, `Payload`, or `Item` when `Record`,
  `Explanation`, `Projection`, or the domain noun would say what the surface
  actually holds.
- Avoid abstract boundary labels such as `core` or `main` for forward-looking
  package, product, or concept names when the owning stage, layer, or domain
  boundary is already known. Prefer the explicit owner such as `domain`,
  `reconciliation`, `checkpoint`, `accounting`, or `tax`.
- Keep record-family stems and id stems aligned. Prefer `GapRecord` plus
  `gap_id` or `ReadinessRecord` plus `readiness_id` over longer names that
  repeat context the record family already supplies, unless a real sibling
  family would make the shorter stem ambiguous.
- Apply the same rule to child-local fields, refs, and helper names. When the
  owning product or record already supplies the parent context, prefer the
  shortest truthful child noun such as `selection_id`, `proposal_refs`, or
  `assertion_ids` over longer forms that restate the parent stem.
- Do not shorten a child name when that child must travel outside the owning
  family and the shorter noun would become ambiguous across stages or products.
  Keep the longer owning stem only when that broader ambiguity is real.
- When a record or product owns one primary as-of time, prefer `as_of_at`.
  Add a longer prefix only when the same record carries multiple as-of fields
  or one field is explicitly naming another concept's as-of time.
- When a record owns one obvious child-id or child-ref family, prefer the
  child noun directly, such as `assertion_ids`, `proposal_refs`, or
  `target_refs`, over repeating the full stage or product stem.
- Apply the same rule to one obvious upstream-ref family or review-pair field
  inside a record. Prefer `member_refs`, `observation_refs`, `event_refs`,
  `assertion_refs`, or `gap_ids` over longer forms when the owning record
  already supplies the missing context.
- For stage-owned product-emission identities, prefer `emitter_id` and
  `emitter_key` over the more abstract `producer_id` and `producer_key`.
- When product metadata or a record already supplies the owner, prefer the
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
- For persisted files and workspace basenames, prefer the owning product or
  support role in the filename. Avoid generic names such as `state.json`,
  `data.json`, `output.json`, or `results.json` when later call sites would
  need directory context alone to tell what the file holds.
- In forward-looking docs and code, reserve `artifact` for current-state bridge
  outputs, oracle/reference packages, or intentionally mixed file families.
  When the storage role is known, prefer `kernel`, `sidecar`, `projection`,
  `file`, or `package`.
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
- In canonical target-layer evidence and claim contracts, prefer `source_*`
  or `source_local_*` over `provider_*` unless the field truly preserves an
  adapter-local or compatibility-only provider label.
- When a record owns one primary lifecycle, decision, or resolution field,
  prefer plain `status`, `basis`, or `outcome` over repeating the record stem.
  Add a prefix only when the field describes another concept's status or basis
  rather than the record's own state.
- Prefer `status` over `state` for bounded field vocabularies. Reserve
  `State` for named domain concepts or broader state bundles when `status`
  would underspecify the concept.
- Apply the same status-versus-state rule to named vocabulary concepts.
  Prefer concept names such as `SettlementStatus` when the concept is a
  bounded status family rather than a broader state bundle.
- When a record owns one primary classification, role, or intent field,
  prefer plain `kind`, `role`, `side`, `purpose`, or `measure_kind` over
  repeating the record stem. Add a longer prefix only when the same record
  carries multiple fields of that family or the field describes another
  concept's role or purpose.
- For controlled vocabularies on one record-local kind field, prefer singular
  nouns or noun phrases such as `economic_event`, `adjustment`,
  `carry_forward`, or `unsupported_mapping` unless the value truly names a
  collection artifact rather than one record-local kind.
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
- In kind vocabularies for emitted records, drop redundant suffixes such as
  `schedule`, `report`, or `state` when the record family already tells the
  reader they are looking at an output or emitted state surface.
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
- Inside aggregate summary records, use `rollup_kind` and `rollup_key` for the
  grouping dimensions so `summary` remains the record shape, not a second
  generic field prefix.
- Inside aggregate summary records, drop repeated subject or entity nouns from
  count fields when the summary already establishes that context. Prefer
  `ready_count` over `ready_subject_count`.
- Prefer `Proposal` for stage-owned pre-acceptance records that later become
  accepted truth. Reserve `Candidate` for raw search-space options or other
  unmanaged alternatives that the owning stage has not yet shaped into a
  proposal.
- When a record links or checks another owned concept, include that concept in
  the stem when the shorter noun would be generic across stages. Prefer
  `EventLinkRecord` or `EntryCheckRecord` over ambiguous cross-stage names such
  as `LinkRecord` or `ValidationRecord`.
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
- For compatibility-only material that is not a target concept, name it by
  boundary and role rather than promoting it to a pseudo-domain type.
  Prefer `bridge annotation sidecar detail`, `output annotation sidecar`, or
  `compatibility sidecar` over introducing a new canonical-seeming type name in
  forward-looking docs or code.
- Name the held thing separately from its identity seam or persistence shell:
  `BasisPool` is a concept, `BasisPoolRef` is its ref, and
  `BasisTransitionRecord` is a kernel row family.
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
  `Subject`, or `Transfer` when those are the broader end-state seams.
- Once the pipeline moves past source-local products such as `EvidenceSet` and
  `ClaimSet`, do not keep provider or source-system nouns in later product
  record names, helper refs, stable ids, or partition labels unless those
  nouns are themselves the persisted concept. Prefer lineage-, origin-, or
  subject-owned names over carry-through source labels in downstream kernels.
- When a canonical target contract must preserve a source-provided label,
  preserve the value without freezing the source noun into the field name.
  Prefer target-aligned names such as `location_label` over
  source-specific names such as `wallet_label` when `Location` already owns
  the shared boundary.
- Prefer product-aligned nouns over abstract process jargon when the product
  already owns the boundary. For example, `TaxInputRecord` is clearer than a
  more abstract tax-record noun when the record is the kernel row inside
  `TaxInputs`.
- Do not bake migration qualifiers such as `bridge`, `legacy`, `current`, or
  `compat` into canonical target-layer concepts, helper ids, or product ids
  unless the name is intentionally current-state or adapter-local.
- Under `adapters/sources/`, group packages by source kind before the provider:
  `platforms/<provider>/`, `wallets/<provider>/`, `explorers/<provider>/`,
  `portfolio/<input_kind>/`, `generic/<contract>/`, or `stubs/<reserved>/`.
- Keep naming stable across implementation, tests, adapter metadata, and owner
  docs.
- In prose, prefer the canonical owning noun once a target product or record
  family already exists. Use phrases such as `claim bundle`, `claim scope`,
  `source-local meaning`, and `dataset-level` over looser labels such as
  `semantic bundle`, `semantic scope`, or `whole-dataset` unless the extra
  abstraction is the point.
- Prefer the shortest boundary noun that still distinguishes the seam. When one
  package exists only to host migration compatibility projections,
  `compatibility/` is clearer than `bridge_compatibility/` unless another
  compatibility boundary would make the shorter name ambiguous.

### Five-View Naming And Congruency Audit

Run this audit before freezing or renaming any forward-looking product, record
family, ref, id, package, or file name.

1. Concept view:
   - does the name say what the thing is in end-state domain terms, not just
     when it is used in the workflow
   - would the name still read correctly if the source were not crypto-specific
2. Shape view:
   - does the noun match the held shape exactly: concept, id, ref, record,
     summary, sidecar, projection, file, package, observation kind, or
     controlled-vocabulary value
3. Ownership view:
   - does the name point at the owning stage, layer, or boundary instead of a
     generic cross-stage label
4. Persistence view:
   - do field names, filenames, and package paths make the held truth obvious
     without relying on directory context alone, and do local discriminators
     use keys rather than anchors or other abstract stand-ins
5. Migration view:
   - are bridge, current, legacy, compat, oracle, output, and source-specific
     qualifiers or nouns kept only on intentionally non-canonical surfaces

When one canonical target name changes, update every owner page, bounded-slice
reference, roadmap phase, helper reference, and control-plane routing page that
uses that family in the same patch. Do not leave competing target names alive
in parallel.

## Refactor-First Hotspots

Split these modules before adding materially new behavior:

- `src/tallylot/application/intake/packages/resolution.py`
- `src/tallylot/adapters/sources/platforms/binance/adapter.py`
- `src/tallylot/adapters/sources/platforms/coinbase/adapter.py`

Preserve these shared package boundaries instead of collapsing them back
into single modules:

- `src/tallylot/domain/transactions/`
- `src/tallylot/interfaces/cli/`
- `src/tallylot/infrastructure/discovery/adapters/`
