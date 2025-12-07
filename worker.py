# worker.py - SQS consumer Lambda
# Consumes raw Telegram updates from SQS, downloads files from Telegram (photo/document),
# uploads them to S3, and records metadata in DynamoDB.
import os
import json
import time
import urllib.request
import urllib.parse
import logging
from datetime import datetime, timezone

import boto3

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

# TELEGRAM_API_BASE = "https://api.telegram.org/bot"
TELEGRAM_API_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org/bot")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ENDPOINT = os.environ.get("AWS_ENDPOINT")  # optional for LocalStack, e.g. http://localhost:4566
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
DDB_TABLE_NAME = os.environ.get("DDB_TABLE_NAME")

boto_kwargs = {"region_name": REGION}
if AWS_ENDPOINT:
    boto_kwargs["endpoint_url"] = AWS_ENDPOINT

s3 = boto3.client("s3", **boto_kwargs)
dynamodb = boto3.resource("dynamodb", **boto_kwargs)
table = dynamodb.Table(DDB_TABLE_NAME)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def download_telegram_file(file_id: str):
    """Return (bytes, filename) by downloading from Telegram."""
    # Step1: get file path
    getfile_url = f"{TELEGRAM_API_BASE}{TELEGRAM_BOT_TOKEN}/getFile"
    params = urllib.parse.urlencode({"file_id": file_id})
    with urllib.request.urlopen(getfile_url + "?" + params, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    result = data.get("result") or {}
    file_path = result.get("file_path")
    if not file_path:
        raise RuntimeError("Telegram returned no file_path for file_id: " + file_id)
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    with urllib.request.urlopen(file_url, timeout=30) as resp:
        content = resp.read()
    filename = file_path.split("/")[-1]
    return content, filename

def s3_upload_bytes(bucket: str, key: str, data: bytes, content_type: str = None):
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    s3.put_object(Bucket=bucket, Key=key, Body=data, **extra)
    return True

def save_file_metadata(user_id: int, message_id: int, s3_key: str, filename: str, mime_type: str, telegram_file_id: str):
    item = {
        "user_id": str(user_id),
        "sort_key": f"file#{message_id}#{int(time.time())}",
        "s3_key": s3_key,
        "file_name": filename,
        "mime_type": mime_type or "",
        "telegram_file_id": telegram_file_id,
        "created_at": now_iso(),
    }
    table.put_item(Item=item)

def process_update(update: dict):
    LOG.info("Processing update: %s", json.dumps(update)[:2000])
    message = update.get("message") or update.get("edited_message") or {}
    if not message:
        LOG.info("No message in update; skipping.")
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    if not chat_id or not message_id:
        LOG.info("Missing chat_id or message_id; skipping.")
        return

    # photos
    if "photo" in message:
        photos = message["photo"]
        largest = photos[-1]
        file_id = largest.get("file_id")
        if file_id:
            try:
                content, filename = download_telegram_file(file_id)
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                s3_key = f"{chat_id}/{message_id}_{ts}_{filename}"
                s3_upload_bytes(S3_BUCKET, s3_key, content, content_type="image/jpeg")
                save_file_metadata(chat_id, message_id, s3_key, filename, "image/jpeg", file_id)
                LOG.info("Uploaded photo to s3://%s/%s", S3_BUCKET, s3_key)
            except Exception as e:
                LOG.exception("Failed to process photo: %s", e)
        return

    # document
    if "document" in message:
        doc = message["document"]
        file_id = doc.get("file_id")
        filename = doc.get("file_name") or "document"
        mime = doc.get("mime_type") or None
        if file_id:
            try:
                content, dl_filename = download_telegram_file(file_id)
                final_filename = filename or dl_filename
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                s3_key = f"{chat_id}/{message_id}_{ts}_{final_filename}"
                s3_upload_bytes(S3_BUCKET, s3_key, content, content_type=mime)
                save_file_metadata(chat_id, message_id, s3_key, final_filename, mime, file_id)
                LOG.info("Uploaded document to s3://%s/%s", S3_BUCKET, s3_key)
            except Exception as e:
                LOG.exception("Failed to process document: %s", e)
        return

    LOG.info("No photo or document found in message %s", message_id)

def lambda_handler(event, context):
    LOG.info("Worker received event: %s", json.dumps(event)[:2000])
    records = event.get("Records", [])
    for rec in records:
        body = rec.get("body")
        if not body:
            continue
        try:
            update = json.loads(body)
        except Exception:
            LOG.exception("Invalid JSON in SQS record body - skipping.")
            continue
        try:
            process_update(update)
        except Exception as e:
            LOG.exception("Error processing update: %s", e)
            # Let Lambda/SQS retry according to configuration
