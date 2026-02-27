**Example 1: To create an egress-only internet gateway**

The following ``create-egress-only-internet-gateway`` example creates an egress-only internet gateway for the specified VPC. ::

    aws ec2 create-egress-only-internet-gateway \
        --vpc-id vpc-0c62a468

Output::

    {
        "EgressOnlyInternetGateway": {
            "EgressOnlyInternetGatewayId": "eigw-015e0e244e24dfe8a",
            "Attachments": [
                {
                    "State": "attached",
                    "VpcId": "vpc-0c62a468"
                }
            ],
            "Tags": []
        }
    }

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To create an egress-only internet gateway with a Name tag**

The following ``create-egress-only-internet-gateway`` example creates an egress-only internet gateway and assigns it a name tag at creation time using ``--tag-specifications``. ::

    aws ec2 create-egress-only-internet-gateway \
        --vpc-id vpc-0c62a468 \
        --tag-specifications ResourceType=egress-only-internet-gateway,Tags=[{Key=Name,Value=my-eigw}]

Output::

    {
        "EgressOnlyInternetGateway": {
            "EgressOnlyInternetGatewayId": "eigw-024c1f9358EXAMPLE",
            "Attachments": [
                {
                    "State": "attached",
                    "VpcId": "vpc-0c62a468"
                }
            ],
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-eigw"
                }
            ]
        }
    }

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.
