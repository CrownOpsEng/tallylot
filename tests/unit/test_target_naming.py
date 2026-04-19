from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from repo_support.paths import override_repo_root
from repo_support.target_naming import (
    NamingFinding,
    audit_target_naming,
    is_target_naming_sensitive_path,
    load_target_naming_catalog,
)


def _write_catalog(
    root: Path,
    *,
    overlap_axes: bool = False,
    local_id_slots: Sequence[Mapping[str, object]] = (),
    identifier_context_rules: Sequence[Mapping[str, object]] = (),
    extra_title_expectations: Mapping[str, str] | None = None,
) -> None:
    catalog: dict[str, object] = {
        "version": 2,
        "root_file_scopes": {},
        "scope_profiles": {
            "forward_target": {
                "enforce_target_naming": True,
                "allow_anti_examples": False,
            },
            "repo_policy": {
                "enforce_target_naming": True,
                "allow_anti_examples": True,
            },
            "current_state": {
                "enforce_target_naming": False,
                "allow_anti_examples": False,
            },
            "bridge_local": {
                "enforce_target_naming": False,
                "allow_anti_examples": False,
            },
            "oracle_local": {
                "enforce_target_naming": False,
                "allow_anti_examples": False,
            },
            "adapter_local": {
                "enforce_target_naming": False,
                "allow_anti_examples": False,
            },
            "workspace_reference": {
                "enforce_target_naming": False,
                "allow_anti_examples": False,
            },
        },
        "title_expectations": {
            "docs/example.md": "Example",
            "docs/matrix.md": "Matrix",
            **(extra_title_expectations or {}),
        },
        "tooling_paths": [],
        "canonical_families": {
            "products": [
                {"name": "EvidenceSet", "id": "evidence_set_id"},
                {"name": "ClaimSet", "id": "claim_set_id"},
            ],
            "records": [
                {"stem": "gap", "record": "GapRecord", "id": "gap_id", "refs": []},
                {
                    "stem": "review",
                    "record": "ReviewRecord",
                    "id": "review_id",
                    "refs": [],
                },
            ],
            "package_paths": ["application/claim/", "domain/assessment/"],
            "standalone_directory_paths": ["compatibility/"],
            "directory_families": [
                {
                    "root": "assessment",
                    "families": [
                        {
                            "stem": "gap",
                            "sidecars": ["gap_records.json", "gap_explanations.json"],
                        },
                        {
                            "stem": "review",
                            "sidecars": [
                                "review_records.json",
                                "review_explanations.json",
                            ],
                        },
                    ],
                },
                {
                    "root": "working/products",
                    "families": [
                        {"stem": "evidence_sets"},
                        {"stem": "claim_sets"},
                    ],
                },
            ],
        },
        "canonical_tokens": {
            "pascal": [],
            "snake": [
                "balance_target_id",
                "checkpoint_assertion_id",
                "checkpoint_id",
                "checkpoint_proposal_id",
                "claim_bundle_decision_id",
                "claim_bundle_id",
                "claim_scope_id",
                "emitter_id",
                "entry_check_id",
                "entry_id",
                "event_id",
                "member_id",
                "observation_id",
                "selection_id",
            ],
            "phrases": [],
        },
        "local_id_slots": list(local_id_slots),
        "identifier_context_rules": list(identifier_context_rules),
        "vocabularies": {
            "values": {
                "basis": ["document_support", "manual_support"],
                "support_shape": (
                    ["document_support", "manual_assertion"]
                    if overlap_axes
                    else ["document_observation", "manual_assertion"]
                ),
                "continuity_kind": ["observed_continuity"],
            },
            "paired_axes": [["basis", "support_shape", "continuity_kind"]],
            "checks": [
                {
                    "path": "docs/example.md",
                    "vocabulary": "basis",
                    "label": "basis",
                    "block_type": "nested_list",
                    "expected_values": [],
                }
            ],
        },
        "banned_phrases": [
            {
                "rule_id": "summary.content_first",
                "term": "Owning concept page",
                "contexts": ["summary"],
                "allowed_scopes": ["forward_target", "repo_policy"],
                "paths": [],
            },
            {
                "rule_id": "body.no_slice_role_jargon",
                "term": "bounded contract",
                "contexts": ["body"],
                "allowed_scopes": ["forward_target"],
                "paths": [],
            },
        ],
        "retired_aliases": [
            {
                "rule_id": "body.compatibility_view_term",
                "term": "compatibility projection",
                "replacement": "compatibility view",
                "contexts": ["body", "inline_code", "summary"],
                "allowed_scopes": ["forward_target", "repo_policy"],
                "paths": [],
                "allowed_paths": [],
            }
        ],
        "exceptions": [
            {
                "exception_id": "locality.bridge_fields",
                "allowed_scopes": ["forward_target", "repo_policy"],
                "allowed_paths": ["docs/example.md"],
                "allowed_section_labels": [],
                "allowed_terms": ["activity_label"],
                "required_marker": "Locality rule",
                "required_rationale": True,
                "notes": "Bridge-local field names must stay explicitly labeled.",
            },
            {
                "exception_id": "locality.instrument_kind",
                "allowed_scopes": ["forward_target", "repo_policy"],
                "allowed_paths": ["docs/example.md"],
                "allowed_section_labels": ["InstrumentKind"],
                "allowed_terms": ["crypto"],
                "required_rationale": False,
                "notes": "Bounded instrument vocabulary may keep crypto in its own section.",
            },
        ],
        "required_markers": [
            "Slice-only example",
            "Compatibility-only locality",
            "Current runtime note",
            "Anti-example",
            "Exception rationale",
            "Migration-only root rationale",
            "Locality rule",
        ],
    }
    target_path = root / "tools" / "target_naming_catalog.yaml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


