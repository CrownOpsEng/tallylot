"""CLI entrypoints."""

from . import checkpoint, output, reconciliation, source, workspace
from .apps import app

REGISTERED_COMMAND_MODULES = (
    checkpoint,
    output,
    reconciliation,
    source,
    workspace,
)

__all__ = ["app"]
