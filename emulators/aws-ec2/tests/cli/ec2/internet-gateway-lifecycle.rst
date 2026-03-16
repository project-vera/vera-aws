**Example 1: To create a VPC for the internet gateway workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.1.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-igw-workflow-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.1.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.1.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-igw-workflow-vpc"
                }
            ]
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create an internet gateway**

The following ``create-internet-gateway`` example creates an internet gateway and applies a Name tag. ::

    aws ec2 create-internet-gateway \
        --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]'

Output::

    {
        "InternetGateway": {
            "Attachments": [],
            "InternetGatewayId": "igw-0d0fb496b3EXAMPLE",
            "OwnerId": "123456789012",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-igw"
                }
            ]
        }
    }

**Example 4: To attach the internet gateway to the VPC**

The following ``attach-internet-gateway`` example attaches the specified internet gateway to the specified VPC. If the command succeeds, no output is returned. ::

    aws ec2 attach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

**Example 5: To describe the internet gateway and confirm the attachment**

The following ``describe-internet-gateways`` example retrieves details about the internet gateway to confirm that it is attached to the specified VPC and that the attachment is in the ``available`` state. ::

    aws ec2 describe-internet-gateways \
        --internet-gateway-ids igw-0d0fb496b3EXAMPLE

Output::

    {
        "InternetGateways": [
            {
                "Attachments": [
                    {
                        "State": "available",
                        "VpcId": "vpc-0a60eb65b4EXAMPLE"
                    }
                ],
                "InternetGatewayId": "igw-0d0fb496b3EXAMPLE",
                "OwnerId": "123456789012",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "my-igw"
                    }
                ]
            }
        ]
    }

**Example 6: To detach the internet gateway from the VPC**

The following ``detach-internet-gateway`` example detaches the specified internet gateway from the specified VPC. If the command succeeds, no output is returned. ::

    aws ec2 detach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

**Example 7: To delete the internet gateway**

The following ``delete-internet-gateway`` example deletes the specified internet gateway after it has been detached from the VPC. If the command succeeds, no output is returned. ::

    aws ec2 delete-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE

**Example 8: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the internet gateway has been detached and deleted. If the command succeeds, no output is returned. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE