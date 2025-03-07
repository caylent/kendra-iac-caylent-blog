# --------- custom connector scheduler role and policy ---------
data "aws_iam_policy_document" "custom_connector_scheduler_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_policy" "custom_connector_scheduler_policy" {
  name        = "custom-connector-scheduler-policy"
  description = "Policy to allow custom connector scheduler to invoke Lambda"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "lambda:InvokeFunction"
        Effect   = "Allow"
        Resource = "${aws_lambda_function.custom_connector_lambda.arn}"
      }
    ]
  })
}

resource "aws_iam_role" "iam_for_custom_connector_scheduler" {
  name               = "custom-connector-scheduler-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.custom_connector_scheduler_assume_role.json
}

resource "aws_iam_role_policy_attachment" "scheduler_policy_attachment" {
  role       = aws_iam_role.iam_for_custom_connector_scheduler.name
  policy_arn = aws_iam_policy.custom_connector_scheduler_policy.arn
}

# --------- custom connector self invoke rule and target ---------
resource "aws_scheduler_schedule" "jira_schedule" {
  name                = "jira"
  description         = "Sync schedule for Jira - runs at 12 AM PT every weekday"
  schedule_expression = "cron(0 8 ? * MON-FRI *)" # 8 AM UTC corresponds to 12 AM PT
  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }
  target {
    arn      = aws_lambda_function.custom_connector_lambda.arn
    role_arn = aws_iam_role.iam_for_custom_connector_scheduler.arn
    input = jsonencode({
      detail = {
        data_source_name = "jira"
        data_source_id   = "${aws_kendra_data_source.custom_jira.data_source_id}"
        index_id         = "${aws_kendra_index.this.id}"
      }
    })
    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}

resource "aws_cloudwatch_event_rule" "custom_connector_self_invoke_rule" {
  name        = "custom-connector-self-invoke-rule"
  description = "Rule to re-trigger the same Lambda function"
  event_pattern = jsonencode({
    source = ["${local.lambda_invoke_event_source}"]
  })
}

resource "aws_cloudwatch_event_target" "self_invoke_target" {
  rule = aws_cloudwatch_event_rule.custom_connector_self_invoke_rule.name
  arn  = aws_lambda_function.custom_connector_lambda.arn
  retry_policy {
    maximum_retry_attempts       = 0
    maximum_event_age_in_seconds = 60
  }
}

resource "aws_lambda_permission" "custom_connector_self_invoke_permission" {
  statement_id  = "AllowCloudWatchEventsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.custom_connector_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.custom_connector_self_invoke_rule.arn
}
