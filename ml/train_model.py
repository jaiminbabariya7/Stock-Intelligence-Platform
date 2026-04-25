import numpy as np
import pandas as pd
import joblib

from google.cloud import bigquery
from statsmodels.tsa.arima.model import ARIMA
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping

PROJECT_ID = "stock-intelligence-493706"

WINDOW_SIZE = 2000
SEQ_LEN = 20
ARIMA_ORDER = (5, 1, 0)

client = bigquery.Client(project=PROJECT_ID)

# ---------------- FETCH DATA ----------------
query = """
SELECT timestamp, price
FROM stock_data.raw_stock_data
ORDER BY timestamp
"""
df = client.query(query).to_dataframe()
df = df.tail(WINDOW_SIZE)

prices = df["price"].values.reshape(-1, 1)

# ---------------- SCALER (DEFINE + FIT) ----------------
scaler = MinMaxScaler()
prices_scaled = scaler.fit_transform(prices).flatten()

# ---------------- ARIMA ----------------
arima_model = ARIMA(prices_scaled, order=ARIMA_ORDER).fit()
residuals = arima_model.resid

# ---------------- CREATE LSTM SEQUENCES ----------------
def create_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len])
    return np.array(X), np.array(y)

X, y = create_sequences(residuals, SEQ_LEN)
X = X.reshape((X.shape[0], X.shape[1], 1))

# ---------------- LSTM ----------------
lstm = Sequential([
    LSTM(50, input_shape=(SEQ_LEN, 1)),
    Dense(1)
])

lstm.compile(optimizer="adam", loss="mse")

early_stop = EarlyStopping(patience=3, restore_best_weights=True)

lstm.fit(
    X, y,
    epochs=50,
    batch_size=32,
    callbacks=[early_stop],
    verbose=1
)

# ---------------- SAVE ARTIFACTS ----------------
joblib.dump(arima_model, "ml/model/arima.pkl")
lstm.save("ml/model/lstm_model.keras")
joblib.dump(scaler, "ml/model/scaler.pkl")

print("Training complete. Models and scaler saved.")