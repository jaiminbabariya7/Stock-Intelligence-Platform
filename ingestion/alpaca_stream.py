import os
import json
import logging
from datetime import datetime, UTC

from google.cloud import pubsub_v1
from alpaca.data.live import StockDataStream

from symbol_config import SYMBOLS

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# -----------------------------------------------------------------------------
# Environment variables (NO hardcoding keys)
# -----------------------------------------------------------------------------
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise ValueError("Alpaca API keys not set in environment variables")

# -----------------------------------------------------------------------------
# Pub/Sub setup
# -----------------------------------------------------------------------------
PROJECT_ID = "stock-intelligence-493706"
TOPIC_ID = "stock-stream"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

# -----------------------------------------------------------------------------
# Alpaca Live Stream Client (WebSocket)
# -----------------------------------------------------------------------------
stream = StockDataStream(API_KEY, SECRET_KEY)


def publish_to_pubsub(message: dict) -> None:
    """Publish trade event to Pub/Sub."""
    try:
        publisher.publish(
            topic_path,
            json.dumps(message).encode("utf-8")
        )
        logging.info(f"Published: {message['symbol']} | {message['price']}")
    except Exception as e:
        logging.error(f"Pub/Sub publish failed: {e}")


# -----------------------------------------------------------------------------
# Trade event handler (called for EVERY trade in real time)
# -----------------------------------------------------------------------------
async def trade_handler(trade):
    """
    This function is triggered automatically by Alpaca
    every time a trade happens for subscribed symbols.
    """

    message = {
        "symbol": trade.symbol,
        "price": float(trade.price),
        "volume": int(trade.size),
        "timestamp": datetime.now(UTC).timestamp(),
    }

    publish_to_pubsub(message)


# -----------------------------------------------------------------------------
# Main runner with auto-reconnect
# -----------------------------------------------------------------------------
def main():
    logging.info("Starting Alpaca live trade stream...")
    logging.info(f"Subscribing to symbols: {SYMBOLS}")

    stream.subscribe_trades(trade_handler, *SYMBOLS)

    try:
        stream.run()
    except Exception as e:
        logging.error(f"Stream crashed: {e}")
        logging.info("Reconnecting to Alpaca stream...")
        main()  # auto-reconnect


if __name__ == "__main__":
    main()