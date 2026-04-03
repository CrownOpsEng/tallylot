"""Typed intake routing rules."""

from .models import IntakeRoute
from .service import route_intake_file

__all__ = ["IntakeRoute", "route_intake_file"]
