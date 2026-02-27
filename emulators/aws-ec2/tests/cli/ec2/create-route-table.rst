**Example 1: To create a route table**

The following ``create-route-table`` example creates a route table for the specified VPC. ::

    aws ec2 create-route-table \
        --vpc-id vpc-a01106c2

Output::

    {
        "RouteTable": {
            "Associations": [],
            "RouteTableId": "rtb-22574640",
            "VpcId": "vpc-a01106c2",
            "PropagatingVgws": [],
            "Tags": [],
            "Routes": [
                {
                    "GatewayId": "local",
                    "DestinationCidrBlock": "10.0.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

For more information, see `Route tables <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To create a route table with a Name tag**

The following ``create-route-table`` example creates a route table and assigns it a name using ``--tag-specifications``. Tagging at creation time avoids a separate ``create-tags`` call. ::

    aws ec2 create-route-table \
        --vpc-id vpc-a01106c2 \
        --tag-specifications ResourceType=route-table,Tags=[{Key=Name,Value=my-route-table}]

Output::

    {
        "RouteTable": {
            "Associations": [],
            "RouteTableId": "rtb-22574641",
            "VpcId": "vpc-a01106c2",
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
                    "DestinationCidrBlock": "10.0.0.0/16",
                    "State": "active"
                }
            ]
        }
    }

For more information, see `Route tables <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html>`__ in the *Amazon VPC User Guide*.
