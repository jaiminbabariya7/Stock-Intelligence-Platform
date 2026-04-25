from datetime import datetime, UTC
import time
import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery
from tensorflow.keras.models import load_model

PROJECT_ID = "stock-intelligence-493706"
TABLE_ID = "stock-intelligence-493706.stock_data.stock_predictions"

client = bigquery.Client(project=PROJECT_ID)

# Load models
arima_model = joblib.load("ml/model/arima.pkl")
lstm_model = load_model("ml/model/lstm_model.keras", compile=False)
scaler = joblib.load("ml/model/scaler.pkl")

# ---------------- STATE TRACKING ----------------
last_written = {}  # symbol -> last price/prediction


def fetch_latest_prices(limit: int = 50) -> pd.DataFrame:
    query = """
        SELECT symbol, price, timestamp
        FROM stock_data.raw_stock_data
        ORDER BY symbol, timestamp DESC
    """
    df = client.query(query).to_dataframe()
    return df.iloc[::-1].reset_index(drop=True)


def forecast_next_price(prices: np.ndarray) -> float:
    prices_scaled = scaler.transform(prices.reshape(-1, 1)).flatten()

    arima_forecast = arima_model.forecast(steps=1)[0]

    seq_len = 20
    sequence = prices_scaled[-seq_len:].reshape((1, seq_len, 1))

    lstm_correction = lstm_model.predict(sequence, verbose=0)[0][0]

    final_scaled = arima_forecast + lstm_correction
    final_price = scaler.inverse_transform([[final_scaled]])[0][0]

    return float(final_price)


def should_write(symbol, price, predicted_price):
    last = last_written.get(symbol)

    if last is None:
        return True

    price_changed = abs(last["price"] - price) > 1e-6
    prediction_changed = abs(last["predicted_price"] - predicted_price) > 1e-3

    return price_changed or prediction_changed


def write_prediction(symbol: str, price: float, predicted_price: float) -> None:
    prediction_time = datetime.now(UTC).isoformat()

    row = {
        "symbol": symbol,
        "predicted_price": predicted_price,
        "prediction_time": prediction_time,
    }

    errors = client.insert_rows_json(TABLE_ID, [row])

    if not errors:
        last_written[symbol] = {
            "price": price,
            "predicted_price": predicted_price
        }
        print(f"Inserted {symbol} at {prediction_time}")
    else:
        print("Insert error:", errors)


def main_loop():
    while True:
        try:
            df = fetch_latest_prices()

            for symbol, group in df.groupby("symbol"):
                prices = group["price"].values

                if len(prices) < 20:
                    continue

                current_price = prices[-1]
                predicted_price = forecast_next_price(prices)

                if should_write(symbol, current_price, predicted_price):
                    write_prediction(symbol, current_price, predicted_price)

        except Exception as e:
            print("Error:", str(e))

        time.sleep(1)


if __name__ == "__main__":
    main_loop()