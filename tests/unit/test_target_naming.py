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
        "tooling_paths": [],
        "canonical_families": {
            "products": [],
            "records": [],
            "package_paths": [],
            "directory_paths": [],
            "sidecar_paths": [],
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
                    "Target authoritative product",
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
            }
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
            bridge-local `activity_label`, and `support/other/detail.json`.
            """
        ),
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert {finding.rule_id for finding in findings} == {
        "body.compatibility_view_term",
        "body.no_slice_role_jargon",
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


def test_real_repo_catalog_covers_root_scopes_and_tooling_paths() -> None:
    catalog = load_target_naming_catalog()

    assert catalog.root_file_scopes == {
        "ROADMAP.md": "forward_target",
        "AGENTS.md": "repo_policy",
        "CHANGELOG.md": "repo_policy",
    }
    assert catalog.scope_profiles["forward_target"].enforce_target_naming is True
    assert catalog.scope_profiles["repo_policy"].allow_anti_examples is True
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
