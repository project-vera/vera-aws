**Example 1: To create a Transit Gateway Connect peer with iBGP**

The following ``create-transit-gateway-connect-peer`` example creates a Connect peer using the transit gateway's own ASN (64512) for the peer. This is an iBGP session where both sides share the same autonomous system number. ::

    aws ec2 create-transit-gateway-connect-peer \
        --transit-gateway-attachment-id tgw-attach-0f0927767cEXAMPLE \
        --peer-address 172.31.1.11 \
        --inside-cidr-blocks 169.254.6.0/29

Output::

    {
        "TransitGatewayConnectPeer": {
            "TransitGatewayAttachmentId": "tgw-attach-0f0927767cEXAMPLE",
            "TransitGatewayConnectPeerId": "tgw-connect-peer-0666adbac4EXAMPLE",
            "State": "pending",
            "CreationTime": "2021-10-13T03:35:17.000Z",
            "ConnectPeerConfiguration": {
                "TransitGatewayAddress": "10.0.0.234",
                "PeerAddress": "172.31.1.11",
                "InsideCidrBlocks": [
                    "169.254.6.0/29"
                ],
                "Protocol": "gre",
                "BgpConfigurations": [
                    {
                        "TransitGatewayAsn": 64512,
                        "PeerAsn": 64512,
                        "TransitGatewayAddress": "169.254.6.2",
                        "PeerAddress": "169.254.6.1",
                        "BgpStatus": "down"
                    },
                    {
                        "TransitGatewayAsn": 64512,
                        "PeerAsn": 64512,
                        "TransitGatewayAddress": "169.254.6.3",
                        "PeerAddress": "169.254.6.1",
                        "BgpStatus": "down"
                    }
                ]
            }
        }
    }

For more information, see `Transit gateway Connect attachments and Transit Gateway Connect peers <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-connect.html>`__ in the *Transit Gateways Guide*.

**Example 2: To create a Transit Gateway Connect peer with eBGP**

The following ``create-transit-gateway-connect-peer`` example creates a Connect peer using a custom peer ASN via ``--bgp-options``. This establishes an eBGP session where the peer device belongs to a different autonomous system (65000) than the transit gateway (64512). Use eBGP when connecting to appliances or networks managed by a different organization or routing domain. ::

    aws ec2 create-transit-gateway-connect-peer \
        --transit-gateway-attachment-id tgw-attach-0f0927767cEXAMPLE \
        --peer-address 172.31.1.11 \
        --inside-cidr-blocks 169.254.6.0/29 \
        --bgp-options PeerAsn=65000

Output::

    {
        "TransitGatewayConnectPeer": {
            "TransitGatewayAttachmentId": "tgw-attach-0f0927767cEXAMPLE",
            "TransitGatewayConnectPeerId": "tgw-connect-peer-0777becbd5EXAMPLE",
            "State": "pending",
            "CreationTime": "2021-10-13T04:12:08.000Z",
            "ConnectPeerConfiguration": {
                "TransitGatewayAddress": "10.0.0.234",
                "PeerAddress": "172.31.1.11",
                "InsideCidrBlocks": [
                    "169.254.6.0/29"
                ],
                "Protocol": "gre",
                "BgpConfigurations": [
                    {
                        "TransitGatewayAsn": 64512,
                        "PeerAsn": 65000,
                        "TransitGatewayAddress": "169.254.6.2",
                        "PeerAddress": "169.254.6.1",
                        "BgpStatus": "down"
                    },
                    {
                        "TransitGatewayAsn": 64512,
                        "PeerAsn": 65000,
                        "TransitGatewayAddress": "169.254.6.3",
                        "PeerAddress": "169.254.6.1",
                        "BgpStatus": "down"
                    }
                ]
            }
        }
    }

For more information, see `Transit gateway Connect attachments and Transit Gateway Connect peers <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-connect.html>`__ in the *Transit Gateways Guide*.
