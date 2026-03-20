**Example 1: To create a VPC for the network-interface security-group workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block. ::

    aws ec2 create-vpc \
        --cidr-block 10.8.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-eni-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.8.0.0/16",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE"
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet in the specified VPC. ::

    aws ec2 create-subnet \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --cidr-block 10.8.1.0/24 \
        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-eni-subnet}]'

Output::

    {
        "Subnet": {
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.8.1.0/24",
            "State": "available"
        }
    }

**Example 4: To create a security group in the VPC**

The following ``create-security-group`` example creates a security group in the specified VPC. ::

    aws ec2 create-security-group \
        --group-name my-eni-sg \
        --description "Security group for ENI workflow" \
        --vpc-id vpc-0a60eb65b4EXAMPLE

Output::

    {
        "GroupId": "sg-0abc1234def567890"
    }

**Example 5: To create a network interface in the subnet with the security group**

The following ``create-network-interface`` example creates a network interface in the specified subnet and attaches the specified security group. ::

    aws ec2 create-network-interface \
        --subnet-id subnet-0e99b93155EXAMPLE \
        --groups sg-0abc1234def567890 \
        --description "ENI for workflow validation"

Output::

    {
        "NetworkInterface": {
            "NetworkInterfaceId": "eni-0abc1234def567890",
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "Status": "available",
            "Groups": [
                {
                    "GroupId": "sg-0abc1234def567890",
                    "GroupName": "my-eni-sg"
                }
            ]
        }
    }

**Example 6: To describe the network interface and confirm subnet and security group relationships**

The following ``describe-network-interfaces`` example retrieves details about the network interface to confirm that it belongs to the specified subnet and VPC and references the specified security group. ::

    aws ec2 describe-network-interfaces \
        --network-interface-ids eni-0abc1234def567890

Output::

    {
        "NetworkInterfaces": [
            {
                "NetworkInterfaceId": "eni-0abc1234def567890",
                "SubnetId": "subnet-0e99b93155EXAMPLE",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "Status": "available",
                "Groups": [
                    {
                        "GroupId": "sg-0abc1234def567890",
                        "GroupName": "my-eni-sg"
                    }
                ]
            }
        ]
    }

**Example 7: To delete the network interface**

The following ``delete-network-interface`` example deletes the specified network interface. ::

    aws ec2 delete-network-interface \
        --network-interface-id eni-0abc1234def567890

**Example 8: To delete the security group**

The following ``delete-security-group`` example deletes the specified security group after the network interface has been removed. ::

    aws ec2 delete-security-group \
        --group-id sg-0abc1234def567890

**Example 9: To delete the subnet**

The following ``delete-subnet`` example deletes the specified subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

**Example 10: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE