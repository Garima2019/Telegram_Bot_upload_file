# handler.py - webhook Lambda (patched)
# Replaces the previous synchronous handler with an immediate-ack webhook that enqueues
# the raw Telegram update to SQS for asynchronous processing by worker.py.
import os
import json
import logging
from datetime import datetime, timezone

import boto3

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

SQS_QUEUE_URL = os.environ.get("ASYNC_QUEUE_URL")  # required
REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ENDPOINT = os.environ.get("AWS_ENDPOINT")  # optional, e.g. http://host.docker.internal:4566

boto_kwargs = {"region_name": REGION}
if AWS_ENDPOINT:
    boto_kwargs["endpoint_url"] = AWS_ENDPOINT

sqs = boto3.client("sqs", **boto_kwargs)

def lambda_handler(event, context):
    """
    Webhook entrypoint: acknowledge immediately, push the update to SQS for processing.
    This function intentionally returns 200 quickly to avoid Telegram retries / 429s.
    """
    LOG.info("Incoming event (webhook): %s", json.dumps(event)[:2000])

    body = event.get("body")
    if not body:
        # nothing to process (healthcheck possibly) - ack
        return {"statusCode": 200, "body": json.dumps({"ok": True})}

    # Try to enqueue raw update to SQS
    try:
        resp = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=body,
            MessageAttributes={
                "received_at": {
                    "DataType": "String",
                    "StringValue": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        LOG.info("Enqueued update to SQS: %s", resp.get("MessageId"))
    except Exception as e:
        LOG.exception("Failed to enqueue message to SQS: %s", e)
        # Important: still return 200 to Telegram to avoid retries.
        # Consider adding monitoring/alerting on enqueue failures.
    # Return HTTP 200 immediately
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
