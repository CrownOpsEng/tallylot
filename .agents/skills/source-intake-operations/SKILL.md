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
3. Review the emitted plan, profile, normalization, and issue artifacts before
   moving to the next stage.
4. Rebuild location inventory only when normalization produced wallet evidence.

## Focus

- plan before apply
- inspect artifacts between stages
- keep evidence outside the repo
