**Example 1: To create a network ACL**

The following ``create-network-acl`` example creates a network ACL for the specified VPC. AWS automatically adds two default deny-all entries (rule 32767) — one for ingress and one for egress — which cannot be removed. ::

    aws ec2 create-network-acl \
        --vpc-id vpc-a01106c2

Output::

    {
        "NetworkAcl": {
            "Associations": [],
            "NetworkAclId": "acl-5fb85d36",
            "VpcId": "vpc-a01106c2",
            "Tags": [],
            "Entries": [
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": true,
                    "RuleAction": "deny"
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": false,
                    "RuleAction": "deny"
                }
            ],
            "IsDefault": false
        }
    }

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To create a network ACL with a Name tag**

The following ``create-network-acl`` example creates a network ACL and assigns it a name tag at creation time using ``--tag-specifications``. The tag is reflected in the ``Tags`` field of the output. ::

    aws ec2 create-network-acl \
        --vpc-id vpc-a01106c2 \
        --tag-specifications ResourceType=network-acl,Tags=[{Key=Name,Value=my-network-acl}]

Output::

    {
        "NetworkAcl": {
            "Associations": [],
            "NetworkAclId": "acl-0e968f94EXAMPLE",
            "VpcId": "vpc-a01106c2",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-network-acl"
                }
            ],
            "Entries": [
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": true,
                    "RuleAction": "deny"
                },
                {
                    "CidrBlock": "0.0.0.0/0",
                    "RuleNumber": 32767,
                    "Protocol": "-1",
                    "Egress": false,
                    "RuleAction": "deny"
                }
            ],
            "IsDefault": false
        }
    }

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.
