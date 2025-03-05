locals {
  account_id                 = data.aws_caller_identity.current.account_id
  region                     = data.aws_region.current.name
  lambda_invoke_event_source = "/kendra/custom_connector_self_invoke"
}
