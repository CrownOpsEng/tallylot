"""Typed intake routing rules."""

from .classification import detect_source_folder
from .models import IntakeRoute
from .service import route_intake_file

__all__ = ["IntakeRoute", "detect_source_folder", "route_intake_file"]
