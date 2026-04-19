from __future__ import annotations

import re

from repo_support.paths import repo_root

from ._common import build_rule
from ..helpers import (
    architecture_doc_paths,
    joined,
    repo_text,
)


POLICY_ALIGNMENT_RULES = (
    build_rule(
        "policy_alignment.docs_do_not_reference_retired_service_or_model_buckets",
        "docs/standards/engineering.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"{path} still references retired surface {needle!r}")
            )
            for path in architecture_doc_paths()
            for needle in (
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
            if needle in path.read_text(encoding="utf-8").lower()
        ],
    ),
    build_rule(
        "policy_alignment.repo_docs_do_not_reference_personal_workspace_roots",
        "AGENTS.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"{path} still references personal workspace path {needle}"
                )
            )
            for path in (
                repo_root() / "README.md",
                repo_root() / "AGENTS.md",
                repo_root() / "tallylot.toml",
                *sorted((repo_root() / "docs").rglob("*.md")),
                *sorted((repo_root() / ".claude").rglob("*.md")),
            )
            for needle in ("/home/user/", "Documents/", "~/Documents/")
            if needle in path.read_text(encoding="utf-8")
        ],
    ),
    build_rule(
        "policy_alignment.commit_standards_require_explicit_lint_amend_reverification",
        "docs/standards/commits.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing commit standard text {needle!r}")
            )
            for needle in (
                "Do not describe `mypy` or `pyright` as covering `pylint` findings.",
                "make pylint ARGS='<touched-file>'",
                "make pytest ARGS='-q --no-cov <touched-test-file>'",
                "git show HEAD:<path>",
            )
            if needle not in repo_text("docs/standards/commits.md")
        ],
    ),
    build_rule(
        "policy_alignment.forward_target_docs_encode_phase_10_default_read_model_activation",
        "ROADMAP.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("Phase 10 default activation wording is out of sync")
            )
            for condition in (
                "Phase 10" not in repo_text("ROADMAP.md"),
                "Phase 10" not in repo_text("docs/concepts/architecture-overview.md"),
                "Phase 10" not in repo_text("docs/status/migration-sequence.md"),
                "Phase 10"
                not in repo_text("docs/concepts/bridge-to-target-mapping.md"),
                "default activation point"
                not in repo_text("docs/concepts/architecture-overview.md"),
                "default activation point"
                not in repo_text("docs/status/migration-sequence.md"),
                "activation defaults to `Phase 10`"
                not in repo_text("docs/concepts/bridge-to-target-mapping.md"),
            )
            if condition
        ],
    ),
    build_rule(
        "policy_alignment.forward_target_docs_reserve_specific_read_model_package_names",
        "docs/concepts/domain-ontology.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"reserved read-model package path {reserved_path!r} is missing"
                )
            )
            for reserved_path in (
                "application/reporting/",
                "application/portfolio/",
                "application/visualization/",
                "application/investigation/",
            )
            if reserved_path not in repo_text("ROADMAP.md")
            or reserved_path not in repo_text("docs/concepts/domain-ontology.md")
            or reserved_path not in repo_text("docs/standards/engineering.md")
        ],
    ),
    build_rule(
        "policy_alignment.commit_standards_require_scoped_subjects",
        "docs/standards/commits.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing scoped subject rule {needle!r}")
            )
            for needle in (
                "type(scope): imperative summary",
                "required lowercase kebab-case scope",
            )
            if needle not in repo_text("docs/standards/commits.md")
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError("commit subjects must not describe scope as optional")
            )
            if "The scope is optional" in repo_text("docs/standards/commits.md")
            else None
        ],
    ),
    build_rule(
        "policy_alignment.commit_standards_document_hybrid_pr_merge_policy",
        "docs/standards/commits.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing merge-policy text {needle!r}")
            )
            for needle in (
                "`main` is a merge-commit branch by default.",
                "Use squash merges only for the narrow single-commit",
                "do not squash PRs with multiple authored commits",
                "non-pushed checkpoint commit may be amended",
                "single-checkpoint exception",
                "search existing open issues first",
                "use the repo-standard issue structure",
                "Single-checkpoint PRs must squash.",
            )
            if needle
            not in "\n".join(
                (
                    repo_text("docs/standards/commits.md"),
                    repo_text("docs/standards/implementation.md"),
                    repo_text(".github/pull_request_template.md"),
                )
            )
        ],
    ),
    build_rule(
        "policy_alignment.module_size_policy_remains_aligned",
        ".pylintrc",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    "module size policy drifted between lint config and engineering standards"
                )
            )
            for condition in (
                "max-module-lines = 600" not in repo_text(".pylintrc"),
                "max-module-lines = 600" not in repo_text(".pylintrc-tests"),
                re.search(
                    r"Refactor before extending beyond 500 lines",
                    repo_text("docs/standards/engineering.md"),
                )
                is None,
                re.search(
                    r"Treat `500` lines as the official repo refactor limit",
                    repo_text("docs/standards/engineering.md"),
                )
                is None,
                re.search(
                    r"Enforced limit is `600` lines as the hard-stop lint ceiling",
                    repo_text("docs/standards/engineering.md"),
                )
                is None,
                re.search(
                    r"Keep the repo standard tighter than the enforcement ceiling",
                    repo_text("docs/standards/engineering.md"),
                )
                is None,
            )
            if condition
        ],
    ),
    build_rule(
        "policy_alignment.delivery_standards_pin_merge_subject_and_repair_label_rules",
        "docs/standards/delivery-guardrails.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("delivery standards references drifted")
            )
            for condition in (
                "<pr title> (#<pr number>)"
                not in repo_text("docs/standards/commits.md"),
                "<pr title> (#<pr number>)"
                not in repo_text("docs/standards/implementation.md"),
                "<pr title> (#<pr number>)" not in repo_text("AGENTS.md"),
                "<pr title> (#<pr number>)"
                not in repo_text(".claude/commands/implementation-checkpoint.md"),
                "Issue linkage:" not in repo_text("docs/standards/commits.md"),
                "Issue linkage:" not in repo_text("docs/standards/issues.md"),
                "Issue linkage:" not in repo_text(".github/pull_request_template.md"),
                "duplicate/superseded label"
                not in repo_text("docs/standards/commits.md"),
                "duplicate/superseded label"
                not in repo_text("docs/standards/implementation.md"),
                "duplicate/superseded label" not in repo_text("AGENTS.md"),
                "duplicate/superseded label"
                not in repo_text(".claude/commands/implementation-checkpoint.md"),
            )
            if condition
        ],
    ),
    build_rule(
        "policy_alignment.delivery_guardrails_doc_is_routed_and_layered",
        "docs/standards/delivery-guardrails.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing guardrail routing text {needle!r}")
            )
            for needle in (
                "platform-native enforcement",
                "repo-native policy as code",
                "agent default behavior",
                "draft by default",
                "ready for review",
                "evidence-backed findings",
                "make audit-delivery-guardrails",
                "single review-capable collaborator",
                "repo_support/review_verification/**",
                "repo_support/target_naming/**",
                "tools/target_naming.py",
                "tools/target_naming_catalog.yaml",
                "`human_docs`",
                "`control_plane_text`",
                "`repo_code_or_tooling`",
                "`ci_or_release`",
                "selected verification mode",
                "always-visible PR metadata checks",
                "full non-duplicated blocking suite",
                "suppresses the narrower targeted pytest subset checks",
                "every applicable changed file group has been revisited",
                "issue-finding with open outcome",
                "green runner never replaces the mandatory red-team repair",
            )
            if needle not in repo_text("docs/standards/delivery-guardrails.md")
        ],
    ),
    build_rule(
        "policy_alignment.engineering_standards_document_contract_guard_expectations",
        "docs/standards/engineering.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"missing engineering contract-guard expectation {needle!r}"
                )
            )
            for needle in (
                "bridge cutover matrix inventory and row order are catalog-governed",
                "bridge cutover matrix owner, compatibility, reader, and gate cells are",
                "bridge cutover current-reader cells must use canonical inventory labels",
                "forward-target contract docs must stay free of transient planning language",
                "treat the blocking `target-naming` review check as the repo-native guard",
            )
            if needle not in repo_text("docs/standards/engineering.md")
        ],
    ),
    build_rule(
        "policy_alignment.repo_local_routing_does_not_depend_on_removed_global_safety_skills",
        "AGENTS.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"{relative_path} still references removed global safety skills"
                )
            )
            for relative_path in (
                "AGENTS.md",
                ".agents/skills/implementation-workflow/SKILL.md",
                ".agents/skills/issue-workflow/SKILL.md",
                ".agents/skills/docs-authoring/SKILL.md",
                ".claude/commands/implementation-checkpoint.md",
                "docs/standards/delivery-guardrails.md",
            )
            if any(
                needle in repo_text(relative_path)
                for needle in (
                    "code-change-safety",
                    "git-delivery-safety",
                    "docs-change-safety",
                )
            )
        ],
    ),
    build_rule(
        "policy_alignment.implementation_anchor_references_use_explicit_doc_paths",
        "AGENTS.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"{relative_path} still uses vague implementation-plan wording"
                )
            )
            for relative_path in ("AGENTS.md", "docs/standards/implementation.md")
            if joined("implementation", " plan") in repo_text(relative_path).lower()
        ],
    ),
)
