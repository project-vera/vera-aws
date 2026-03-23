# Configure the AWS provider (endpoint set by terlocal when running against Vera)
provider "aws" {
  region = "us-east-1"

  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}

# VPC and subnet for the instance
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "vera-tf-instance-vpc"
  }
}

resource "aws_subnet" "main" {
  vpc_id            = "${aws_vpc.main.id}"
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "vera-tf-instance-subnet"
  }
}

# Security group for the instance
resource "aws_security_group" "instance" {
  name        = "vera-tf-instance-sg"
  description = "Security group for Vera Terraform test instance"
  vpc_id      = "${aws_vpc.main.id}"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "vera-tf-instance-sg"
  }
}

# EC2 instance in VPC
resource "aws_instance" "example" {
  ami                    = "ami-785db401"
  instance_type          = "t2.micro"
  subnet_id              = "${aws_subnet.main.id}"
  vpc_security_group_ids = ["${aws_security_group.instance.id}"]

  tags = {
    Name = "vera-tf-test-instance"
  }
}

output "instance_id" {
  value = "${aws_instance.example.id}"
}

output "private_ip" {
  value = "${aws_instance.example.private_ip}"
}
