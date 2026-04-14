from __future__ import annotations

import ast
import importlib
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path

from repo_support.paths import repo_root
from repo_support.pyright_config import PYRIGHT_GENERATED_TEST_CONFIG_NAME
from tallylot.adapters.support.drafts import economic_leg
from tallylot.domain.transactions import EconomicLeg, ProjectionHint, TransactionFact

CLASSIFICATION_KEYWORDS = frozenset(
    {
        "economic_kind",
        "projection_hint",
        "accounting_intent_hint",
        "tax_treatment_hint",
    }
)


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.rglob("*.py")))


def _all_repo_python_files() -> tuple[Path, ...]:
    return (
        repo_root() / "conftest.py",
        *_python_files(repo_root() / "repo_support"),
        *_python_files(repo_root() / "src"),
        *_python_files(repo_root() / "tests"),
        *_python_files(repo_root() / "tools"),
    )


def _repo_side_python_files() -> tuple[Path, ...]:
    root = repo_root()
    repo_side_paths = (
        root / "conftest.py",
        *sorted((root / "repo_support").rglob("*.py")),
        *sorted((root / "tools").rglob("*.py")),
        *sorted((root / "tests").rglob("*.py")),
        *sorted((root / "src" / "tallylot").rglob("tests/**/*.py")),
    )
    seen: dict[Path, None] = {}
    for path in repo_side_paths:
        seen[path] = None
    return tuple(seen)


def _production_python_files(root: Path) -> tuple[Path, ...]:
    return tuple(path for path in _python_files(root) if "tests" not in path.parts)


def _is_named_call(node: ast.expr, name: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id == name
    if isinstance(node, ast.Attribute):
        return node.attr == name
    return False


def _assert_no_imports(
    root: Path, forbidden_modules: tuple[str, ...], *, production_only: bool = False
) -> None:
    python_files = (
        _production_python_files(root) if production_only else _python_files(root)
    )

    for path in python_files:
        module = _module(path)
        for node in ast.walk(module):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                for forbidden in forbidden_modules:
                    assert not (
                        node.module == forbidden
                        or node.module.startswith(f"{forbidden}.")
                    ), f"{path} imports forbidden module {forbidden}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not (
                            alias.name == forbidden
                            or alias.name.startswith(f"{forbidden}.")
                        ), f"{path} imports forbidden module {forbidden}"


def _uses_direct_repo_root_derivation(path: Path) -> bool:
    def is_dunder_file_expr(node: ast.expr) -> bool:
        return isinstance(node, ast.Name) and node.id == "__file__"

    def is_path_dunder_file_expr(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Call)
            and _is_named_call(node.func, "Path")
            and len(node.args) == 1
            and is_dunder_file_expr(node.args[0])
        )

    def is_resolve_call(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "resolve"
            and is_path_dunder_file_expr(node.func.value)
        )

    def is_repo_root_derivation(node: ast.expr) -> bool:
        current = node
        if (
            isinstance(current, ast.Subscript)
            and isinstance(current.value, ast.Attribute)
            and current.value.attr == "parents"
        ):
            return is_resolve_call(current.value.value)
        while isinstance(current, ast.Attribute) and current.attr == "parent":
            current = current.value
        return is_resolve_call(current)

    module = _module(path)
    for node in ast.walk(module):
        if not isinstance(
            node,
            ast.Assign
            | ast.AnnAssign
            | ast.NamedExpr
            | ast.Call
            | ast.Attribute
            | ast.Subscript,
        ):
            continue
        candidate: ast.expr | None = (
            node.value
            if isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr)
            else node
        )
        if candidate is not None and is_repo_root_derivation(candidate):
            return True
    return False


def test_repo_root_derivation_guard_catches_parent_and_parents_forms(
    tmp_path: Path,
) -> None:
    parent_form = tmp_path / "parent_form.py"
    parent_form.write_text(
        "from pathlib import Path\nREPO = Path(__file__).resolve().parent.parent\n",
        encoding="utf-8",
    )
    parents_form = tmp_path / "parents_form.py"
    parents_form.write_text(
        "from pathlib import Path\nREPO = Path(__file__).resolve().parents[1]\n",
        encoding="utf-8",
    )
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        "from repo_support.paths import repo_root\nROOT = repo_root()\n",
        encoding="utf-8",
    )

    assert _uses_direct_repo_root_derivation(parent_form) is True
    assert _uses_direct_repo_root_derivation(parents_form) is True
    assert _uses_direct_repo_root_derivation(allowed) is False


