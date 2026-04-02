"""Typer applications for the CLI surface."""

from __future__ import annotations

import typer

app = typer.Typer(help="Crypto reconciliation CLI.")
workspace_app = typer.Typer(help="Workspace operations.")
baseline_app = typer.Typer(help="Baseline operations.")
source_app = typer.Typer(help="Source operations.")
source_intake_app = typer.Typer(help="Source intake commands.")
wallet_app = typer.Typer(help="Wallet inventory operations.")
wallet_inventory_app = typer.Typer(help="Wallet inventory commands.")
output_app = typer.Typer(help="Output operations.")
output_render_app = typer.Typer(help="Output rendering commands.")
verification_app = typer.Typer(help="Verification operations.")
batch_app = typer.Typer(help="Import batch operations.")
round_app = typer.Typer(help="Round operations.")
supporting_app = typer.Typer(help="Supporting artifact operations.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(baseline_app, name="baseline")
app.add_typer(source_app, name="source")
app.add_typer(wallet_app, name="wallet")
app.add_typer(output_app, name="output")
app.add_typer(verification_app, name="verification")
app.add_typer(batch_app, name="batch")
app.add_typer(round_app, name="round")
app.add_typer(supporting_app, name="supporting")
wallet_app.add_typer(wallet_inventory_app, name="inventory")
output_app.add_typer(output_render_app, name="render")
source_app.add_typer(source_intake_app, name="intake")
