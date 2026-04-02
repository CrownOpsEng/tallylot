"""Core immutable domain models."""

from .adapters import AdapterCapability, AdapterManifest
from .inventory import FileInventoryEntry, WalletInventoryRecord
from .issues import IssueRecord, NormalizationReviewRecord
from .profiles import SourceProfile, VerificationExportSet
from .transactions import BalanceSnapshot, NormalizedTransaction, TransactionCategory

__all__ = [
    "AdapterCapability",
    "AdapterManifest",
    "BalanceSnapshot",
    "FileInventoryEntry",
    "IssueRecord",
    "NormalizationReviewRecord",
    "NormalizedTransaction",
    "SourceProfile",
    "TransactionCategory",
    "VerificationExportSet",
    "WalletInventoryRecord",
]
