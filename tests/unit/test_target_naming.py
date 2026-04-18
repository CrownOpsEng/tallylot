from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from repo_support.paths import override_repo_root
from repo_support.target_naming import (
    audit_target_naming,
    is_target_naming_sensitive_path,
    load_target_naming_catalog,
)


def _write_catalog(root: Path, *, overlap_axes: bool = False) -> None:
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
        },
        "reference_group_headings": [
            "### Target References",
            "### Current-State References",
            "### Oracle References",
        ],
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
                {
                    "stem": "readiness",
                    "record": "ReadinessRecord",
                    "id": "readiness_id",
                    "refs": [],
                },
                {
                    "stem": "readiness_rollup",
                    "record": "ReadinessRollupRecord",
                    "id": "readiness_rollup_id",
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
                        {
                            "stem": "readiness",
                            "sidecars": [
                                "readiness_records.json",
                                "readiness_rollup_records.json",
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
            "snake": [],
            "phrases": [],
        },
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
        "matrix_specs": [
            {
                "path": "docs/matrix.md",
                "required_columns": [
                    "Current bridge surface",
                    "Target authoritative product(s)",
                    "Derived compatibility view",
                    "Derived compatibility sidecar",
                    "Current readers",
                    "Target readers after cutover",
                    "Cutover gate",
                    "Retirement gate",
                ],
                "allowed_shape_nouns": [
                    "compatibility view",
                    "compatibility sidecar",
                    "none",
                ],
                "banned_fragments": ["view or sidecar"],
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

    assert findings == ()


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

    assert findings == ()


def test_audit_reports_missing_naming_scope_for_repo_docs(tmp_path: Path) -> None:
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

    assert [finding.rule_id for finding in findings] == [
        "structure.missing_naming_scope"
    ]


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

    assert findings == ()


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


def test_audit_reports_docs_home_reference_group_drift(tmp_path: Path) -> None:
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

    assert {finding.rule_id for finding in findings} == {"docs_home.reference_groups"}


def test_real_repo_catalog_covers_root_scopes_and_tooling_paths() -> None:
    catalog = load_target_naming_catalog()

    assert catalog.root_file_scopes == {
        "ROADMAP.md": "forward_target",
        "AGENTS.md": "repo_policy",
        "CHANGELOG.md": "repo_policy",
    }
    assert catalog.scope_profiles["forward_target"].enforce_target_naming is True
    assert catalog.scope_profiles["repo_policy"].allow_anti_examples is True
    assert (
        catalog.title_expectations["docs/concepts/gaps-and-readiness.md"]
        == "Gap, Review, And Readiness"
    )
    assert (
        catalog.title_expectations["docs/concepts/reconciliation-tax-architecture.md"]
        == "Reconciliation, Checkpoint, Journal, And Tax Architecture"
    )
    assert catalog.canonical_families.directory_paths == (
        "compatibility/",
        "assessment/gap/",
        "assessment/review/",
        "assessment/readiness/",
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
        "assessment/readiness/readiness_records.json",
        "assessment/readiness/readiness_rollup_records.json",
    )
    assert catalog.reference_group_headings == (
        "### Target References",
        "### Current-State References",
        "### Oracle References",
    )
    record_names = {record.record for record in catalog.canonical_families.records}
    assert "EvidenceObservationRecord" in record_names
    assert "ClaimBundleRecord" in record_names
    assert "ValuationRecord" in record_names
    assert "JournalEntryRecord" in record_names
    assert "GapRecord" in record_names
    assert "tools/target_naming.py" in catalog.tooling_paths
    assert "tests/unit/test_target_naming_parser.py" in catalog.tooling_paths


def test_target_naming_sensitive_path_helper_covers_docs_and_control_plane() -> None:
    assert (
        is_target_naming_sensitive_path("docs/concepts/pipeline-stage-contracts.md")
        is True
    )
    assert is_target_naming_sensitive_path("docs/standards/engineering.md") is True
    assert is_target_naming_sensitive_path("AGENTS.md") is True
    assert is_target_naming_sensitive_path("tools/target_naming_catalog.yaml") is True
    assert is_target_naming_sensitive_path("docs/guides/source-intake.md") is False
