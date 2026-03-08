**To export a Client VPN client configuration**

The following ``export-client-vpn-client-configuration`` example exports the client configuration for the specified Client VPN endpoint. ::

    aws ec2 export-client-vpn-client-configuration \
        --client-vpn-endpoint-id cvpn-endpoint-123456789123abcde

Output::

    {
        "ClientConfiguration": ""
    }
