🚀 Async Telegram Bot – Serverless Architecture on AWS + LocalStack

Python · Lambda · SQS · S3 · DynamoDB · Terraform · LocalStack

This project implements an asynchronous Telegram bot backend using:

AWS Lambda (webhook & worker functions)

Amazon SQS (for async job queueing)

Amazon S3 (file/media storage)

Amazon DynamoDB (metadata storage)

Terraform (infrastructure as code)

LocalStack (full local AWS simulation)

Async bot processing pipeline for photo/document uploads

Optional: Mock Telegram Server for 100% offline testing

This repo gives you a complete, production-backed pattern for scalable Telegram bot processing without blocking webhook latency.

🧠 Architecture Overview
Flow: Incoming Telegram Updates → Webhook Lambda → SQS → Worker Lambda → S3 + DynamoDB
Telegram → Webhook Lambda → SQS Queue → Worker Lambda → S3 (files)
                                                └──→ DynamoDB (metadata)

Why this design?

Webhook Lambda stays fast — it only validates the update & pushes to SQS (no blocking I/O)

Worker Lambda handles file downloads from Telegram (or mock server)

S3 stores actual media (photos, documents, videos)

DynamoDB stores metadata (user_id, file_path, timestamps, S3 keys)

Terraform builds and wires everything automatically

LocalStack enables local development without deploying to AWS

📦 Project Structure
.
├── main.tf                 # Full infrastructure (S3, SQS, Lambda, IAM, DynamoDB)
├── variables.tf            # All Terraform variables
├── terraform.tfvars        # User-specific values (bucket name, token, etc.)
├── handler.py              # Webhook Lambda: receives Telegram webhook, pushes message to SQS
├── worker.py               # Worker Lambda: consumes SQS, fetches file, uploads to S3, writes DynamoDB
├── webhook.zip             # Deployed lambda package
├── worker.zip              # Deployed lambda package
├── deploy.sh               # Linux/Mac deployment helper
├── mock_telegram.py        # Local Flask mock of Telegram's getFile + file download endpoints
├── test_runner.py          # Locally invokes worker.process_update() for offline testing
└── README.md               # You’re reading it.

🔧 Requirements
Local tools
Tool	Version
Python	3.9–3.11
Terraform	≥ 1.3
LocalStack	Latest
AWS CLI	Latest
awscli-local (awslocal)	Recommended
⚙️ Setup & Installation
1️⃣ Clone Repository
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>

2️⃣ Start LocalStack
localstack start


Verify:

curl http://localhost:4566/health

3️⃣ Configure Terraform Variables

Edit terraform.tfvars:

s3_bucket_name      = "my-bot-media"
ddb_table_name      = "my-bot-table"
telegram_bot_token  = "123456:ABCDEF-YOUR-REAL-TOKEN"


For safety, don’t commit your token.
You can also pass the token via CLI:

terraform apply -var="telegram_bot_token=YOURTOKEN"

4️⃣ Deploy Infrastructure
terraform init
terraform apply -auto-approve \
  -var="s3_bucket_name=my-bot-media" `
  -var="ddb_table_name=my-bot-table" `
  -var="telegram_bot_token=123456:ABCDEF-YOURTOKEN"


Terraform provisions:

S3 bucket

SQS queue

IAM roles/policies

Webhook Lambda

Worker Lambda

SQS → Lambda event source mapping

🧪 Local Testing Options
✔ Option A — Test With Mock Telegram Server (Recommended)

Run the mock server:

python mock_telegram.py


It exposes:

GET /bot<token>/getFile?file_id=FILE123

GET /file/bot<token>/<file_path>

Run the local worker test runner:

python test_runner.py


This:

Builds a fake Telegram update with a photo

Calls worker.process_update(update) directly

Downloads file bytes from mock_telegram

Uploads the file to S3

Writes metadata to DynamoDB

Check S3:
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-bot-media --recursive

Check DynamoDB:
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name my-bot-table

✔ Option B — Simulate Webhook → SQS → Worker

Invoke webhook lambda manually:

$body = '{ "body": "{\"message\":{\"message_id\":123, \"chat\":{\"id\":111}, \"text\":\"hello\"}}"}'
Set-Content payload.json $body

aws --endpoint-url=http://localhost:4566 lambda invoke `
  --function-name bot-webhook `
  --payload file://payload.json output.json


Check SQS:

aws --endpoint-url=http://localhost:4566 sqs receive-message --queue-url "<queue-url>"


Worker should automatically process and write logs.

🗂 DynamoDB Metadata Structure

Each file upload produces an item:

Attribute	Description
user_id	Telegram chat ID
sort_key	"file#<message_id>#<timestamp>"
telegram_file_id	ID reported by Telegram
file_name	Extracted filename
s3_key	Key in S3 bucket
created_at	ISO timestamp
📤 S3 File Structure

File uploads are organized as:

<user_id>/<timestamp>_<message_id>_<filename>


Example:

123456/2025-12-07T16-30-00_5001_testfile.png

🛠 Development Notes

LocalStack is non-strict — IAM is not enforced like AWS.

API Gateway is intentionally NOT used in this setup to avoid LocalStack inconsistencies.

Telegram file downloads are async and handled only by worker lambda.

Webhook lambda stays extremely lightweight.

🧼 Cleanup
terraform destroy -auto-approve
localstack stop

🧩 Future Enhancements

✔ Add Telegram command-handling framework
✔ Add rate-limit retry queue
✔ Add media processing (thumbnails, PDFs → images, etc.)
✔ Replace Flask mock server with pytest fixtures
✔ Deploy for real using AWS API Gateway + ACM + Route53

📄 License

MIT — free to use, modify, and deploy.
