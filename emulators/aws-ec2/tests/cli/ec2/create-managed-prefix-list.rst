**Example 1: To create an IPv4 prefix list**

The following ``create-managed-prefix-list`` example creates an IPv4 prefix list with a maximum of 10 entries, and creates 2 entries in the prefix list. ::

    aws ec2 create-managed-prefix-list \
        --address-family IPv4 \
        --max-entries 10 \
        --entries Cidr=10.0.0.0/16,Description=vpc-a Cidr=10.2.0.0/16,Description=vpc-b \
        --prefix-list-name vpc-cidrs

Output::

    {
        "PrefixList": {
            "PrefixListId": "pl-0123456abcabcabc1",
            "AddressFamily": "IPv4",
            "State": "create-in-progress",
            "PrefixListArn": "arn:aws:ec2:us-west-2:123456789012:prefix-list/pl-0123456abcabcabc1",
            "PrefixListName": "vpc-cidrs",
            "MaxEntries": 10,
            "Version": 1,
            "Tags": [],
            "OwnerId": "123456789012"
        }
    }

For more information, see `Managed prefix lists <https://docs.aws.amazon.com/vpc/latest/userguide/managed-prefix-lists.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To create an IPv6 prefix list**

The following ``create-managed-prefix-list`` example creates an IPv6 prefix list with a maximum of 5 entries, and creates 2 entries in the prefix list. Note that ``--address-family`` is set to ``IPv6`` and the CIDR entries use IPv6 notation. ::

    aws ec2 create-managed-prefix-list \
        --address-family IPv6 \
        --max-entries 5 \
        --entries Cidr=2001:db8::/32,Description=ipv6-range-a Cidr=2001:db8:1::/48,Description=ipv6-range-b \
        --prefix-list-name ipv6-cidrs

Output::

    {
        "PrefixList": {
            "PrefixListId": "pl-0123456abcabcabc2",
            "AddressFamily": "IPv6",
            "State": "create-in-progress",
            "PrefixListArn": "arn:aws:ec2:us-west-2:123456789012:prefix-list/pl-0123456abcabcabc2",
            "PrefixListName": "ipv6-cidrs",
            "MaxEntries": 5,
            "Version": 1,
            "Tags": [],
            "OwnerId": "123456789012"
        }
    }

For more information, see `Managed prefix lists <https://docs.aws.amazon.com/vpc/latest/userguide/managed-prefix-lists.html>`__ in the *Amazon VPC User Guide*.
