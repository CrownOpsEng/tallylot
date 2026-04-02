"""Shared CLI helpers."""

from __future__ import annotations

import json

import typer


def emit_response(payload: object) -> None:
    typer.echo(json.dumps(payload, default=str))