def _defines_root_constants(path: Path) -> bool:
    constant_names = {"REPO_ROOT", "DOCS_ROOT", "AGENTS_ROOT"}
    module = _module(path)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constant_names
            for target in node.targets
        ):
            return True
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in constant_names
        ):
            return True
    return False


def test_repo_has_no_type_ignore_comments() -> None:
    forbidden = (
        "type:" + " ignore",
        "pyright:" + " ignore",
        "# " + "pyright:",
        "# " + "mypy:",
    )

    for path in _all_repo_python_files():
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} contains forbidden typing bypass {needle!r}"
            )


def test_protected_access_suppressions_only_live_in_test_pylint_config() -> None:
    needle = "protected" + "-access"
    allowed_paths = {
        repo_root() / "tests" / "unit" / "test_run_pylint.py",
    }

    for path in _all_repo_python_files():
        if path in allowed_paths:
            continue
        text = path.read_text(encoding="utf-8")
        assert needle not in text, f"{path} contains scattered {needle!r} suppression"


def test_repo_root_derivation_is_centralized_in_repo_support_paths() -> None:
    approved = repo_root() / "repo_support" / "paths.py"

    offenders = [
        path
        for path in _repo_side_python_files()
        if path != approved and _uses_direct_repo_root_derivation(path)
    ]

    assert not offenders, (
        f"repo-side python still derives repo root outside repo_support.paths: {offenders}"
    )


def test_repo_side_python_does_not_define_repo_root_constants() -> None:
    offenders = [
        path for path in _repo_side_python_files() if _defines_root_constants(path)
    ]

    assert not offenders, (
        f"repo-side python still defines local root constants: {offenders}"
    )


def test_production_code_does_not_import_repo_support_or_tools() -> None:
    src_root = repo_root() / "src" / "tallylot"

    _assert_no_imports(src_root, ("repo_support", "tools"), production_only=True)


def test_repo_support_avoids_generic_sink_modules() -> None:
    forbidden = {"helpers.py", "utils.py", "common.py", "misc.py"}
    support_root = repo_root() / "repo_support"
    if not support_root.exists():
        raise AssertionError("repo_support package is missing")
    offenders = sorted(
        path.name for path in support_root.rglob("*.py") if path.name in forbidden
    )

    assert not offenders, (
        f"repo_support contains forbidden generic sink modules: {offenders}"
    )


def test_markdownlint_only_disables_md013() -> None:
    config = json.loads(
        (repo_root() / ".markdownlint.json").read_text(encoding="utf-8")
    )
    assert config == {"default": True, "MD013": False}


def test_module_size_policy_remains_aligned() -> None:
    pylint_text = (repo_root() / ".pylintrc").read_text(encoding="utf-8")
    test_pylint_text = (repo_root() / ".pylintrc-tests").read_text(encoding="utf-8")
    standards_text = (repo_root() / "docs/standards/engineering.md").read_text(
        encoding="utf-8"
    )

    assert "max-module-lines = 600" in pylint_text
    assert "max-module-lines = 600" in test_pylint_text
    assert (
        re.search(r"Refactor before extending beyond 500 lines", standards_text)
        is not None
    )
    assert (
        re.search(
            r"Treat `500` lines as the official repo refactor limit", standards_text
        )
        is not None
    )
    assert (
        re.search(
            r"Enforced limit is `600` lines as the hard-stop lint ceiling",
            standards_text,
        )
        is not None
    )
    assert (
        re.search(
            r"Keep the repo standard tighter than the enforcement ceiling",
            standards_text,
        )
        is not None
    )


