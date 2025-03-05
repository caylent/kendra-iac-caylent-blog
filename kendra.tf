# --------- IAM Roles and Policies ---------
data "aws_iam_policy_document" "kendra_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["kendra.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "kendra_role" {
  name               = "kendra-role"
  path               = "/service-role/"
  assume_role_policy = data.aws_iam_policy_document.kendra_assume_role.json
  description        = "IAM role for Kendra index and data source operations"
}

resource "aws_iam_policy" "kendra_policy" {
  name        = "kendra-policy"
  path        = "/service-role/"
  description = "Policy for Kendra to access CloudWatch logs and metrics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = { "cloudwatch:namespace" = "AWS/Kendra" }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups",
          "logs:CreateLogGroup",
          "logs:DescribeLogStreams",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/kendra/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kendra_policy_attachment" {
  role       = aws_iam_role.kendra_role.name
  policy_arn = aws_iam_policy.kendra_policy.arn
}

# --------- Kendra Index ---------
resource "aws_kendra_index" "this" {
  name        = "rag-chatbot-index"
  description = "Kendra index for RAG chatbot"
  edition     = "DEVELOPER_EDITION"
  role_arn    = aws_iam_role.kendra_role.arn
}

# --------- Jira Data Source ---------
resource "aws_kendra_data_source" "custom_jira" {
  index_id    = aws_kendra_index.this.id
  name        = "custom-jira"
  description = "Custom Kendra connector for Jira integration"
  type        = "CUSTOM"
}