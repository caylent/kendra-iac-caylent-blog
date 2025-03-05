provider "aws" {
  region = "us-west-2"
  default_tags {
    tags = {
      "caylent:owner" = "kevin.nha@caylent.com"
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}