def test_delivery_standards_pin_merge_subject_and_repair_label_rules() -> None:
    commits_text = (repo_root() / "docs/standards/commits.md").read_text(
        encoding="utf-8"
    )
    implementation_text = (repo_root() / "docs/standards/implementation.md").read_text(
        encoding="utf-8"
    )
    issues_text = (repo_root() / "docs/standards/issues.md").read_text(encoding="utf-8")
    agents_text = (repo_root() / "AGENTS.md").read_text(encoding="utf-8")
    pr_template_text = (repo_root() / ".github" / "pull_request_template.md").read_text(
        encoding="utf-8"
    )
    message_standards_text = (repo_root() / "tools/message_standards.py").read_text(
        encoding="utf-8"
    )
    pr_validator_text = (repo_root() / "tools/validate_pr_metadata.py").read_text(
        encoding="utf-8"
    )
    commit_validator_text = (
        repo_root() / "tools/validate_commit_message.py"
    ).read_text(encoding="utf-8")
    checkpoint_text = (
        repo_root() / ".claude/commands/implementation-checkpoint.md"
    ).read_text(encoding="utf-8")

    assert "<pr title> (#<pr number>)" in commits_text
    assert "<pr title> (#<pr number>)" in implementation_text
    assert "<pr title> (#<pr number>)" in agents_text
    assert "<pr title> (#<pr number>)" in checkpoint_text
    assert "Issue linkage:" in commits_text
    assert "Issue linkage:" in issues_text
    assert "Issue linkage:" in pr_template_text
    assert "file/stdin authoring forms" in commits_text
    assert "shell-sensitive text" in commits_text
    assert "Follow-ups:" in commits_text
    assert "optional `Follow-ups:` section is allowed" in commits_text
    assert "Follow-ups:" in pr_template_text
    assert '"Issue linkage"' in message_standards_text
    assert 'PR_BODY_OPTIONAL_SECTIONS = ("Follow-ups",)' in message_standards_text
    assert "PR_BODY_OPTIONAL_SECTIONS" in pr_validator_text
    assert "`Issue linkage:`" in pr_validator_text
    assert "GENERATED_MAINLINE_COMMIT_OPTIONAL_SECTIONS" in commit_validator_text
    assert "`- Closes #123: <problem statement>`" in commits_text
    assert "`- Refs #123`" in issues_text
    assert "`- None: ...`" in issues_text
    assert "duplicate/superseded label" in commits_text
    assert "duplicate/superseded label" in implementation_text
    assert "duplicate/superseded label" in agents_text
    assert "duplicate/superseded label" in checkpoint_text
    assert "Every authored commit must stay bounded to" in commits_text
    assert "multiple bounded checkpoint commits" in commits_text
    assert "keep each authored commit bounded" in implementation_text
    assert "split it into\n   multiple bounded checkpoint commits" in checkpoint_text
    assert "keep every authored commit bounded to one reviewable slice" in agents_text


