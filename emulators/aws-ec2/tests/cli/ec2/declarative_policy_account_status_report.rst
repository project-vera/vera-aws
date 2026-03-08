**To create a managed prefix list**

The following ``create-managed-prefix-list`` example creates a managed prefix list with a maximum of 10 entries and one initial entry. ::

    aws ec2 create-managed-prefix-list \
        --address-family IPv4 \
        --max-entries 10 \
        --entries Cidr=10.0.0.0/16,Description=vpc-a \
        --prefix-list-name vpc-cidrs

Output::

    {
        "PrefixList": {
            "PrefixListId": "pl-0abcdef1234567890",
            "AddressFamily": "IPv4",
            "State": "create-in-progress",
            "PrefixListArn": "arn:aws:ec2:region:123456789012:prefix-list/pl-0abcdef1234567890",
            "PrefixListName": "vpc-cidrs",
            "MaxEntries": 10,
            "Version": 1,
            "Tags": [],
            "OwnerId": "123456789012"
        }
    }
