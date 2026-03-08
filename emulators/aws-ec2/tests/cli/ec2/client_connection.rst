**To describe Client VPN connections**

The following ``describe-client-vpn-connections`` example describes the connections to the specified Client VPN endpoint. ::

    aws ec2 describe-client-vpn-connections \
        --client-vpn-endpoint-id cvpn-endpoint-123456789123abcde

Output::

    {
        "Connections": []
    }
