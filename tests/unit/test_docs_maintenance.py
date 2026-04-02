from __future__ import annotations

from pathlib import Path

from tools import docs_maintenance

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    *sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")),
)


def test_docs_maintenance_sync_check_passes() -> None:
    assert docs_maintenance.main(["sync", "--check"]) == 0


def test_docs_and_agents_pages_have_valid_frontmatter() -> None:
    paths = (
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / "agents").rglob("*.md")),
    )
    documents = docs_maintenance.validate_documents()

    assert {document.path for document in documents} == set(paths)


def test_entrypoints_do_not_reference_retired_docs_paths() -> None:
    for path in ENTRYPOINT_PATHS:
        text = path.read_text(encoding="utf-8")
        for retired_reference in docs_maintenance.RETIRED_REFERENCES:
            assert retired_reference not in text, (
                f"{path.relative_to(REPO_ROOT)} still references retired path {retired_reference}"
            )
