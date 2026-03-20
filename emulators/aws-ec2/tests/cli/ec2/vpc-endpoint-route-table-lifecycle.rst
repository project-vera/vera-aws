**Example 1: To create a VPC for the VPC endpoint route-table workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block. ::

    aws ec2 create-vpc \
        --cidr-block 10.9.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-endpoint-vpc}]'

Output::

    {
        "Vpc": {
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.9.0.0/16",
            "State": "pending"
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a route table in the VPC**

The following ``create-route-table`` example creates a route table for the specified VPC. ::

    aws ec2 create-route-table \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=my-endpoint-route-table}]'

Output::

    {
        "RouteTable": {
            "RouteTableId": "rtb-22574640",
            "VpcId": "vpc-0a60eb65b4EXAMPLE"
        }
    }

**Example 4: To create a gateway VPC endpoint associated with the route table**

The following ``create-vpc-endpoint`` example creates a gateway VPC endpoint for the specified service and associates it with the specified route table. ::

    aws ec2 create-vpc-endpoint \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --service-name com.amazonaws.us-east-1.s3 \
        --vpc-endpoint-type Gateway \
        --route-table-ids rtb-22574640

Output::

    {
        "VpcEndpoint": {
            "VpcEndpointId": "vpce-0abc1234def567890",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "ServiceName": "com.amazonaws.us-east-1.s3",
            "VpcEndpointType": "Gateway",
            "State": "available",
            "RouteTableIds": [
                "rtb-22574640"
            ]
        }
    }

**Example 5: To describe the VPC endpoint and confirm route-table association**

The following ``describe-vpc-endpoints`` example retrieves details about the VPC endpoint to confirm that it is associated with the expected route table. ::

    aws ec2 describe-vpc-endpoints \
        --vpc-endpoint-ids vpce-0abc1234def567890

Output::

    {
        "VpcEndpoints": [
            {
                "VpcEndpointId": "vpce-0abc1234def567890",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "ServiceName": "com.amazonaws.us-east-1.s3",
                "VpcEndpointType": "Gateway",
                "State": "available",
                "RouteTableIds": [
                    "rtb-22574640"
                ]
            }
        ]
    }

**Example 6: To describe the route table after endpoint association**

The following ``describe-route-tables`` example retrieves details about the route table after the endpoint has been associated with it. ::

    aws ec2 describe-route-tables \
        --route-table-ids rtb-22574640

Output::

    {
        "RouteTables": [
            {
                "RouteTableId": "rtb-22574640",
                "VpcId": "vpc-0a60eb65b4EXAMPLE"
            }
        ]
    }

**Example 7: To delete the VPC endpoint**

The following ``delete-vpc-endpoints`` example deletes the specified VPC endpoint. ::

    aws ec2 delete-vpc-endpoints \
        --vpc-endpoint-ids vpce-0abc1234def567890

Output::

    {
        "Unsuccessful": []
    }

**Example 8: To delete the route table**

The following ``delete-route-table`` example deletes the specified route table. ::

    aws ec2 delete-route-table \
        --route-table-id rtb-22574640

**Example 9: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE