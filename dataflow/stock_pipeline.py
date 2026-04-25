import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import argparse
import json


class TransformStock(beam.DoFn):
    def process(self, element):
        record = json.loads(element.decode("utf-8"))

        price = float(record["price"])

        yield {
            "symbol": record["symbol"],
            "price": price,
            "volume": int(record["volume"]),
            "timestamp": float(record["timestamp"]),
            #"price_category": "HIGH" if price > 200 else "LOW"
        }


def run():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input_subscription", required=True)
    parser.add_argument("--output_table", required=True)

    args, beam_args = parser.parse_known_args()

    options = PipelineOptions(
        beam_args,
        streaming=True,
        save_main_session=True
    )

    with beam.Pipeline(options=options) as p:

        (
            p
            | "Read PubSub" >> beam.io.ReadFromPubSub(
                subscription=args.input_subscription
            )
            | "Transform" >> beam.ParDo(TransformStock())
            | "Write BigQuery" >> beam.io.WriteToBigQuery(
                args.output_table,
                schema={
                    "fields": [
                        {"name": "symbol", "type": "STRING"},
                        {"name": "price", "type": "FLOAT"},
                        {"name": "volume", "type": "INTEGER"},
                        {"name": "timestamp", "type": "FLOAT"},
                       #{"name": "price_category", "type": "STRING"},
                    ]
                },
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )


if __name__ == "__main__":
    run()