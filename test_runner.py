# test_runner.py
import os
import json
import time

# Ensure Python finds your worker.py in the same directory
import importlib.util
from pathlib import Path

worker_path = Path(__file__).parent / "worker.py"
spec = importlib.util.spec_from_file_location("worker", str(worker_path))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

# Config: override env vars for local test
os.environ["TELEGRAM_BOT_TOKEN"] = "TESTTOKEN"   # token string used by mock (mock ignores token content)
os.environ["TELEGRAM_API_BASE"] = "http://localhost:8080/bot"
# For LocalStack endpoints:
os.environ["AWS_ENDPOINT"] = "http://localhost:4566"
os.environ["AWS_REGION"] = "us-east-1"
# Set your S3 bucket and DynamoDB table you created with Terraform:
os.environ["S3_BUCKET_NAME"] = "my-bot-media"
os.environ["DDB_TABLE_NAME"] = "my-bot-table"

# Build a sample Telegram update that contains a photo with file_id=FILE123
update = {
    "message": {
        "message_id": 5001,
        "date": int(time.time()),
        "chat": {"id": 123456, "type": "private"},
        "from": {"id": 123456, "first_name": "Test"},
        # 'photo' array with smallest->largest; worker picks last
        "photo": [
            {"file_id": "FILE123", "file_size": 10, "width": 90, "height": 90}
        ]
    }
}

if __name__ == "__main__":
    print("Invoking worker.process_update with sample update...")
    worker.process_update(update)
    print("Done. Check S3 and DynamoDB for results.")
