"""CLI entrypoints."""

from . import checkpoint, output, source, workspace
from .apps import app

REGISTERED_COMMAND_MODULES = (
    checkpoint,
    output,
    source,
    workspace,
)

__all__ = ["app"]
