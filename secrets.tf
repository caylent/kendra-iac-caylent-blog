resource "aws_secretsmanager_secret" "jira_secret" {
  name = "jira-secret"
}

resource "aws_secretsmanager_secret_version" "jira_secret_version" {
  secret_id = aws_secretsmanager_secret.jira_secret.id
  secret_string = jsonencode({
    jiraId  = var.jira_user,
    jiraCredential = var.jira_token
  })
}

data "aws_kms_key" "secrets_manager" {
  key_id = "alias/aws/secretsmanager"
}