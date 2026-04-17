from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from repo_support.paths import override_repo_root
from repo_support.target_naming import (
    audit_target_naming,
    is_target_naming_sensitive_path,
    load_target_naming_catalog,
)


def _write_catalog(
    root: Path,
    *,
    include_paths: list[str] | None = None,
    include_prefixes: list[str] | None = None,
    exclude_paths: list[str] | None = None,
    overlap_axes: bool = False,
) -> None:
    catalog: dict[str, object] = {
        "version": 1,
        "surfaces": {
            "include": {
                "paths": include_paths or ["docs/example.md"],
                "prefixes": include_prefixes or [],
            },
            "exclude": {"paths": exclude_paths or [], "prefixes": []},
        },
        "families": {
            "products": [{"name": "Checkpoint", "id": "checkpoint_id"}],
            "records": [
                {
                    "stem": "checkpoint_proposal",
                    "record": "CheckpointProposalRecord",
                    "id": "checkpoint_proposal_id",
                    "refs": ["superseding_proposal_ref"],
                    "required_in": ["docs/example.md"],
                }
            ],
            "paths": {
                "package_stems": ["application/checkpoint/"],
                "directory_stems": ["working/products/checkpoints/"],
                "sidecar_paths": ["support/gap/gap_records.json"],
            },
            "vocabularies": {
                "values": {
                    "basis": ["document_support", "manual_support"],
                    "support_shape": (
                        ["document_support", "manual_assertion"]
                        if overlap_axes
                        else ["document_observation", "manual_assertion"]
                    ),
                    "continuity_kind": [
                        "observed_continuity",
                        "reconciled_rollforward",
                    ],
                    "balance_target_observation_status": [
                        "observed",
                        "unobserved",
                    ],
                    "balance_target_comparison_outcome": [
                        "matched",
                        "mismatched",
                    ],
                    "journal_entry_status": [
                        "expanded",
                        "blocked",
                    ],
                    "entry_check_status": [
                        "passed",
                        "blocked",
                    ],
                    "tax_output_status": [
                        "ready",
                        "partial",
                    ],
                    "checkpoint_proposal_status": [
                        "ready",
                        "partial",
                        "blocked",
                    ],
                    "valuation_purpose": [
                        "economic_measurement",
                        "market_measurement",
                    ],
                    "origin_kind": [
                        "claim",
                        "market_reference",
                    ],
                },
                "paired_axes": [["basis", "support_shape", "continuity_kind"]],
                "checks": [
                    {
                        "path": "docs/example.md",
                        "vocabulary": "basis",
                        "label": "basis",
                        "block_type": "nested_list",
                    }
                ],
            },
        },
        "phrases": {"canonical": ["compatibility view", "entry check"]},
        "aliases": {
            "banned": [
                {
                    "term": "compatibility projection",
                    "replacement": "compatibility view",
                    "finding_class": "banned-alias",
                    "summary_only": False,
                    "paths": [],
                    "path_prefixes": [],
                }
            ]
        },
        "exceptions": [
            {
                "name": "bridge-local",
                "paths": ["docs/example.md"],
                "path_prefixes": [],
                "allowed_terms": ["activity_label"],
            }
        ],
    }
    target_path = root / "tools" / "target_naming_catalog.yaml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


