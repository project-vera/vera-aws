**Example 1: To create a VPC for the subnet-route-table association workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.3.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-subnet-association-workflow-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.3.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.3.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-subnet-association-workflow-vpc"
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
        --cidr-block 10.3.1.0/24 \
        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-associated-subnet}]'

Output::

    {
        "Subnet": {
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.3.1.0/24",
            "State": "available",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-associated-subnet"
                }
            ]
        }
    }

**Example 4: To create a route table in the VPC**

The following ``create-route-table`` example creates a route table for the specified VPC and applies a Name tag. ::

    aws ec2 create-route-table \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=my-associated-route-table}]'

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
                    "Value": "my-associated-route-table"
                }
            ],
            "Routes": [
                {
                    "GatewayId": "local",
                    "DestinationCidrBlock": "10.3.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

**Example 5: To associate the route table with the subnet**

The following ``associate-route-table`` example associates the specified route table with the specified subnet. ::

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

**Example 6: To describe the route table and confirm the subnet association**

The following ``describe-route-tables`` example retrieves details about the route table to confirm that the subnet association was created successfully. ::

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
                "PropagatingVgws": [],
                "RouteTableId": "rtb-22574640",
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.3.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active"
                    }
                ],
                "VpcId": "vpc-0a60eb65b4EXAMPLE"
            }
        ]
    }

**Example 7: To disassociate the route table from the subnet**

The following ``disassociate-route-table`` example removes the subnet association from the route table. ::

    aws ec2 disassociate-route-table \
        --association-id rtbassoc-0abcdef1234567890

**Example 8: To delete the subnet**

The following ``delete-subnet`` example deletes the specified subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

**Example 9: To delete the route table**

The following ``delete-route-table`` example deletes the specified route table. ::

    aws ec2 delete-route-table \
        --route-table-id rtb-22574640

**Example 10: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE