"""
Flask dashboard — Stock Intelligence Platform.

Serves a real-time stock monitoring UI backed by BigQuery.
Endpoints:
  GET  /                        — dashboard home
  GET  /api/symbols             — list of monitored symbols
  GET  /api/latest/<symbol>     — latest tick + prediction for a symbol
  GET  /api/history/<symbol>    — last N ticks for charting
  GET  /api/predictions         — latest predictions for all symbols
  GET  /health                  — service health
"""
from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, render_template, abort
from google.cloud import bigquery

from symbol_config import PROJECT_ID, BQ_FEAT_TABLE, BQ_PRED_TABLE, SYMBOLS

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("flask_app")

app    = Flask(__name__)
client = bigquery.Client(project=PROJECT_ID)

HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "200"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _query_df(sql: str, params: list | None = None):
    cfg = bigquery.QueryJobConfig(query_parameters=params or [])
    return client.query(sql, job_config=cfg).to_dataframe()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """Dashboard home page."""
    return render_template("index.html", symbols=SYMBOLS)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "project": PROJECT_ID})


@app.route("/api/symbols")
def get_symbols():
    """Return the list of monitored symbols."""
    return jsonify({"symbols": SYMBOLS})


@app.route("/api/latest/<symbol>")
def get_latest(symbol: str):
    """Return the most recent tick and prediction for a symbol."""
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        abort(404, description=f"Symbol {symbol} not monitored")

    # Latest tick
    tick_sql = f"""
        SELECT symbol, price, volume, vwap, price_return, tick_ts
        FROM `{BQ_FEAT_TABLE}`
        WHERE symbol = @sym
        ORDER BY tick_ts DESC LIMIT 1
    """
    pred_sql = f"""
        SELECT predicted_price, change_pct, direction, prediction_time
        FROM `{BQ_PRED_TABLE}`
        WHERE symbol = @sym
        ORDER BY prediction_time DESC LIMIT 1
    """
    sym_param = [bigquery.ScalarQueryParameter("sym", "STRING", symbol)]

    try:
        tick_df = _query_df(tick_sql, sym_param)
        pred_df = _query_df(pred_sql, sym_param)

        tick = tick_df.iloc[0].to_dict() if not tick_df.empty else {}
        pred = pred_df.iloc[0].to_dict() if not pred_df.empty else {}

        # Convert Timestamp objects to ISO strings for JSON serialisation
        for d in [tick, pred]:
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()

        return jsonify({"symbol": symbol, "tick": tick, "prediction": pred})
    except Exception as exc:
        logger.error("Query failed for %s: %s", symbol, exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/history/<symbol>")
def get_history(symbol: str):
    """Return last N ticks for a symbol (for charting)."""
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        abort(404, description=f"Symbol {symbol} not monitored")

    sql = f"""
        SELECT tick_ts, price, volume, vwap
        FROM `{BQ_FEAT_TABLE}`
        WHERE symbol = @sym
        ORDER BY tick_ts DESC LIMIT {HISTORY_LIMIT}
    """
    try:
        df = _query_df(sql, [bigquery.ScalarQueryParameter("sym", "STRING", symbol)])
        df = df.sort_values("tick_ts")
        # Convert timestamps
        df["tick_ts"] = df["tick_ts"].astype(str)
        return jsonify({"symbol": symbol, "ticks": df.to_dict(orient="records")})
    except Exception as exc:
        logger.error("History query failed for %s: %s", symbol, exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/predictions")
def get_all_predictions():
    """Return the latest prediction for every monitored symbol."""
    sql = f"""
        SELECT symbol, current_price, predicted_price, change_pct,
               direction, prediction_time
        FROM `{BQ_PRED_TABLE}`
        WHERE prediction_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY prediction_time DESC) = 1
    """
    try:
        df = _query_df(sql)
        df["prediction_time"] = df["prediction_time"].astype(str)
        return jsonify({"predictions": df.to_dict(orient="records")})
    except Exception as exc:
        logger.error("Predictions query failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=debug)
