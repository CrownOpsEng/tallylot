from __future__ import annotations

DOCS_AUDIT_SUBSTRATE_PREFIXES = (
    "docs/",
    ".claude/commands/",
    "src/tallylot/interfaces/cli/",
    "tools/oracles/",
)

DOCS_AUDIT_SUBSTRATE_EXACT_PATHS = {
    "README.md",
    "AGENTS.md",
    "ROADMAP.md",
    "src/tallylot/infrastructure/workspace/layout.py",
    "src/tallylot/domain/captures/provenance.py",
    "src/tallylot/ports/source_profiles.py",
    "src/tallylot/domain/transactions/classification.py",
    ".pylintrc",
    ".pylintrc-tests",
    "tools/message_standards.py",
    "tools/validate_commit_message.py",
    "tools/validate_pr_metadata.py",
}


def is_docs_audit_substrate_path(path: str) -> bool:
    return path in DOCS_AUDIT_SUBSTRATE_EXACT_PATHS or any(
        path.startswith(prefix) for prefix in DOCS_AUDIT_SUBSTRATE_PREFIXES
    )
