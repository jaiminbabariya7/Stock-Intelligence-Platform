"""
Symbol and pipeline configuration for the Stock Intelligence Platform.

Centralises all tunable parameters so operators can configure the
pipeline without touching business logic.
"""
from __future__ import annotations
import os

# ── Symbols to stream ────────────────────────────────────────────────────────
SYMBOLS: list[str] = os.getenv(
    "WATCH_SYMBOLS",
    "AAPL,TSLA,NVDA,MSFT,GOOGL,AMZN,META,NFLX"
).upper().split(",")

# ── Pub/Sub ───────────────────────────────────────────────────────────────────
PROJECT_ID    = os.environ["GCP_PROJECT_ID"]
PUBSUB_TOPIC  = os.getenv("PUBSUB_TOPIC",  "stock-price-events")
PUBSUB_SUB    = os.getenv("PUBSUB_SUB",    "dataflow-stock-sub")

# ── BigQuery ──────────────────────────────────────────────────────────────────
BQ_DATASET      = os.getenv("BQ_DATASET",      "stock_data")
BQ_RAW_TABLE    = f"{PROJECT_ID}.{BQ_DATASET}.raw_stock_data"
BQ_FEAT_TABLE   = f"{PROJECT_ID}.{BQ_DATASET}.stock_features"
BQ_PRED_TABLE   = f"{PROJECT_ID}.{BQ_DATASET}.stock_predictions"

# ── Alpaca ────────────────────────────────────────────────────────────────────
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://stream.data.alpaca.markets")
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY_SECS", "5"))
MAX_RECONNECTS  = int(os.getenv("MAX_RECONNECTS", "10"))

# ── Feature engineering windows ───────────────────────────────────────────────
SMA_SHORT   = int(os.getenv("SMA_SHORT",   "10"))
SMA_LONG    = int(os.getenv("SMA_LONG",    "30"))
RSI_PERIOD  = int(os.getenv("RSI_PERIOD",  "14"))
VWAP_WINDOW = int(os.getenv("VWAP_WINDOW", "20"))
