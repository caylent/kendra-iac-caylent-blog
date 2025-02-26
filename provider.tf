provider "aws" {
  region = "us-west-2"
  default_tags {
    tags = {
      "caylent:owner" = "kevin.nha@caylent.com"
    }
  }
}
