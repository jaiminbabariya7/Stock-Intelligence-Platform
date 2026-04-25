from flask import Flask, render_template, jsonify
from google.cloud import bigquery
import os

app = Flask(__name__)

PROJECT_ID = "stock-intelligence-493706"
client = bigquery.Client(project=PROJECT_ID)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search/<symbol>")
def search(symbol):
    query = """
        SELECT symbol, predicted_price, prediction_time
        FROM stock_data.stock_predictions
        WHERE symbol = @symbol
        ORDER BY prediction_time DESC
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("symbol", "STRING", symbol)
        ]
    )

    df = client.query(query, job_config=job_config).to_dataframe()

    if df.empty:
        return jsonify({"error": "No prediction found for this symbol"})

    row = df.iloc[0]

    return jsonify({
        "symbol": row["symbol"],
        "predicted_price": float(row["predicted_price"]),
        "prediction_time": str(row["prediction_time"])
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))