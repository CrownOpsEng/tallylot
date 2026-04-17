.DEFAULT_GOAL := help

PROJECT_ENV ?= $(HOME)/.venvs/tallylot-py312
PROJECT_BIN := $(PROJECT_ENV)/bin
TMP_ROOT ?= $(if $(TMPDIR),$(TMPDIR),/tmp)
UV_CACHE_DIR ?= $(TMP_ROOT)/tallylot-uv-cache
export VIRTUAL_ENV := $(PROJECT_ENV)
export UV_PROJECT_ENVIRONMENT := $(PROJECT_ENV)
export UV_CACHE_DIR := $(UV_CACHE_DIR)
export PATH := $(PROJECT_BIN):$(PATH)

ARGS ?=
TOOL ?=

.PHONY: help install-hooks workspace-init docs-sync docs-check quality quality-full \
	pr-review pr-review-full audit-delivery-guardrails audit-pr-review \
	test-stress coverage-hotspots benchmark-tests benchmark-quality \
	sync-pyright-config precommit markdownlint ruff mypy pyright pylint pytest \
	actionlint naming-check cli oracle tool validate-commit-message scaffold-adapter \
	refresh-adapter-goldens validate-workspace-replay

help:
	@printf '%s\n' \
		'TallyLot local command surface' \
		'' \
		'The Makefile configures PATH and the shared external environment once,' \
		'so local commands stay portable and repo docs do not need inline env' \
		'prefixes or machine-specific paths.' \
		'' \
		'Variables:' \
		'  PROJECT_ENV=<path>   Override the external virtualenv root.' \
		'  UV_CACHE_DIR=<path>  Override the temporary uv cache root for sandbox-safe uv runs.' \
		'  ARGS="<args>"       Pass extra arguments to a target command.' \
		'  TOOL=<module>       Select the tools.<module> entrypoint for `make tool`.' \
		'' \
		'Bootstrap:' \
		'  make install-hooks                    Sync the shared env and install repo git hooks.' \
		'  make workspace-init                   Initialize the external workspace.' \
		'' \
		'Docs:' \
		'  make docs-sync                        Refresh docs-maintenance generated content.' \
		'  make docs-check                       Verify docs-maintenance output is current.' \
		'  make naming-check                    Verify forward-looking target naming is aligned.' \
		'' \
		'Verification:' \
		'  make quality [ARGS="..."]            Run the default local quality gates.' \
		'  make quality-full [ARGS="..."]       Run the explicit full-suite override.' \
		'  make pr-review [ARGS="..."]          Run the planned PR-review checks.' \
		'  make pr-review-full [ARGS="..."]     Run the full PR-review suite.' \
		'  make audit-pr-review [ARGS="..."]    Audit review-surface selection and coverage.' \
		'  make audit-delivery-guardrails       Audit delivery policy enforcement.' \
		'  make test-stress [ARGS="..."]        Run order-sensitivity and flake checks.' \
		'  make coverage-hotspots [ARGS="..."]  Report recent full-suite coverage hotspots.' \
		'  make benchmark-tests [ARGS="..."]    Benchmark pytest scheduling variants.' \
		'  make benchmark-quality [ARGS="..."]  Benchmark quality-gate schedules.' \
		'' \
		'Direct runners:' \
		'  make cli ARGS="source intake plan ..."            Run the main tallylot CLI.' \
		'  make oracle ARGS="round scaffold ..."             Run oracle CLI routes.' \
		'  make tool TOOL=docs_maintenance ARGS="sync --check"  Run any tools.<module> entrypoint.' \
		'' \
		'Individual tools:' \
		'  make pytest ARGS="tests/unit/test_x.py -q --no-cov"' \
		'  make ruff ARGS="check ."' \
		'  make mypy ARGS="src tools repo_support"' \
		'  make pyright ARGS=""' \
		'  make pylint ARGS="src/tallylot/application/foo.py"' \
		'  make markdownlint ARGS="docs/README.md"' \
		'  make precommit ARGS="run markdownlint --all-files"' \
		'' \
		'Examples:' \
		'  make quality ARGS="--gate pytest --fail-fast"' \
		'  make pr-review-full ARGS="--pr-body-file /tmp/pr-body.md"' \
		'  make cli ARGS="checkpoint scaffold-balance-submission --source coinbase"' \
		'  make oracle ARGS="verification compare --current-dir <dir> --previous-dir <dir>"'

install-hooks:
	python -m tools.install_git_hooks $(ARGS)

workspace-init:
	tallylot workspace init $(ARGS)

docs-sync:
	python -m tools.docs_maintenance sync $(ARGS)

docs-check:
	python -m tools.docs_maintenance sync --check $(ARGS)

quality:
	python -m tools.run_quality_gates $(ARGS)

quality-full:
	python -m tools.run_quality_gates --full-tests $(ARGS)

pr-review:
	python -m tools.run_pr_review_checks $(ARGS)

pr-review-full:
	python -m tools.run_pr_review_checks --mode full $(ARGS)

audit-delivery-guardrails:
	python -m tools.audit_delivery_guardrails $(ARGS)

audit-pr-review:
	python -m tools.audit_pr_review $(ARGS)

test-stress:
	python -m tools.run_test_stress_checks $(ARGS)

coverage-hotspots:
	python -m tools.report_coverage_hotspots $(ARGS)

benchmark-tests:
	python -m tools.benchmark_tests $(ARGS)

benchmark-quality:
	python -m tools.benchmark_quality_gates $(ARGS)

sync-pyright-config:
	python -m tools.sync_pyright_config $(ARGS)

precommit:
	pre-commit $(ARGS)

markdownlint:
	markdownlint $(ARGS)

ruff:
	ruff $(ARGS)

mypy:
	mypy $(ARGS)

pyright:
	@python -m tools.sync_pyright_config > /dev/null
	pyright --project .pyrightconfig.local.json $(ARGS)

pylint:
	pylint $(ARGS)

pytest:
	pytest $(ARGS)

actionlint:
	actionlint $(ARGS)

naming-check:
	python -m tools.target_naming check $(ARGS)

cli:
	tallylot $(ARGS)

oracle:
	python -m tools.oracles.cli $(ARGS)

tool:
	@test -n "$(TOOL)" || { echo 'TOOL is required, e.g. make tool TOOL=docs_maintenance ARGS="sync --check"'; exit 2; }
	python -m tools.$(TOOL) $(ARGS)

validate-commit-message:
	python -m tools.validate_commit_message $(ARGS)

scaffold-adapter:
	python -m tools.scaffold_adapter $(ARGS)

refresh-adapter-goldens:
	python -m tools.refresh_adapter_goldens $(ARGS)

validate-workspace-replay:
	python -m tools.validate_workspace_replay $(ARGS)
