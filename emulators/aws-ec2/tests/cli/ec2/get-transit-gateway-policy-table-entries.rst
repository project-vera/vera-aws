**To get the entries for a transit gateway policy table**

The following ``get-transit-gateway-policy-table-entries`` example returns the entries for the specified transit gateway policy table. Each entry defines a policy rule that controls how traffic is routed based on source and destination CIDR blocks. ::

    aws ec2 get-transit-gateway-policy-table-entries \
        --transit-gateway-policy-table-id tgw-ptb-0a16f134b78668a81

Output::

    {
        "TransitGatewayPolicyTableEntries": [
            {
                "TransitGatewayPolicyRuleNumber": 1,
                "MetaData": {
                    "ProviderName": "example-provider",
                    "ProviderAccount": "123456789012"
                },
                "TargetRouteTableId": "tgw-rtb-0960981be7EXAMPLE",
                "TransitGatewayPolicyRule": {
                    "SourceCidrBlock": "10.0.0.0/8",
                    "SourcePortRange": "0-65535",
                    "DestinationCidrBlock": "192.168.0.0/16",
                    "DestinationPortRange": "0-65535",
                    "Protocol": "tcp"
                }
            }
        ]
    }

For more information, see `Transit gateway policy tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-policy-tables.html>`__ in the *Transit Gateways Guide*.