def _write_doc(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_catalog_validation_rejects_surface_overlap(tmp_path: Path) -> None:
    _write_catalog(tmp_path, exclude_paths=["docs/example.md"])
    _write_doc(
        tmp_path,
        "docs/example.md",
        '---\ntitle: "Example"\nsummary: "Clean summary."\ndoc_type: concept\naudience: human\nowner: repo\nstatus: active\n---\n',
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(ValueError, match="surface include/exclude overlap"),
    ):
        load_target_naming_catalog()


def test_catalog_validation_rejects_paired_axis_overlap(tmp_path: Path) -> None:
    _write_catalog(tmp_path, overlap_axes=True)
    _write_doc(
        tmp_path,
        "docs/example.md",
        '---\ntitle: "Example"\nsummary: "Clean summary."\ndoc_type: concept\naudience: human\nowner: repo\nstatus: active\n---\n',
    )

    with (
        override_repo_root(tmp_path),
        pytest.raises(ValueError, match="paired-axis overlap"),
    ):
        load_target_naming_catalog()


def test_audit_finds_banned_alias_unknown_identifier_family_mismatch_and_flat_support_path(
    tmp_path: Path,
) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        """---
title: "Example"
summary: "Clean summary."
doc_type: concept
audience: human
owner: repo
status: active
---

- `basis`:
  - `document_support`
  - `manual_support`

Use `compatibility projection`, `CheckpointProposalRecord`, `unknown_id`, and `support/gap_records.json`.
""",
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert {finding.finding_class for finding in findings} == {
        "banned-alias",
        "unknown-target-identifier",
        "record-family-mismatch",
        "flat-support-path",
    }


def test_audit_allows_path_scoped_exception(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        """---
title: "Example"
summary: "Clean summary."
doc_type: concept
audience: human
owner: repo
status: active
---

- `basis`:
  - `document_support`
  - `manual_support`

Allowed exception: `activity_label`.
""",
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert findings == ()


def test_audit_finds_vocabulary_drift(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    _write_doc(
        tmp_path,
        "docs/example.md",
        """---
title: "Example"
summary: "Clean summary."
doc_type: concept
audience: human
owner: repo
status: active
---

- `basis`:
  - `document_support`
  - `manual_assertion`
""",
    )

    with override_repo_root(tmp_path):
        findings = audit_target_naming()

    assert [finding.finding_class for finding in findings] == ["vocabulary-drift"]


def test_real_repo_catalog_covers_expected_surfaces() -> None:
    catalog = load_target_naming_catalog()

    assert catalog.surfaces.include.paths == (
        "ROADMAP.md",
        "docs/README.md",
        "docs/standards/engineering.md",
        "docs/concepts/architecture-overview.md",
        "docs/concepts/bridge-to-target-mapping.md",
        "docs/concepts/domain-ontology.md",
        "docs/concepts/gaps-and-readiness.md",
        "docs/concepts/oracle-boundaries.md",
        "docs/concepts/pipeline-stage-contracts.md",
        "docs/concepts/reconciliation-tax-architecture.md",
        "docs/concepts/unified-adapter-architecture.md",
        "docs/reference/first-upstream-slice-contract.md",
        "docs/reference/first-downstream-slice-contract.md",
        "docs/reference/target-ids-and-refs.md",
        "docs/reference/target-persistence-reference.md",
        "docs/status/migration-sequence.md",
        "docs/status/adapter-delivery-plan.md",
    )
    assert catalog.surfaces.exclude.paths == (
        "docs/status/current-state.md",
        "docs/concepts/current-bridge-contracts.md",
        "docs/reference/baseline-validation-contract.md",
        "docs/reference/canadian-crypto-tax-guide.md",
        "docs/reference/cointracking-oracle-artifacts.md",
        "docs/reference/export-checklist.md",
        "docs/reference/location-inventory-artifacts.md",
        "docs/reference/manual-balance-submission-artifacts.md",
        "docs/reference/repository-history.md",
        "docs/reference/tax-source-map.md",
        "docs/reference/timezone-validation-artifacts.md",
    )
    assert catalog.surfaces.exclude.prefixes == ("docs/workspace/",)


def test_target_naming_sensitive_path_helper_covers_docs_and_control_plane() -> None:
    assert (
        is_target_naming_sensitive_path("docs/concepts/pipeline-stage-contracts.md")
        is True
    )
    assert is_target_naming_sensitive_path("tools/target_naming_catalog.yaml") is True
    assert is_target_naming_sensitive_path("docs/guides/source-intake.md") is False
