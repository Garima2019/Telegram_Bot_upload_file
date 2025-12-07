# main.tf - LocalStack-targeted S3 + SQS + IAM policy + Lambda functions + Event Source Mapping
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
    iam      = "http://localhost:4566"
    lambda   = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
  }
}

# NOTE: All variables are declared in variables.tf

# S3 bucket for media
resource "aws_s3_bucket" "bot_media" {
  bucket        = var.s3_bucket_name
  acl           = "private"
  force_destroy = true
  tags = {
    Name = "bot-media"
  }
}

# SQS queue for async processing
resource "aws_sqs_queue" "bot_queue" {
  name                       = var.sqs_queue_name
  visibility_timeout_seconds = 60
  message_retention_seconds  = 86400
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "bot-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM policy document
data "aws_iam_policy_document" "lambda_policy_doc" {
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.bot_media.arn,
      "${aws_s3_bucket.bot_media.arn}/*"
    ]
  }

  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.bot_queue.arn]
  }

  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem"
    ]
    resources = ["arn:aws:dynamodb:us-east-1:000000000000:table/${var.ddb_table_name}"]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name   = "bot-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "attach_lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Lambda function: webhook
resource "aws_lambda_function" "webhook" {
  filename         = var.webhook_lambda_zip
  function_name    = "bot-webhook"
  role             = aws_iam_role.lambda_exec.arn
  handler          = var.lambda_handler_webhook
  runtime          = var.lambda_runtime
  timeout          = 10
  memory_size      = 256

  environment {
    variables = {
      ASYNC_QUEUE_URL = aws_sqs_queue.bot_queue.id
      AWS_REGION      = var.aws_region
      AWS_ENDPOINT    = var.aws_endpoint
    }
  }
}

# Lambda function: worker
resource "aws_lambda_function" "worker" {
  filename         = var.worker_lambda_zip
  function_name    = "bot-worker"
  role             = aws_iam_role.lambda_exec.arn
  handler          = var.lambda_handler_worker
  runtime          = var.lambda_runtime
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.bot_media.bucket
      DDB_TABLE_NAME     = var.ddb_table_name
      TELEGRAM_BOT_TOKEN = var.telegram_bot_token
      AWS_REGION         = var.aws_region
      AWS_ENDPOINT       = var.aws_endpoint
    }
  }
}

# Event Source Mapping: SQS -> Worker Lambda
resource "aws_lambda_event_source_mapping" "sqs_to_worker" {
  event_source_arn = aws_sqs_queue.bot_queue.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 5
  enabled          = true
}

# Outputs
output "s3_bucket" {
  value = aws_s3_bucket.bot_media.bucket
}

output "sqs_queue_url" {
  value = aws_sqs_queue.bot_queue.id
}

output "sqs_queue_arn" {
  value = aws_sqs_queue.bot_queue.arn
}

output "webhook_lambda_name" {
  value = aws_lambda_function.webhook.function_name
}

output "worker_lambda_name" {
  value = aws_lambda_function.worker.function_name
}
