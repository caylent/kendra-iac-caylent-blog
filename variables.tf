variable "jira_projects" {
  description = "List of Jira project keys to index in Kendra"
  type        = list(string)

  validation {
    condition     = length(var.jira_projects) > 0
    error_message = "At least one Jira project must be specified."
  }
}

variable "jira_url" {
  description = "Base URL of the Jira instance (e.g., https://your-domain.atlassian.net)"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^https?://.*", var.jira_url))
    error_message = "Jira URL must be a valid HTTP/HTTPS URL."
  }
}

variable "jira_token" {
  description = "Jira API token for authentication"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.jira_token) > 0
    error_message = "Jira API token cannot be empty."
  }
}

variable "jira_user" {
  description = "Jira user email address for authentication"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.jira_user))
    error_message = "Jira user must be a valid email address."
  }
}
