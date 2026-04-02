#!/usr/bin/env python3

"""Shared file-family classification helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


def classify_file_family(path: Path, header: Sequence[str]) -> str:
    name = path.name.lower()
    header_lower = [column.strip().lower() for column in header]
    header_set = set(header_lower)

    def has_all(*columns: str) -> bool:
        return set(columns).issubset(header_set)

    if path.suffix.lower() == ".pdf":
        return "statement_balance_pdf"
    if has_all("type", "buy", "cur.", "sell", "fee", "exchange", "date"):
        return "cointracking_trade_table_csv"
    if has_all("type", "buy amount", "buy cur.", "sell amount", "sell cur.", "fee amount (optional)"):
        return "cointracking_import_csv"
    if has_all("id", "timestamp", "transaction type") and ("asset" in header_set or "statement" in name):
        return "custodial_all_time_csv"
    if has_all("portfolio", "trade id", "product", "side", "created at"):
        return "fills_csv"
    if has_all("portfolio", "type", "time", "amount", "balance", "amount/balance unit"):
        return "transfer_statement_csv"
    if has_all("transaction_date", "settlement_date", "account_type", "activity_type"):
        return "broker_activity_csv"
    if has_all("date", "transaction", "description", "amount", "balance", "currency"):
        return "statement_transaction_csv"
    if has_all("operation date", "operation type", "operation amount"):
        return "wallet_operation_csv"
    if has_all("date", "pair", "addr"):
        return "derivatives_report_csv"
    if has_all("deal_id", "status", "bot", "account", "bot_id", "pair"):
        return "trading_bot_deals_csv"
    if has_all("receipt no", "date", "activity", "amount", "currency", "cad amount", "cad rate"):
        return "coinberry_activity_csv"
    if has_all(
        "transaction type",
        "date",
        "amount debited",
        "debit currency",
        "amount credited",
        "credit currency",
        "buy / sell rate",
        "direction",
        "spot rate",
        "source / destination",
    ):
        return "shakepay_transactions_csv"
    if has_all("redemption date(utc)", "coin", "redemption amount", "status"):
        return "binance_staking_redemption_csv"
    if has_all("date", "time (utc)", "type", "symbol", "specification"):
        return "gemini_account_history_csv"
    if "receipt" in header_set and "deposit value" in header_set:
        return "near_receipt_csv"
    if has_all("txn hash", "direction", "token id", "contract"):
        return "near_nft_transaction_csv"
    if has_all("txn hash", "direction", "token", "contract"):
        return "near_ft_transaction_csv"
    if has_all("txn hash", "method", "deposit value", "txn fee"):
        return "near_transaction_csv"
    if has_all("user_id", "utc_time", "account", "operation", "coin", "change", "remark"):
        return "custodial_transaction_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "tokenvalue", "tokensymbol"):
        return "explorer_token_transfer_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "token id", "quantity"):
        return "explorer_nft_transfer_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "parenttxfrom", "parenttxto"):
        return "explorer_internal_transaction_csv"
    if "transaction hash" in header_set and "datetime (utc)" in header_set and any(
        column.startswith("value_in(") or column.startswith("value_out(") for column in header_lower
    ):
        return "explorer_transaction_csv"
    if has_all("txhash", "blockno", "unixtimestamp", "datetime", "from", "to"):
        return "explorer_transaction_csv"
    if has_all("type", "amount credited", "asset credited", "amount debited", "asset debited"):
        return "custodial_transaction_csv"
    if has_all("date", "type", "description", "debit", "credit"):
        return "fiat_transaction_csv"
    if has_all("timestamp (utc)", "transaction description", "currency", "amount", "transaction kind"):
        return "custodial_transaction_csv"
    if has_all("time", "wallet", "pair", "sell", "buy", "status"):
        return "convert_order_csv"
    if has_all("time", "coin", "network", "amount", "address", "txid", "status"):
        return "deposit_history_csv"
    if has_all("time", "coin", "network", "amount", "fee", "address", "txid", "status"):
        return "withdrawal_history_csv"
    if has_all("order number", "order type", "asset", "fiat type", "total price", "status"):
        return "p2p_order_csv"
    if has_all("time", "method", "spend amount", "receive amount", "fee", "price", "status", "transaction id"):
        return "fiat_buy_csv"
    if has_all("method", "amount", "price", "final amount", "created time", "status", "transaction id"):
        return "fiat_exchange_csv"
    if has_all("time", "type", "amount", "asset", "symbol", "transaction id"):
        return "futures_transaction_csv"
    if has_all("time", "pair", "side", "price", "executed", "amount", "fee"):
        return "fills_csv"
    if has_all("date(utc)", "pair", "side", "price", "executed", "amount", "fee"):
        return "binance_margin_trade_csv"
    if has_all("date(utc)", "orderno", "pair", "type", "side", "order price"):
        return "binance_margin_order_csv"
    if has_all("pair", "coin", "date", "amount", "type", "status"):
        return "binance_margin_borrow_csv"
    if has_all("pair", "coin", "amount", "time", "interest type"):
        return "binance_margin_interest_csv"
    if has_all("pair", "coin", "date", "principal amount", "interest", "total"):
        return "binance_margin_repay_csv"
    if has_all("pair", "coin", "date", "margin account (in/out)", "amount"):
        return "binance_margin_transfer_csv"
    if has_all("date", "pair", "type", "side", "average", "price", "executed", "amount", "total"):
        return "binance_margin_liquidation_csv"
    if has_all("date", "pair", "coin", "amount", "to account", "bnb deducted"):
        return "binance_margin_fee_return_csv"
    if has_all("chain", "token", "amount", "value") or "portfolio" in name:
        return "portfolio_snapshot_csv"
    if "transaction" in name and "history" in name:
        return "custodial_transaction_csv"
    return "unknown"
