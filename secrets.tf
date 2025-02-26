variable "jira_user" {
  type = string
}

variable "jira_token" {
  type = string
}

resource "aws_secretsmanager_secret" "jira_secret" {
  name = "jira-secret"
}

resource "aws_secretsmanager_secret_version" "example" {
  secret_id = aws_secretsmanager_secret.jira_secret.id
  secret_string = jsonencode({
    user  = var.jira_user,
    token = var.jira_token
  })
}