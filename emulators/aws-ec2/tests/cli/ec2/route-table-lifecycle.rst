**Example 1: To create a VPC for the route table workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.2.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-route-table-workflow-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.2.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.2.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-route-table-workflow-vpc"
                }
            ]
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a route table for the VPC**

The following ``create-route-table`` example creates a route table for the specified VPC and applies a Name tag. ::

    aws ec2 create-route-table \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=my-route-table}]'

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
                    "Value": "my-route-table"
                }
            ],
            "Routes": [
                {
                    "GatewayId": "local",
                    "DestinationCidrBlock": "10.2.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

**Example 4: To describe the route table and confirm its settings**

The following ``describe-route-tables`` example retrieves details about the route table to confirm that it belongs to the specified VPC and that the local route is in the ``active`` state. ::

    aws ec2 describe-route-tables \
        --route-table-ids rtb-22574640

Output::

    {
        "RouteTables": [
            {
                "Associations": [],
                "PropagatingVgws": [],
                "RouteTableId": "rtb-22574640",
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.2.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active"
                    }
                ],
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "my-route-table"
                    }
                ],
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "OwnerId": "123456789012"
            }
        ]
    }

**Example 5: To delete the route table**

The following ``delete-route-table`` example deletes the specified route table. If the command succeeds, no output is returned. ::

    aws ec2 delete-route-table \
        --route-table-id rtb-22574640

**Example 6: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the route table has been removed. If the command succeeds, no output is returned. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE