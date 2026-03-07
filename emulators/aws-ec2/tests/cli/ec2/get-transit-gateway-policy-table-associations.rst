**To get the associations for a transit gateway policy table**

The following ``get-transit-gateway-policy-table-associations`` example displays the associations for the specified transit gateway policy table. ::

    aws ec2 get-transit-gateway-policy-table-associations \
        --transit-gateway-policy-table-id tgw-ptb-0a16f134b78668a81

Output::

    {
        "Associations": [
            {
                "TransitGatewayAttachmentId": "tgw-attach-0b5968d3b6EXAMPLE",
                "ResourceId": "vpc-0065acced4EXAMPLE",
                "ResourceType": "vpc",
                "State": "associated"
            }
        ]
    }

For more information, see `Transit gateway policy tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-policy-tables.html>`__ in the *Transit Gateways Guide*.
