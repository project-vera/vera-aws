# Configure the AWS provider (endpoint set by terlocal when running against Vera)
provider "aws" {
  region = "us-east-1"

  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}

# VPC for EC2 resources
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "vera-tf-test-vpc"
  }
}

# Public subnet in the VPC
resource "aws_subnet" "public" {
  vpc_id            = "${aws_vpc.main.id}"
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "vera-tf-test-subnet"
  }
}

# Outputs for verification
output "vpc_id" {
  value = "${aws_vpc.main.id}"
}

output "subnet_id" {
  value = "${aws_subnet.public.id}"
}
