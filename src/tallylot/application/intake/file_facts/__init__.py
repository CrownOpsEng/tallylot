"""Typed file facts used by intake routing and review decisions."""

from .capture_labels import detect_capture_label
from .inspection import inspect_intake_file
from .models import IntakeFileFacts

__all__ = ["IntakeFileFacts", "detect_capture_label", "inspect_intake_file"]
