"""Typer applications for the CLI surface."""

from __future__ import annotations

import typer

app = typer.Typer(help="Portfolio normalization and reconciliation CLI.")
workspace_app = typer.Typer(help="Workspace operations.")
source_app = typer.Typer(help="Source operations.")
source_intake_app = typer.Typer(help="Source intake commands.")
checkpoint_app = typer.Typer(help="Checkpoint and evidence operations.")
output_app = typer.Typer(help="Output operations.")
output_render_app = typer.Typer(help="Output rendering commands.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(source_app, name="source")
app.add_typer(checkpoint_app, name="checkpoint")
app.add_typer(output_app, name="output")
output_app.add_typer(output_render_app, name="render")
source_app.add_typer(source_intake_app, name="intake")
