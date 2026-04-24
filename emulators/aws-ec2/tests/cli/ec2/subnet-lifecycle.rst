**Example 1: To create a VPC for the subnet workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-subnet-workflow-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.0.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.0.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-subnet-workflow-vpc"
                }
            ]
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet in the specified VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-subnet \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --cidr-block 10.0.1.0/24 \
        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-subnet}]'

Output::

    {
        "Subnet": {
            "AvailabilityZone": "us-east-1a",
            "AvailabilityZoneId": "use1-az1",
            "AvailableIpAddressCount": 251,
            "CidrBlock": "10.0.1.0/24",
            "DefaultForAz": false,
            "MapPublicIpOnLaunch": false,
            "State": "available",
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "AssignIpv6AddressOnCreation": false,
            "Ipv6CidrBlockAssociationSet": [],
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-subnet"
                }
            ],
            "SubnetArn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-0e99b93155EXAMPLE"
        }
    }

**Example 4: To describe the subnet and confirm it is available**

The following ``describe-subnets`` example retrieves details about the subnet to confirm that it belongs to the specified VPC, that the CIDR block matches the requested value, and that the subnet is in the ``available`` state. ::

    aws ec2 describe-subnets \
        --subnet-ids subnet-0e99b93155EXAMPLE

Output::

    {
        "Subnets": [
            {
                "AvailabilityZone": "us-east-1a",
                "AvailabilityZoneId": "use1-az1",
                "AvailableIpAddressCount": 251,
                "CidrBlock": "10.0.1.0/24",
                "DefaultForAz": false,
                "MapPublicIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-0e99b93155EXAMPLE",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "OwnerId": "123456789012",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "my-subnet"
                    }
                ],
                "SubnetArn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-0e99b93155EXAMPLE",
                "EnableDns64": false,
                "Ipv6Native": false,
                "PrivateDnsNameOptionsOnLaunch": {
                    "HostnameType": "ip-name",
                    "EnableResourceNameDnsARecord": false,
                    "EnableResourceNameDnsAAAARecord": false
                }
            }
        ]
    }

**Example 5: To delete the subnet**

The following ``delete-subnet`` example deletes the specified subnet. If the command succeeds, no output is returned. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

**Example 6: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the subnet has been removed. If the command succeeds, no output is returned. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE