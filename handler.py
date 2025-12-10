# handler.py - webhook Lambda (immediate ack, enqueue raw update to SQS)
import os
import json
import logging
from datetime import datetime, timezone

import boto3

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

SQS_QUEUE_URL = os.environ.get("ASYNC_QUEUE_URL")
REGION = os.environ.get("AWS_REGION", "eu-central-1")

boto_kwargs = {"region_name": REGION}
sqs = boto3.client("sqs", **boto_kwargs)

def lambda_handler(event, context):
    LOG.info("Incoming event (webhook): %s", json.dumps(event)[:2000])

    body = event.get("body")
    if not body:
        return {"statusCode": 200, "body": json.dumps({"ok": True})}

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
        LOG.info("Enqueued update to SQS id=%s", resp.get("MessageId"))
    except Exception:
        LOG.exception("Failed enqueue to SQS; continuing to return 200 to Telegram")

    return {"statusCode": 200, "body": json.dumps({"ok": True})}
