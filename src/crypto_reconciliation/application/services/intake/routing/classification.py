"""Source-folder classification rules for intake routing."""

from __future__ import annotations

from crypto_reconciliation.application.services.intake.file_facts import IntakeFileFacts

SOURCE_FOLDER_HINTS = (
    ("wealthsimple", "wealthsimple"),
    ("coinbase", "coinbase"),
    ("binance", "binance"),
    ("crypto.com", "crypto_com"),
    ("crypto_com", "crypto_com"),
    ("shakepay", "shakepay"),
    ("ledger", "ledger_live"),
    ("near", "near"),
    ("gtrade", "gtrade"),
    ("state logs", "evm_wallet"),
    ("wallet state", "evm_wallet"),
    ("etherscan", "evm_explorer"),
    ("arbiscan", "evm_explorer"),
    ("polygonscan", "evm_explorer"),
    ("bsc", "evm_explorer"),
    ("evm", "evm_explorer"),
)
HEADER_SOURCE_HINTS = (
    ("pair,coin,date,amount,type,status", "binance"),
    ("pair,coin,amount,time,interest type", "binance"),
    ("date(utc),pair,side,price,executed,amount,fee", "binance"),
    ("portfolio,type,time,amount,balance,amount/balance unit", "coinbase"),
)


def detect_source_folder(relative_path: str, facts: IntakeFileFacts) -> str:
    lower_path = relative_path.lower()
    for hint, source_folder in SOURCE_FOLDER_HINTS:
        if hint in lower_path:
            return source_folder
    if facts.header:
        normalized_header = ",".join(facts.header).strip().lower()
        for header_hint, source_folder in HEADER_SOURCE_HINTS:
            if header_hint in normalized_header:
                return source_folder
    return "unclassified"
