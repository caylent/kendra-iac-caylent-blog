locals {
  account_id = data.aws_caller_identity.current.account_id
  lambda_invoke_event_source = "/kendra/custom_connector_self_invoke"
}
