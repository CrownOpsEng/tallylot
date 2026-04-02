"""Binance adapter matching rules and known export headers."""

from __future__ import annotations

from crypto_reconciliation.domain.models import FileInventoryEntry

SPOT_HEADER = ("Time", "Pair", "Side", "Price", "Executed", "Amount", "Fee")
DEPOSIT_HEADER = ("Time", "Coin", "Network", "Amount", "Address", "TXID", "Status")
WITHDRAW_HEADER = ("Time", "Coin", "Network", "Amount", "Fee", "Address", "TXID", "Status")
TRANSACTION_HEADER = ("User ID", "Time", "Account", "Operation", "Coin", "Change", "Remark")
CONVERT_HEADER = ("Time", "Wallet", "Pair", "Type", "Sell", "Buy", "Price", "Inverse Price", "Date Updated", "Status")
C2C_HEADER = (
    "Order Number",
    "Created Time",
    "Order Type",
    "Asset",
    "Quantity",
    "Total Price",
    "Fiat Type",
    "Counterparty",
    "Status",
)

KNOWN_HEADERS = frozenset(
    {
        SPOT_HEADER,
        DEPOSIT_HEADER,
        WITHDRAW_HEADER,
        TRANSACTION_HEADER,
        CONVERT_HEADER,
        C2C_HEADER,
    }
)


def match_binance_inventory(source: str, inventory: tuple[FileInventoryEntry, ...]) -> int:
    """Return the adapter score for a source label and profiled inventory."""
    if "binance" in source.lower():
        return 100
    headers = {item.header for item in inventory}
    return 100 if any(header in headers for header in KNOWN_HEADERS) else 0
