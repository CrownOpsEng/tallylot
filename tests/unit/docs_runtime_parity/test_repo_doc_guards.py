from __future__ import annotations

from tallylot.infrastructure.workspace.layout import SEED_FILES

from tests.support.docs_runtime_parity import (
    adapter_packs_root,
    agents_root,
    architecture_doc_paths,
    docs_root,
    repo_root,
)


def test_docs_do_not_reference_retired_service_or_model_buckets() -> None:
    forbidden = (
        "application/services",
        "application/models",
        "domain/models",
        "source diff",
        "baseline validate",
        "verification compare",
        "batch stage",
        "batch screen",
        "round scaffold",
        "supporting extract-pdf-balances",
        "wallet inventory rebuild",
    )
    for path in architecture_doc_paths():
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references retired surface {needle!r}"
            )


def test_docs_use_lowercase_filenames_except_readmes() -> None:
    for path in sorted(docs_root().rglob("*")):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        assert path.name == path.name.lower(), f"doc filename is not lowercase: {path}"


def test_repo_docs_do_not_reference_personal_workspace_roots() -> None:
    forbidden = (
        "/home/user/",
        "Documents/",
        "~/Documents/",
    )
    paths = (
        repo_root() / "README.md",
        repo_root() / "AGENTS.md",
        repo_root() / "tallylot.toml",
        *sorted(docs_root().rglob("*.md")),
        *sorted(agents_root().rglob("*.md")),
        *sorted((repo_root() / ".claude").rglob("*.md")),
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references personal workspace path {needle}"
            )


def test_private_oracle_manifest_is_not_checked_in() -> None:
    assert not (
        docs_root() / "reference" / "cointracking-full-export-manifest.csv"
    ).exists()


def test_workspace_issue_log_seed_header_matches_template() -> None:
    template_header = (
        (docs_root() / "workspace" / "analysis" / "issues" / "issue-log-template.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/issue_log.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_inventory_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-inventory-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_inventory.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_captures_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "inventory"
            / "source-captures-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/inventory/source_captures.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_label_map_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-label-map-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_label_map.csv"
    )

    assert seeded_header == template_header


def test_commit_standards_require_explicit_lint_amend_reverification() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")

    assert "Do not describe `mypy` or `pyright` as covering `pylint` findings." in text
    assert "make pylint ARGS='<touched-file>'" in text
    assert "make pytest ARGS='-q --no-cov <touched-test-file>'" in text
    assert "git show HEAD:<path>" in text


def test_commit_standards_document_hybrid_pr_merge_policy() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")
    implementation_text = (docs_root() / "standards" / "implementation.md").read_text(
        encoding="utf-8"
    )
    pr_template = (repo_root() / ".github" / "pull_request_template.md").read_text(
        encoding="utf-8"
    )

    assert "`main` is a merge-commit branch by default." in text
    assert "Use squash merges only for the narrow single-commit" in text
    assert "do not squash PRs with multiple authored commits" in text
    assert "non-pushed checkpoint commit may be amended" in text
    assert "single-checkpoint exception" in implementation_text
    assert "search existing open issues first" in implementation_text
    assert "use the repo-standard issue structure" in implementation_text
    assert "Single-checkpoint PRs must squash." in pr_template


def test_implementation_anchor_references_use_explicit_doc_paths() -> None:
    paths = (
        repo_root() / "AGENTS.md",
        docs_root() / "standards" / "implementation.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "implementation plan" not in text.lower(), (
            f"{path} still uses vague implementation-plan wording"
        )


def test_reference_docs_do_not_check_in_oracle_data_files() -> None:
    forbidden_suffixes = {".csv", ".json", ".zip", ".html", ".pdf"}

    for path in sorted((docs_root() / "reference").rglob("*")):
        if not path.is_file():
            continue
        assert path.suffix not in forbidden_suffixes, (
            f"repo reference docs should not contain oracle data files: {path}"
        )


def test_adapter_pack_goldens_do_not_embed_absolute_home_paths() -> None:
    forbidden = ("/home/user/", "CoinTracking.info/tallylot-2025")

    for path in sorted(adapter_packs_root().rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still embeds absolute local path content"
            )
