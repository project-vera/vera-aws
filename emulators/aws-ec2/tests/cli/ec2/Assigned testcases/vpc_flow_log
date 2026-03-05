**To create a network ACL**

The following ``create-network-acl`` example creates a network ACL for the specified VPC. ::

    aws ec2 create-network-acl \
        --vpc-id vpc-0a60eb65b4EXAMPLE

Output::

    {
        "NetworkAcl": {
            "Associations": [],
            "Entries": [
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": true,
                    "Protocol": "all",
                    "RuleAction": "deny",
                    "RuleNumber": 32767
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": false,
                    "Protocol": "all",
                    "RuleAction": "deny",
                    "RuleNumber": 32767
                }
            ],
            "IsDefault": false,
            "Tags": [],
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "NetworkAclId": "acl-0abcdef1234567890"
        }
    }
