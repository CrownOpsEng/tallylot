"""Auto-discovery for source and output adapters."""

from .registry import AdapterRegistry, build_registry

__all__ = ["AdapterRegistry", "build_registry"]