def test_delivery_guardrails_doc_is_routed_and_layered() -> None:
    guardrails_text = (repo_root() / "docs/standards/delivery-guardrails.md").read_text(
        encoding="utf-8"
    )
    docs_index_text = (repo_root() / "docs/README.md").read_text(encoding="utf-8")
    agents_text = (repo_root() / "AGENTS.md").read_text(encoding="utf-8")
    roadmap_text = (repo_root() / "ROADMAP.md").read_text(encoding="utf-8")
    checkpoint_text = (
        repo_root() / ".claude/commands/implementation-checkpoint.md"
    ).read_text(encoding="utf-8")
    hardening_route_text = (
        repo_root() / ".claude" / "commands" / "pr-review.md"
    ).read_text(encoding="utf-8")

    assert "platform-native enforcement" in guardrails_text
    assert "repo-native policy as code" in guardrails_text
    assert "agent default behavior" in guardrails_text
    assert "<pr title> (#<pr number>)" in guardrails_text
    assert "draft by default" in guardrails_text
    assert "ready for review" in guardrails_text
    assert "evidence-backed findings" in guardrails_text
    assert "duplicate or superseded label" in guardrails_text
    assert "tools.audit_delivery_guardrails" in guardrails_text
    assert "single review-capable collaborator" in guardrails_text
    assert ".github/actions/**" in guardrails_text
    assert ".github/ISSUE_TEMPLATE/**" in guardrails_text
    assert "docs/status/current-state.md" in guardrails_text
    assert "tools/docs_maintenance/cli.py" in guardrails_text
    assert "tools/benchmark_quality_gates.py" in guardrails_text
    assert "repo_support/local_autofix.py" in guardrails_text
    assert "repo_support/review_verification/**" in guardrails_text
    assert "tools/evaluate_review_results.py" in guardrails_text
    assert "`markdown` skill" in guardrails_text
    assert "human docs, agent" in guardrails_text
    assert "standards/delivery-guardrails.md" in docs_index_text
    assert "standards/issues.md" in docs_index_text
    assert (
        "Repo standards, docs placement, doc authoring rules, or agent-default enforcement changes"
        in agents_text
    )
    assert (
        "Issue templates, issue-writing policy, or proactive follow-up issue creation"
        in agents_text
    )
    assert "use the `markdown` skill if available" in agents_text
    assert (
        "use\n  the repo-local workflow for the active surface and reload the narrow repo\n  guidance listed in this file before editing."
        in agents_text
    )
    assert "docs/standards/issues.md" in agents_text
    assert ".claude/commands/issue-workflow.md" in agents_text
    assert "tools/docs_maintenance/metadata.py" in agents_text
    assert "docs/reference/repository-history.md" in agents_text
    assert "docs/standards/delivery-guardrails.md" in agents_text
    assert ".claude/commands/pr-review.md" in agents_text
    assert "delivery guardrails layered across platform settings" in roadmap_text
    assert "control-plane ownership routing" in roadmap_text
    assert "audit local CODEOWNERS coverage and live GitHub delivery" in roadmap_text
    assert "settings together without broad context loading" in roadmap_text
    assert "repo-native PR review routing" in roadmap_text
    assert "benchmark-backed" in roadmap_text
    assert "one opaque parity shell" in roadmap_text
    assert (
        "if standards, docs placement, doc authoring rules, or agent-default enforcement changed"
        in checkpoint_text
    )
    assert (
        "use `markdown` for Markdown/docs work when that skill is available"
        in checkpoint_text
    )
    assert "shell-safe commit and PR authoring rules" in checkpoint_text
    assert "scratch workflow bookkeeping" in checkpoint_text
    assert "search for an existing issue first" in checkpoint_text
    assert "`human_docs`" in guardrails_text
    assert "`control_plane_text`" in guardrails_text
    assert "`repo_code_or_tooling`" in guardrails_text
    assert "`ci_or_release`" in guardrails_text
    assert "selected verification mode" in guardrails_text
    assert "always-visible PR metadata checks" in guardrails_text
    assert "full non-duplicated blocking suite" in guardrails_text
    assert "suppresses the narrower targeted pytest subset checks" in guardrails_text
    assert (
        "every applicable changed surface group has been revisited" in guardrails_text
    )
    assert "issue-finding with open outcome" in guardrails_text
    assert "tools.audit_pr_review" in hardening_route_text
    assert "tools.run_pr_review_checks" in hardening_route_text
    assert (
        "green runner never replaces the mandatory red-team repair" in guardrails_text
    )
    assert (
        "green `tools.run_pr_review_checks` result as a no-findings"
        in hardening_route_text
    )
    assert "issue-finding loop" in hardening_route_text
    assert "invent findings to hit a quota" in hardening_route_text
    assert (
        "stop only after a full pass yields no new meaningful findings"
        not in guardrails_text
    )
    assert "clean hardening pass" not in guardrails_text
    assert "full clean loop" not in hardening_route_text
    assert "claiming a clean pass" not in hardening_route_text
    assert "final PR review" not in hardening_route_text
    assert (
        "Continue steps 1 through 5 until every applicable changed surface group has"
        in hardening_route_text
    )


