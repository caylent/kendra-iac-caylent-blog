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
}

resource "aws_iam_policy" "kendra_policy" {
  name = "${terraform.workspace}-kendra-policy"
  path = "/service-role/"
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
        Effect   = "Allow"
        Action   = ["logs:DescribeLogGroups", "logs:CreateLogGroup", "logs:DescribeLogStreams", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kendra_policy_attachment" {
  role       = aws_iam_role.kendra_role.name
  policy_arn = aws_iam_policy.kendra_policy.arn
}

resource "aws_kendra_index" "this" {
  name        = "rag-chatbot-index"
  description = "Kendra index for RAG chatbot"
  edition     = "DEVELOPER_EDITION"
  role_arn    = aws_iam_role.kendra_role.arn
}