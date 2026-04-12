---
name: source-intake-operations
description: >-
  Run tallylot's typed intake path without ad hoc shell choreography. Use when
  the task is source intake planning, apply, manifesting, profiling,
  normalization, or checkpoint inventory follow-through.
---

# Source Intake Operations

Use this skill for source intake and normalization workflow execution.

## Workflow

1. Read the operator route first:
   - `docs/guides/operator-quickstart.md`
   - `docs/guides/source-intake.md`
   - `.claude/commands/source-intake.md`
2. Use the runtime CLI, not ad hoc loops:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake plan`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake apply`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source manifest`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source profile`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source normalize`
   - When the incoming evidence needs a stable source label, seed
     `analysis/issues/source_inventory.csv` and an explicit
     `analysis/issues/source_label_map.csv` row first; the planner uses the
     incoming directory name as the capture scope.
   - When you need to verify a rebuilt workspace, use
     `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_workspace_replay`
     against a reference workspace and a clean candidate workspace so replay
     parity stays explicit.
3. Review the emitted plan, profile, normalization, and issue artifacts before
   moving to the next stage.
4. Rebuild location inventory only when normalization produced wallet evidence.

## Focus

- plan before apply
- inspect artifacts between stages
- keep evidence outside the repo
