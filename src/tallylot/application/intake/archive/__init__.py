"""Archive-aware filesystem and ZIP scanning seams for intake."""

from .models import ScanIssue, ScannedFile, ScannedTree
from .scan import (
    MAX_ARCHIVE_DEPTH,
    MAX_ARCHIVE_FILE_SIZE_BYTES,
    MAX_ARCHIVE_MEMBER_COUNT,
    MAX_ARCHIVE_MEMBER_SIZE_BYTES,
    MAX_ARCHIVE_TOTAL_EXPANDED_BYTES,
    SUPPORTED_ARCHIVE_SUFFIXES,
    SUPPORTED_ZIP_COMPRESSIONS,
    UNSUPPORTED_ARCHIVE_SUFFIXES,
    scanned_tree_files,
)

__all__ = [
    "MAX_ARCHIVE_DEPTH",
    "MAX_ARCHIVE_FILE_SIZE_BYTES",
    "MAX_ARCHIVE_MEMBER_COUNT",
    "MAX_ARCHIVE_MEMBER_SIZE_BYTES",
    "MAX_ARCHIVE_TOTAL_EXPANDED_BYTES",
    "SUPPORTED_ARCHIVE_SUFFIXES",
    "SUPPORTED_ZIP_COMPRESSIONS",
    "UNSUPPORTED_ARCHIVE_SUFFIXES",
    "ScanIssue",
    "ScannedFile",
    "ScannedTree",
    "scanned_tree_files",
]
