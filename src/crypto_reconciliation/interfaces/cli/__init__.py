"""CLI entrypoints."""

from . import baseline, batch, output, rounds, source, supporting, verification, wallet, workspace
from .apps import app

REGISTERED_COMMAND_MODULES = (
    baseline,
    batch,
    output,
    rounds,
    source,
    supporting,
    verification,
    wallet,
    workspace,
)

__all__ = ["app"]
