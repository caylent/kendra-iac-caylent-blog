variable "jira_projects" {
  type = list(string)
}

variable "jira_url" {
  type = string
  sensitive = true
}

variable "jira_token" {
  type = string
  sensitive = true
}

variable "jira_user" {
  type = string
  sensitive = true
}
