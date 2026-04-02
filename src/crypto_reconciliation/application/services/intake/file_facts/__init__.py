"""Typed file facts used by intake routing and review decisions."""

from .capture_ids import detect_capture_id
from .inspection import inspect_intake_file
from .models import IntakeFileFacts

__all__ = ["IntakeFileFacts", "detect_capture_id", "inspect_intake_file"]
