resource "aws_ssm_parameter" "jira_last_crawled" {
  name  = "/kendra/last_crawled/jira"
  type  = "String"
  value = "1"
  lifecycle {
    ignore_changes = [value]
  }
}