def test_repo_local_routing_does_not_depend_on_removed_global_safety_skills() -> None:
    guardrails_text = (repo_root() / "docs/standards/delivery-guardrails.md").read_text(
        encoding="utf-8"
    )
    hardening_route_text = (
        repo_root() / ".claude" / "commands" / "pr-review.md"
    ).read_text(encoding="utf-8")

    for relative_path in (
        "AGENTS.md",
        ".agents/skills/implementation-workflow/SKILL.md",
        ".agents/skills/issue-workflow/SKILL.md",
        ".agents/skills/docs-authoring/SKILL.md",
        ".claude/commands/implementation-checkpoint.md",
        "docs/standards/delivery-guardrails.md",
    ):
        text = (repo_root() / relative_path).read_text(encoding="utf-8")
        assert "code-change-safety" not in text
        assert "git-delivery-safety" not in text
        assert "docs-change-safety" not in text
    assert (
        "repair every finding from that pass before starting the next pass"
        in guardrails_text
    )
    assert "issue-finding with open outcome" in hardening_route_text
    assert "AGENTS.md`, its task-routing table" in guardrails_text
    assert "checkpoint commits during the loop" in guardrails_text
    assert "applicable surface groups" in guardrails_text
    assert (
        "Repair every finding from that pass before starting the next pass"
        in hardening_route_text
    )
    assert "verification evidence for the current" in hardening_route_text
    assert "red-team pass" in hardening_route_text
    assert "create a bounded checkpoint commit" in hardening_route_text
    assert "relevant delivery guidance or skills" in hardening_route_text
    assert "updating the PR state" in hardening_route_text
    assert "tools.audit_pr_review" in hardening_route_text
    assert "tools.run_pr_review_checks" in hardening_route_text


def test_control_plane_codeowners_file_exists_and_covers_guardrail_paths() -> None:
    codeowners_path = repo_root() / ".github" / "CODEOWNERS"
    assert codeowners_path.exists(), ".github/CODEOWNERS is missing"

    codeowners_text = codeowners_path.read_text(encoding="utf-8")
    required_entries = (
        ".agents/skills/**",
        ".github/actions/**",
        ".github/ISSUE_TEMPLATE/**",
        ".github/workflows/**",
        ".github/pull_request_template.md",
        ".github/CODEOWNERS",
        "AGENTS.md",
        "docs/standards/**",
        ".claude/commands/**",
        "repo_support/local_autofix.py",
        "repo_support/quality_gates.py",
        "repo_support/review_verification/**",
        "tools/install_git_hooks.py",
        "tools/pre_commit_hook.py",
        "tools/pre_push_hook.py",
        "tools/audit_delivery_guardrails.py",
        "tools/audit_pr_review.py",
        "tools/benchmark_quality_gates.py",
        "tools/evaluate_review_results.py",
        "tools/message_standards.py",
        "tools/run_review_check.py",
        "tools/run_pr_review_checks.py",
        "tools/validate_commit_message.py",
        "tools/validate_pr_metadata.py",
        "tools/run_quality_gates.py",
        "tools/verify_built_wheel.py",
    )

    for entry in required_entries:
        assert entry in codeowners_text, f"CODEOWNERS is missing {entry}"


def test_src_does_not_accumulate_flat_same_prefix_clusters() -> None:
    source_root = repo_root() / "src" / "tallylot"

    for directory in sorted({path.parent for path in source_root.rglob("*.py")}):
        prefix_groups: dict[str, list[str]] = defaultdict(list)
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            parts = path.stem.split("_")
            if len(parts) < 2:
                continue
            prefix_groups["_".join(parts[:2])].append(path.name)
        offenders = {
            prefix: names for prefix, names in prefix_groups.items() if len(names) > 2
        }
        assert not offenders, (
            f"{directory} has flat same-prefix clusters that should be packaged: {offenders}"
        )


def test_retired_bucket_directories_do_not_exist() -> None:
    src_root = repo_root() / "src" / "tallylot"

    assert not (src_root / "application" / "services").exists()
    assert not (src_root / "application" / "models").exists()
    assert not (src_root / "domain" / "models").exists()
    assert not (src_root / "ports" / "adapters.py").exists()
    assert not (src_root / "ports" / "storage.py").exists()
    assert not (src_root / "ports" / "output_workflows.py").exists()


