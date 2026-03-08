**To create a customer gateway**

The following ``create-customer-gateway`` example creates a customer gateway with the specified IP address and ASN. ::

    aws ec2 create-customer-gateway \
        --type ipsec.1 \
        --public-ip 12.1.2.3 \
        --bgp-asn 65534

Output::

    {
        "CustomerGateway": {
            "BgpAsn": "65534",
            "CustomerGatewayId": "cgw-0abcdef1234567890",
            "IpAddress": "12.1.2.3",
            "State": "available",
            "Type": "ipsec.1",
            "Tags": []
        }
    }