def _write_doc(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _local_slot(canonical_id: str, slot: str) -> dict[str, object]:
    return {"canonical_id": canonical_id, "slot": slot}


def _identifier_context_rule(
    *,
    surface_kind: str,
    canonical_ids: Sequence[str],
    path: str = "docs/example.md",
    section_path: Sequence[str] = ("ClaimSet",),
    region_label: str = "Record families",
    mode: str = "local_short",
) -> dict[str, object]:
    return {
        "path": path,
        "section_path": list(section_path),
        "region_label": region_label,
        "surface_kind": surface_kind,
        "mode": mode,
        "canonical_ids": list(canonical_ids),
    }


def _audit_example_doc(
    tmp_path: Path,
    *,
    body: str,
    scope: str = "forward_target",
    local_id_slots: Sequence[Mapping[str, object]] = (),
    identifier_context_rules: Sequence[Mapping[str, object]] = (),
) -> tuple[NamingFinding, ...]:
    _write_catalog(
        tmp_path,
        local_id_slots=local_id_slots,
        identifier_context_rules=identifier_context_rules,
    )
    _write_doc(
        tmp_path,
        "docs/example.md",
        "\n".join(
            [
                "---",
                'title: "Example"',
                'summary: "Clean summary."',
                "doc_type: concept",
                "audience: human",
                "owner: repo",
                "status: active",
                f"naming_scope: {scope}",
                "---",
                "",
                dedent(body).strip(),
                "",
                "- `basis`:",
                "  - `document_support`",
                "  - `manual_support`",
                "",
            ]
        ),
    )

    with override_repo_root(tmp_path):
        return audit_target_naming(paths=("docs/example.md",))


def test_catalog_validation_rejects_paired_axis_overlap(tmp_path: Path) -> None:
    _write_catalog(tmp_path, overlap_axes=True)

    with (
        override_repo_root(tmp_path),
        pytest.raises(ValueError, match="paired-axis overlap"),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_directory_sidecar_family_drift(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    target_path = tmp_path / "tools" / "target_naming_catalog.yaml"
    loaded = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    canonical_families = loaded["canonical_families"]
    canonical_families["directory_families"] = [
        {
            "root": "assessment",
            "families": [
                {
                    "stem": "gap",
                    "sidecars": ["review_records.json"],
                }
            ],
        },
        {
            "root": "working/products",
            "families": [
                {"stem": "evidence_sets"},
                {"stem": "claim_sets"},
            ],
        },
    ]
    target_path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")

    with (
        override_repo_root(tmp_path),
        pytest.raises(ValueError, match="directory family sidecar must stay grouped"),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_unknown_record_directory_family_stem(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    target_path = tmp_path / "tools" / "target_naming_catalog.yaml"
    loaded = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    directory_families = loaded["canonical_families"]["directory_families"]
    directory_families[0]["families"][0] = {
        "stem": "analysis",
        "sidecars": ["analysis_records.json"],
    }
    target_path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="directory family stem must name a canonical record",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_product_directory_family_drift(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    target_path = tmp_path / "tools" / "target_naming_catalog.yaml"
    loaded = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    directory_families = loaded["canonical_families"]["directory_families"]
    directory_families[1]["families"][0]["stem"] = "evidence_groupings"
    target_path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match=(
                "working/products directory families must cover every canonical "
                "product stem"
            ),
        ),
    ):
        load_target_naming_catalog()


def test_catalog_loads_valid_local_id_slots(tmp_path: Path) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
    )

    with override_repo_root(tmp_path):
        catalog = load_target_naming_catalog()

    assert catalog.local_id_slots[0].canonical_id == "claim_scope_id"
    assert catalog.local_id_slots[0].slot == "scope_id"


def test_catalog_validation_rejects_duplicate_local_id_slot(tmp_path: Path) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[
            _local_slot("claim_scope_id", "scope_id"),
            _local_slot("claim_bundle_id", "scope_id"),
        ],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(ValueError, match="duplicate local id slot"),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_duplicate_canonical_slot_mapping(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[
            _local_slot("claim_scope_id", "scope_id"),
            _local_slot("claim_scope_id", "scope_alias_id"),
        ],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="canonical stable id must map to at most one local slot",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_local_slot_equal_to_canonical_id(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "claim_scope_id")],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="local id slot must differ from canonical stable id",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_local_slot_reusing_canonical_token(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "member_id")],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="local id slot must not reuse a canonical stable id token",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_identifier_context_unknown_canonical_id(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="field_slot",
                canonical_ids=("checkpoint_assertion_id",),
            )
        ],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="identifier context rule references undeclared canonical id",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_invalid_identifier_namespace_mode(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="field_slot",
                canonical_ids=("claim_scope_id",),
                mode="localish",
            )
        ],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="unsupported identifier namespace mode",
        ),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_invalid_identifier_surface_kind(
    tmp_path: Path,
) -> None:
    _write_catalog(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="field_name",
                canonical_ids=("claim_scope_id",),
            )
        ],
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(
            ValueError,
            match="unsupported identifier surface kind",
        ),
    ):
        load_target_naming_catalog()


