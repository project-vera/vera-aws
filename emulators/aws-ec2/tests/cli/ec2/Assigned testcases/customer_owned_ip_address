**To create DHCP options**

The following ``create-dhcp-options`` example creates DHCP options with a custom DNS server. ::

    aws ec2 create-dhcp-options \
        --dhcp-configuration "Key=domain-name-servers,Values=10.2.5.1"

Output::

    {
        "DhcpOptions": {
            "OwnerId": "123456789012",
            "Tags": [],
            "DhcpOptionsId": "dopt-0abcdef1234567890",
            "DhcpConfigurations": [
                {
                    "Key": "domain-name-servers",
                    "Values": [
                        {
                            "Value": "10.2.5.1"
                        }
                    ]
                }
            ]
        }
    }
