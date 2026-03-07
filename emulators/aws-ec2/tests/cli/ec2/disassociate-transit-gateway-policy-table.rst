**To disassociate a transit gateway policy table from an attachment**

The following ``disassociate-transit-gateway-policy-table`` example disassociates the specified attachment from the transit gateway policy table. ::

    aws ec2 disassociate-transit-gateway-policy-table \
        --transit-gateway-policy-table-id tgw-ptb-0a16f134b78668a81 \
        --transit-gateway-attachment-id tgw-attach-0b5968d3b6EXAMPLE

Output::

    {
        "Association": {
            "TransitGatewayPolicyTableId": "tgw-ptb-0a16f134b78668a81",
            "TransitGatewayAttachmentId": "tgw-attach-0b5968d3b6EXAMPLE",
            "ResourceId": "vpc-0065acced4EXAMPLE",
            "ResourceType": "vpc",
            "State": "disassociated"
        }
    }

For more information, see `Transit gateway policy tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-policy-tables.html>`__ in the *Transit Gateways Guide*.
