**Example 1: To create a VPC for the public-subnet route workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.6.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-public-route-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.6.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.6.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-public-route-vpc"
                }
            ]
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet in the specified VPC and applies a Name tag. ::

    aws ec2 create-subnet \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --cidr-block 10.6.1.0/24 \
        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-public-subnet}]'

Output::

    {
        "Subnet": {
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.6.1.0/24",
            "State": "available",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-public-subnet"
                }
            ]
        }
    }

**Example 4: To create an internet gateway**

The following ``create-internet-gateway`` example creates an internet gateway and applies a Name tag. ::

    aws ec2 create-internet-gateway \
        --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-public-igw}]'

Output::

    {
        "InternetGateway": {
            "Attachments": [],
            "InternetGatewayId": "igw-0d0fb496b3EXAMPLE",
            "OwnerId": "123456789012",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-public-igw"
                }
            ]
        }
    }

**Example 5: To attach the internet gateway to the VPC**

The following ``attach-internet-gateway`` example attaches the specified internet gateway to the specified VPC. ::

    aws ec2 attach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

**Example 6: To create a route table for the VPC**

The following ``create-route-table`` example creates a route table for the specified VPC and applies a Name tag. ::

    aws ec2 create-route-table \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=my-public-route-table}]'

Output::

    {
        "RouteTable": {
            "Associations": [],
            "RouteTableId": "rtb-22574640",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "PropagatingVgws": [],
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-public-route-table"
                }
            ],
            "Routes": [
                {
                    "GatewayId": "local",
                    "DestinationCidrBlock": "10.6.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

**Example 7: To create a default route through the internet gateway**

The following ``create-route`` example adds a default route that targets the attached internet gateway. ::

    aws ec2 create-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0 \
        --gateway-id igw-0d0fb496b3EXAMPLE

Output::

    {
        "Return": true
    }

**Example 8: To associate the route table with the subnet**

The following ``associate-route-table`` example associates the route table with the specified subnet. ::

    aws ec2 associate-route-table \
        --route-table-id rtb-22574640 \
        --subnet-id subnet-0e99b93155EXAMPLE

Output::

    {
        "AssociationId": "rtbassoc-0abcdef1234567890",
        "AssociationState": {
            "State": "associated"
        }
    }

**Example 9: To describe the route table and confirm both the default route and the subnet association**

The following ``describe-route-tables`` example retrieves details about the route table to confirm that the internet route is active and that the subnet association exists. ::

    aws ec2 describe-route-tables \
        --route-table-ids rtb-22574640

Output::

    {
        "RouteTables": [
            {
                "Associations": [
                    {
                        "Main": false,
                        "RouteTableAssociationId": "rtbassoc-0abcdef1234567890",
                        "RouteTableId": "rtb-22574640",
                        "SubnetId": "subnet-0e99b93155EXAMPLE",
                        "AssociationState": {
                            "State": "associated"
                        }
                    }
                ],
                "RouteTableId": "rtb-22574640",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.6.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active"
                    },
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "GatewayId": "igw-0d0fb496b3EXAMPLE",
                        "Origin": "CreateRoute",
                        "State": "active"
                    }
                ]
            }
        ]
    }

**Example 10: To clean up the public-subnet route workflow**

The following ``disassociate-route-table`` example removes the subnet association. ::

    aws ec2 disassociate-route-table \
        --association-id rtbassoc-0abcdef1234567890

The following ``delete-route`` example removes the default route. ::

    aws ec2 delete-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0

The following ``delete-route-table`` example deletes the route table. ::

    aws ec2 delete-route-table \
        --route-table-id rtb-22574640

The following ``delete-subnet`` example deletes the subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

The following ``detach-internet-gateway`` example detaches the internet gateway from the VPC. ::

    aws ec2 detach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

The following ``delete-internet-gateway`` example deletes the detached internet gateway. ::

    aws ec2 delete-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE

The following ``delete-vpc`` example deletes the VPC after all dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE