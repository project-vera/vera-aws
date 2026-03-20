**Example 1: To create a VPC for the internet-routed workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.4.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-igw-route-workflow-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.4.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.4.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-igw-route-workflow-vpc"
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
        --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-route-igw}]'

Output::

    {
        "InternetGateway": {
            "Attachments": [],
            "InternetGatewayId": "igw-0d0fb496b3EXAMPLE",
            "OwnerId": "123456789012",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-route-igw"
                }
            ]
        }
    }

**Example 4: To attach the internet gateway to the VPC**

The following ``attach-internet-gateway`` example attaches the specified internet gateway to the specified VPC. ::

    aws ec2 attach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

**Example 5: To create a route table**

The following ``create-route-table`` example creates a route table for the specified VPC. ::

    aws ec2 create-route-table \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=my-igw-route-table}]'

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
                    "Value": "my-igw-route-table"
                }
            ],
            "Routes": [
                {
                    "GatewayId": "local",
                    "DestinationCidrBlock": "10.4.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

**Example 6: To create a default route through the internet gateway**

The following ``create-route`` example adds a default route that targets the attached internet gateway. ::

    aws ec2 create-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0 \
        --gateway-id igw-0d0fb496b3EXAMPLE

Output::

    {
        "Return": true
    }

**Example 7: To describe the route table and confirm the internet route**

The following ``describe-route-tables`` example retrieves details about the route table to confirm that the default route through the internet gateway is active. ::

    aws ec2 describe-route-tables \
        --route-table-ids rtb-22574640

Output::

    {
        "RouteTables": [
            {
                "RouteTableId": "rtb-22574640",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.4.0.0/16",
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

**Example 8: To delete the default route**

The following ``delete-route`` example removes the default route from the route table. ::

    aws ec2 delete-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0

**Example 9: To delete the route table**

The following ``delete-route-table`` example deletes the specified route table. ::

    aws ec2 delete-route-table \
        --route-table-id rtb-22574640

**Example 10: To detach and delete the internet gateway**

The following ``detach-internet-gateway`` example detaches the internet gateway from the VPC. ::

    aws ec2 detach-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE \
        --vpc-id vpc-0a60eb65b4EXAMPLE

The following ``delete-internet-gateway`` example deletes the detached internet gateway. ::

    aws ec2 delete-internet-gateway \
        --internet-gateway-id igw-0d0fb496b3EXAMPLE

**Example 11: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE