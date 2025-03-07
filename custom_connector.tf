# --------- custom connector lambda role and policy ---------
data "aws_iam_policy_document" "custom_connector_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "iam_for_custom_connector_lambda" {
  name               = "custom-connector-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.custom_connector_assume_role.json
}

resource "aws_iam_policy" "custom_connector_lambda_policy" {
  name        = "custom-connector-lambda-policy"
  description = "IAM policy for Kendra operations"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "kendra:BatchPutDocument",
          "kendra:StartDataSourceSyncJob",
          "kendra:StopDataSourceSyncJob",
          "secretsmanager:GetSecretValue",
          "events:PutEvents",
          "ssm:PutParameter",
          "ssm:GetParameter"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "custom_connector_lambda_policy_attachment" {
  role       = aws_iam_role.iam_for_custom_connector_lambda.name
  policy_arn = aws_iam_policy.custom_connector_lambda_policy.arn
}

# --------- custom connector lambda zip ---------
locals {
  custom_connector_lambda_source_path     = "./custom_connector/src"
  custom_connector_lambda_output_zip_path = "${path.module}/custom_connector_lambda_package.zip"
}

data "archive_file" "custom_connector_lambda_zip" {
  type        = "zip"
  source_dir  = local.custom_connector_lambda_source_path
  output_path = local.custom_connector_lambda_output_zip_path
}

# --------- custom connector lambda ---------
resource "aws_lambda_function" "custom_connector_lambda" {
  function_name    = "custom-connector-lambda"
  handler          = "main.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.iam_for_custom_connector_lambda.arn
  filename         = data.archive_file.custom_connector_lambda_zip.output_path
  source_code_hash = data.archive_file.custom_connector_lambda_zip.output_base64sha256
  timeout          = 600
  memory_size      = 1024
  environment {
    variables = {
      CUSTOM_CONNECTOR_SELF_INVOKE_EVENT_SOURCE = local.lambda_invoke_event_source
      LAST_CRAWLED_SSM_NAME                     = aws_ssm_parameter.jira_last_crawled.name
      JIRA_SECRET_NAME                          = aws_secretsmanager_secret.jira_secret.name
      JIRA_URL                                  = var.jira_url
      JIRA_PROJECTS                             = join(",", var.jira_projects)
    }
  }
}

# --------- custom connector lambda invoke config ---------
resource "aws_lambda_function_event_invoke_config" "custom_connector_invoke_config" {
  function_name          = aws_lambda_function.custom_connector_lambda.function_name
  maximum_retry_attempts = 0
}