def test_oracle_code_is_not_in_production_package() -> None:
    src_root = repo_root() / "src" / "tallylot"
    forbidden = (
        src_root / "application" / "oracle_review",
        src_root / "adapters" / "oracles",
    )
    for path in forbidden:
        assert not path.exists()

    for path in sorted(src_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        assert "oracle review" not in text
        assert "baseline validation" not in text
        assert "verification compare" not in text


def test_future_capability_roots_remain_available_for_next_phase() -> None:
    src_root = repo_root() / "src" / "tallylot"

    required_packages = (
        src_root / "application" / "balances",
        src_root / "application" / "reconciliation",
        src_root / "application" / "checkpoints",
        src_root / "application" / "accounting",
        src_root / "application" / "tax",
        src_root / "domain" / "balances",
        src_root / "domain" / "accounting",
        src_root / "domain" / "tax",
        src_root / "domain" / "transactions",
        src_root / "infrastructure" / "composition",
    )
    required_modules = (
        src_root / "ports" / "facts.py",
        src_root / "ports" / "evidence.py",
        src_root / "ports" / "balance_providers.py",
        src_root / "ports" / "source_translation.py",
        src_root / "ports" / "source_adapters.py",
        src_root / "ports" / "output_adapters.py",
    )

    for package in required_packages:
        assert package.is_dir(), f"missing future capability package root: {package}"
        assert (package / "__init__.py").exists(), (
            f"missing package marker for {package}"
        )
        importlib.import_module(".".join(package.relative_to(src_root.parent).parts))
    for module in required_modules:
        assert module.exists(), f"missing capability boundary module: {module}"


def test_production_packaging_excludes_dev_only_oracle_tooling() -> None:
    pyproject = tomllib.loads(
        (repo_root() / "pyproject.toml").read_text(encoding="utf-8")
    )

    scripts = pyproject["project"]["scripts"]
    wheel_packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]

    assert scripts == {"tallylot": "tallylot.interfaces.cli:app"}
    assert wheel_packages == ["src/tallylot"]
    assert all("tools.oracles" not in target for target in scripts.values())


def test_typecheck_configs_remain_strict() -> None:
    mypy_text = (repo_root() / "mypy.ini").read_text(encoding="utf-8")
    pyright_config = json.loads(
        (repo_root() / "pyrightconfig.json").read_text(encoding="utf-8")
    )

    assert "strict = true" in mypy_text
    assert "warn_unused_ignores = true" in mypy_text
    assert "files = src, tests, tools, repo_support" in mypy_text
    assert pyright_config["typeCheckingMode"] == "strict"
    assert pyright_config["reportUnnecessaryTypeIgnoreComment"] is True
    assert "repo_support" in pyright_config["include"]


def test_pyright_private_usage_config_matches_repo_test_trees() -> None:
    pyright_config = json.loads(
        (repo_root() / PYRIGHT_GENERATED_TEST_CONFIG_NAME).read_text(encoding="utf-8")
    )
    expected_private_usage_roots = {
        "tests",
        *(
            path.relative_to(repo_root()).as_posix()
            for path in sorted(
                (repo_root() / "src" / "tallylot" / "adapters").rglob("tests")
            )
            if path.is_dir()
        ),
    }

    private_usage_roots = {
        environment["root"]
        for environment in pyright_config["executionEnvironments"]
        if environment.get("reportPrivateUsage") is False
    }

    assert private_usage_roots == expected_private_usage_roots


def test_pyright_root_config_extends_generated_test_config() -> None:
    pyright_config = json.loads(
        (repo_root() / "pyrightconfig.json").read_text(encoding="utf-8")
    )

    assert pyright_config.get("extends") == f"./{PYRIGHT_GENERATED_TEST_CONFIG_NAME}"
    assert "executionEnvironments" not in pyright_config


def test_application_modules_do_not_import_infrastructure() -> None:
    application_root = repo_root() / "src" / "tallylot" / "application"

    _assert_no_imports(application_root, ("tallylot.infrastructure",))


def test_domain_modules_do_not_import_outer_layers_or_pydantic() -> None:
    domain_root = repo_root() / "src" / "tallylot" / "domain"

    _assert_no_imports(
        domain_root,
        (
            "tallylot.application",
            "tallylot.ports",
            "tallylot.infrastructure",
            "tallylot.interfaces",
            "pydantic",
        ),
    )


def test_ports_modules_do_not_import_implementation_layers() -> None:
    ports_root = repo_root() / "src" / "tallylot" / "ports"

    _assert_no_imports(
        ports_root,
        (
            "tallylot.application",
            "tallylot.adapters",
            "tallylot.infrastructure",
            "tallylot.interfaces",
        ),
    )


def test_adapter_production_modules_do_not_import_application_or_infrastructure() -> (
    None
):
    adapters_root = repo_root() / "src" / "tallylot" / "adapters"

    _assert_no_imports(
        adapters_root,
        (
            "tallylot.application",
            "tallylot.infrastructure",
        ),
        production_only=True,
    )