def test_audit_finds_phrase_alias_vocabulary_locality_and_structure_drift(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            - `basis`:
              - `document_support`
              - `manual_assertion`

            This bounded contract still relies on compatibility projection,
            bridge-local `activity_label`, `application/non_canonical/`,
            and `support/other/detail.json`.
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert {finding.rule_id for finding in findings} == {
        "body.compatibility_view_term",
        "body.no_slice_role_jargon",
        "family.path.canonical",
        "locality.field.exception_restatement",
        "structure.flat_support_path",
        "vocab.axis.basis",
    }


def test_audit_allows_marked_locality_exception(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            ## Bridge Fields

            **Locality rule:** Retain `activity_label` only for this bridge-local
            compatibility note.

            Later prose may restate `activity_label` inside the same governed section.

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert not findings


def test_audit_allows_unmarked_allowed_section_locality_term(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            ### InstrumentKind

            Shared vocabulary:

            - `crypto`

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert not findings


def test_audit_does_not_own_missing_naming_scope_for_repo_docs(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            ---

            Example body.
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert not findings


def test_audit_reports_capitalized_retired_alias_in_body(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            This page still uses Compatibility projection.

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert [finding.rule_id for finding in findings] == ["body.compatibility_view_term"]


def test_audit_reports_capitalized_retired_alias_in_summary(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Compatibility projection remains in the summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert [finding.rule_id for finding in findings] == ["body.compatibility_view_term"]


def test_audit_reports_transient_process_term_in_summary(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    target_path = tmp_path / "tools" / "target_naming_catalog.yaml"
    loaded = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    loaded["banned_phrases"].append(
        {
            "rule_id": "body.no_transient_process_term",
            "term": "implementation plan",
            "contexts": ["body", "summary"],
            "allowed_scopes": ["forward_target"],
            "paths": [],
        }
    )
    target_path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Implementation plan summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert [finding.rule_id for finding in findings] == [
        "body.no_transient_process_term"
    ]


def test_audit_reports_stepwise_handoff_label_in_body(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    target_path = tmp_path / "tools" / "target_naming_catalog.yaml"
    loaded = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    loaded["banned_phrases"].append(
        {
            "rule_id": "body.no_stepwise_handoff_label",
            "term": "step 1",
            "contexts": ["body"],
            "allowed_scopes": ["forward_target"],
            "paths": [],
        }
    )
    target_path.write_text(yaml.safe_dump(loaded, sort_keys=False), encoding="utf-8")
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            Step 1: hand the work to a later pass.

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert [finding.rule_id for finding in findings] == [
        "body.no_stepwise_handoff_label"
    ]


def test_audit_reports_title_drift(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Wrong"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert [finding.rule_id for finding in findings] == ["title.canonical"]


def test_locality_rule_ignores_terms_without_applicable_scope_rule(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/standards.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: standard
            audience: human
            owner: repo
            status: active
            naming_scope: repo_policy
            ---

            Paragraph with wallet wording.

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/standards.md",))

    assert not findings


def test_audit_checks_locality_exceptions_inside_table_cells(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            | Field |
            | --- |
            | `activity_label` |

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert [finding.rule_id for finding in findings] == [
        "locality.field.exception_restatement"
    ]


def test_audit_reports_legacy_support_root_once(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            `support/gap/gap_records.json`

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/example.md",))

    assert [finding.rule_id for finding in findings] == ["structure.flat_support_path"]


def test_audit_checks_family_paths_in_repo_policy_docs(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/standards.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: standard
            audience: human
            owner: repo
            status: active
            naming_scope: repo_policy
            ---

            `application/non_canonical/`

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/standards.md",))

    assert [finding.rule_id for finding in findings] == ["family.path.canonical"]


def test_audit_checks_catalog_declared_standalone_directory_paths(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/standards.md",
        dedent(
            """\
            ---
            title: "Example"
            summary: "Clean summary."
            doc_type: standard
            audience: human
            owner: repo
            status: active
            naming_scope: repo_policy
            ---

            `compatibility/non_canonical/`

            - `basis`:
              - `document_support`
              - `manual_support`
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/standards.md",))

    assert [finding.rule_id for finding in findings] == ["family.path.canonical"]


def test_audit_does_not_own_docs_home_reference_group_drift(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/README.md",
        dedent(
            """\
            ---
            title: "Docs"
            summary: "Clean summary."
            doc_type: reference
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            ### Target References

            - Example

            ### Current-State And Oracle References

            - Example
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/README.md",))

    assert not findings


def test_audit_does_not_own_bridge_cutover_matrix_semantics(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/matrix.md",
        dedent(
            """\
            ---
            title: "Matrix"
            summary: "Clean summary."
            doc_type: concept
            audience: human
            owner: repo
            status: active
            naming_scope: forward_target
            ---

            | Current bridge surface | Target authoritative product(s) | Derived compatibility view | Derived compatibility sidecar | Current readers | Target readers after cutover | Cutover gate | Retirement gate |
            | --- | --- | --- | --- | --- | --- | --- | --- |
            | translation_input_plan.json | `EvidenceSet` | compatibility projection | none | future reader | claim construction | deterministic output | reader retired |
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming(paths=("docs/matrix.md",))

    assert not findings


def test_identifier_namespace_requires_canonical_ids_by_default(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        scope="repo_policy",
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        body="""
        ## Naming Rules

        - `scope_id`
        """,
    )

    assert [finding.rule_id for finding in findings] == [
        "identifier.namespace.canonical_required"
    ]


def test_identifier_namespace_allows_canonical_ids_by_default(tmp_path: Path) -> None:
    findings = _audit_example_doc(
        tmp_path,
        scope="repo_policy",
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        body="""
        ## Naming Rules

        - `claim_scope_id`
        """,
    )

    assert not findings


def test_identifier_namespace_requires_local_short_field_slots(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="field_slot",
                canonical_ids=("claim_scope_id",),
            )
        ],
        body="""
        ## ClaimSet

        Record families:

        - `claim_scope_id`
        """,
    )

    assert [finding.rule_id for finding in findings] == [
        "identifier.namespace.local_short_required"
    ]


def test_identifier_namespace_allows_local_short_field_slots(tmp_path: Path) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="field_slot",
                canonical_ids=("claim_scope_id",),
            )
        ],
        body="""
        ## ClaimSet

        Record families:

        - `scope_id`
        """,
    )

    assert not findings


def test_identifier_namespace_requires_local_short_array_components(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="array_component",
                canonical_ids=("claim_scope_id",),
                region_label="Stable ids",
            )
        ],
        body="""
        ## ClaimSet

        Stable ids:

        - `[claim_scope_id, key]`
        """,
    )

    assert [finding.rule_id for finding in findings] == [
        "identifier.namespace.local_short_required"
    ]


def test_identifier_namespace_allows_local_short_array_components(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="array_component",
                canonical_ids=("claim_scope_id",),
                region_label="Stable ids",
            )
        ],
        body="""
        ## ClaimSet

        Stable ids:

        - `[scope_id, key]`
        """,
    )

    assert not findings


def test_identifier_namespace_mixes_canonical_and_local_short_regions(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="array_component",
                canonical_ids=("claim_scope_id",),
                region_label="Stable ids",
            )
        ],
        body="""
        ## ClaimSet

        Stable ids:

        - `[scope_id, key]`

        Cardinality:

        - `scope_id`
        """,
    )

    assert [finding.rule_id for finding in findings] == [
        "identifier.namespace.canonical_required"
    ]


def test_identifier_namespace_ignores_canonical_ids_without_local_slots(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("claim_scope_id", "scope_id")],
        body="""
        ## Naming Rules

        - `member_id`
        - `selection_id`
        - `event_id`
        - `entry_id`
        - `emitter_id`
        """,
    )

    assert not findings


def test_identifier_namespace_checks_qualified_field_suffixes(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("checkpoint_assertion_id", "assertion_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="qualified_field_suffix",
                canonical_ids=("checkpoint_assertion_id",),
                section_path=("Checkpoint",),
            )
        ],
        body="""
        ## Checkpoint

        Record families:

        - `CheckpointAssertionRecord.checkpoint_assertion_id`
        """,
    )

    assert [finding.rule_id for finding in findings] == [
        "identifier.namespace.local_short_required"
    ]


def test_identifier_namespace_allows_local_short_qualified_field_suffixes(
    tmp_path: Path,
) -> None:
    findings = _audit_example_doc(
        tmp_path,
        local_id_slots=[_local_slot("checkpoint_assertion_id", "assertion_id")],
        identifier_context_rules=[
            _identifier_context_rule(
                surface_kind="qualified_field_suffix",
                canonical_ids=("checkpoint_assertion_id",),
                section_path=("Checkpoint",),
            )
        ],
        body="""
        ## Checkpoint

        Record families:

        - `CheckpointAssertionRecord.assertion_id`
        """,
    )

    assert not findings


def test_real_repo_catalog_loads_core_family_and_identifier_data() -> None:
    catalog = load_target_naming_catalog()

    assert catalog.canonical_families.directory_paths == (
        "compatibility/",
        "assessment/gap/",
        "assessment/review/",
        "working/products/evidence_sets/",
        "working/products/claim_sets/",
        "working/products/economic_facts/",
        "working/products/reconciliation_states/",
        "working/products/checkpoints/",
        "working/products/journals/",
        "working/products/tax_inputs/",
        "working/products/tax_outputs/",
    )
    assert catalog.canonical_families.sidecar_paths == (
        "assessment/gap/gap_records.json",
        "assessment/gap/gap_explanations.json",
        "assessment/review/review_records.json",
        "assessment/review/review_explanations.json",
    )
    assert catalog.local_id_slot_by_canonical_id == {
        "claim_scope_id": "scope_id",
        "claim_bundle_id": "bundle_id",
        "claim_bundle_decision_id": "decision_id",
        "continuity_segment_id": "segment_id",
        "balance_target_id": "target_id",
        "checkpoint_proposal_id": "proposal_id",
        "checkpoint_assertion_id": "assertion_id",
        "entry_check_id": "check_id",
    }
    assert (
        catalog.identifier_context_rules[0].path
        == "docs/concepts/pipeline-stage-contracts.md"
    )
    record_names = {record.record for record in catalog.canonical_families.records}
    assert "EvidenceObservationRecord" in record_names
    assert "ClaimBundleRecord" in record_names
    assert "ValuationRecord" in record_names
    assert "JournalEntryRecord" in record_names
    assert "GapRecord" in record_names
    assert "ReadinessRecord" not in record_names
    assert "ReadinessRollupRecord" not in record_names
    assert "application/assessment/" not in catalog.canonical_families.package_paths
    assert "application/reporting/" not in catalog.canonical_families.package_paths
    assert "application/portfolio/" not in catalog.canonical_families.package_paths
    assert "application/visualization/" not in catalog.canonical_families.package_paths
    assert "application/investigation/" not in catalog.canonical_families.package_paths
    assert "assessment view" not in catalog.canonical_tokens.phrases
    assert "readiness rollup" not in catalog.canonical_tokens.phrases
    assert "readiness_rollup_id" not in catalog.canonical_tokens.snake
    retired_aliases = {
        alias.term: alias.replacement for alias in catalog.retired_aliases
    }
    banned_terms = {phrase.term for phrase in catalog.banned_phrases}
    assert retired_aliases["application/readiness/"] == "owning application slice"
    assert retired_aliases["application/assessment/"] == "owning application slice"
    assert (
        retired_aliases["application/query/"]
        == "specific capability-owned derived read-model package"
    )
    assert (
        retired_aliases["application/read_models/"]
        == "specific capability-owned derived read-model package"
    )
    assert retired_aliases["operator view"] == "derived view"
    assert retired_aliases["operator views"] == "derived views"
    assert "implementation plan" in banned_terms
    assert "step 1" in banned_terms
    assert "tools/target_naming.py" in catalog.tooling_paths
    assert "tests/unit/test_target_naming_parser.py" in catalog.tooling_paths


def test_target_naming_sensitive_path_helper_covers_docs_and_control_plane() -> None:
    assert (
        is_target_naming_sensitive_path("docs/concepts/pipeline-stage-contracts.md")
        is True
    )
    assert is_target_naming_sensitive_path("docs/README.md") is True
    assert is_target_naming_sensitive_path("docs/standards/engineering.md") is True
    assert is_target_naming_sensitive_path("AGENTS.md") is True
    assert is_target_naming_sensitive_path("tools/target_naming_catalog.yaml") is True
    assert (
        is_target_naming_sensitive_path("docs/concepts/transaction-classification.md")
        is False
    )
    assert is_target_naming_sensitive_path("docs/guides/source-intake.md") is False
