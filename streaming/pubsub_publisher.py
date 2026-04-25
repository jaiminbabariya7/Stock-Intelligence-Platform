from google.cloud import pubsub_v1
import json

PROJECT_ID = "stock-intelligence-493706"
SUBSCRIPTION_ID = "stock-stream-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)


def callback(message):
    data = json.loads(message.data.decode("utf-8"))
    print("Received:", data)
    message.ack()


stream = subscriber.subscribe(subscription_path, callback=callback)

print("Listening for messages...")

stream.result()