def test_transaction_fact_category_bridge_is_removed() -> None:
    assert not hasattr(TransactionFact, "category")


def test_transaction_fact_single_leg_compatibility_helpers_are_removed() -> None:
    for attribute in (
        "asset_in",
        "amount_in",
        "asset_out",
        "amount_out",
        "fee_asset",
        "fee_amount",
        "fee_legs",
    ):
        assert not hasattr(TransactionFact, attribute)


def test_economic_leg_fee_specific_helper_and_flag_are_removed() -> None:
    assert not hasattr(EconomicLeg, "is_fee")
    assert economic_leg.__name__ != "fee_leg"


def test_repo_does_not_reference_fact_category_attribute() -> None:
    guarded_roots = (
        repo_root() / "src" / "tallylot" / "adapters",
        repo_root() / "src" / "tallylot" / "application" / "outputs",
        repo_root() / "src" / "tallylot" / "infrastructure" / "storage",
        repo_root() / "src" / "tallylot" / "adapters" / "support",
        repo_root() / "tests" / "unit" / "domain",
        repo_root() / "tests" / "unit" / "application" / "outputs",
        repo_root() / "tests" / "contract",
    )

    for root in guarded_roots:
        for path in _python_files(root):
            for node in ast.walk(_module(path)):
                if isinstance(node, ast.Attribute):
                    assert node.attr != "category", (
                        f"{path} references removed fact category attribute"
                    )


def test_repo_does_not_reference_removed_single_leg_fact_attributes() -> None:
    guarded_roots = (
        repo_root() / "src" / "tallylot",
        repo_root() / "tests",
    )
    forbidden_attributes = {
        "asset_in",
        "amount_in",
        "asset_out",
        "amount_out",
        "fee_asset",
        "fee_amount",
        "fee_legs",
        "is_fee",
    }

    for root in guarded_roots:
        for path in _python_files(root):
            for node in ast.walk(_module(path)):
                if isinstance(node, ast.Attribute):
                    assert node.attr not in forbidden_attributes, (
                        f"{path} references removed single-leg fact attribute {node.attr}"
                    )


def test_source_adapters_do_not_pass_string_classification_values() -> None:
    adapters_root = repo_root() / "src" / "tallylot" / "adapters" / "sources"

    for path in _python_files(adapters_root):
        for node in ast.walk(_module(path)):
            if not isinstance(node, ast.Call):
                continue
            if not _is_named_call(node.func, "classification"):
                continue
            for keyword in node.keywords:
                if keyword.arg not in CLASSIFICATION_KEYWORDS:
                    continue
                if isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, str
                ):
                    raise AssertionError(
                        f"{path} passes string classification value {keyword.arg}={keyword.value.value!r} "
                        "through shared draft helpers"
                    )


def test_projection_hint_runtime_values_remain_machine_oriented() -> None:
    assert ProjectionHint.TRADE.value == "trade"
    assert ProjectionHint.DEPOSIT.value == "deposit"
    assert ProjectionHint.WITHDRAWAL.value == "withdrawal"


def test_balance_reference_has_single_production_owner() -> None:
    occurrences = 0
    for path in _python_files(repo_root() / "src" / "tallylot"):
        text = path.read_text(encoding="utf-8")
        occurrences += text.count("class BalanceReference:")
    assert occurrences == 1


def test_transaction_classification_matrix_describes_runtime_projection_values() -> (
    None
):
    matrix_text = (
        repo_root() / "docs" / "concepts" / "transaction-classification.md"
    ).read_text(encoding="utf-8")

    assert (
        "| `trade` | `trade` | `spot_trade` | `capital_exchange` | `asset_exchange` |"
        in matrix_text
    )
    assert (
        "| `deposit` | `deposit` | `asset_deposit` | `non_taxable_transfer_in` | `funding_inflow` |"
        in matrix_text
    )
    assert (
        "| `withdrawal` | `withdrawal` | `asset_withdrawal` | `non_taxable_transfer_out` | `funding_outflow` |"
        in matrix_text
    )
    assert "enum members such as `ProjectionHint.TRADE`" in matrix_text
    assert "stored/runtime values such as `trade`" in matrix_text
    assert "renderer labels such as `Trade`" in matrix_text
