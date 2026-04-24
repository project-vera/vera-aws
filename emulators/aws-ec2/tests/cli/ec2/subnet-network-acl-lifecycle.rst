**Example 1: To create a VPC for the subnet network ACL workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block. ::

    aws ec2 create-vpc \
        --cidr-block 10.11.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-acl-vpc}]'

Output::

    {
        "Vpc": {
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.11.0.0/16",
            "State": "pending"
        }
    }

**Example 2: To wait for the VPC to become available**

The following ``wait vpc-available`` example pauses and resumes running only after it confirms that the specified VPC is available. ::

    aws ec2 wait vpc-available \
        --vpc-ids vpc-0a60eb65b4EXAMPLE

**Example 3: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet in the specified VPC. ::

    aws ec2 create-subnet \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --cidr-block 10.11.1.0/24

Output::

    {
        "Subnet": {
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.11.1.0/24",
            "State": "available"
        }
    }
    
**Example 4: To identify the subnet's current default network ACL association**

The following ``describe-network-acls`` example retrieves the current network ACL association for the subnet so that it can later be replaced. ::

    aws ec2 describe-network-acls \
        --filters Name=association.subnet-id,Values=subnet-0e99b93155EXAMPLE

Output::

    {
        "NetworkAcls": [
            {
                "NetworkAclId": "acl-0default1234567890",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "IsDefault": true,
                "Associations": [
                    {
                        "NetworkAclAssociationId": "aclassoc-0abcdef1234567890",
                        "NetworkAclId": "acl-0default1234567890",
                        "SubnetId": "subnet-0e99b93155EXAMPLE"
                    }
                ]
            }
        ]
    }

**Example 5: To create a network ACL in the VPC**

The following ``create-network-acl`` example creates a non-default network ACL in the specified VPC. ::

    aws ec2 create-network-acl \
        --vpc-id vpc-0a60eb65b4EXAMPLE

Output::

    {
        "NetworkAcl": {
            "NetworkAclId": "acl-0abc1234def567890",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "IsDefault": false,
            "Entries": [],
            "Associations": []
        }
    }

**Example 6: To associate the new network ACL with the subnet**

The following ``replace-network-acl-association`` example replaces the subnet's current default ACL association with the new network ACL. ::

    aws ec2 replace-network-acl-association \
        --association-id aclassoc-0abcdef1234567890 \
        --network-acl-id acl-0abc1234def567890

Output::

    {
        "NewAssociationId": "aclassoc-0fedcba9876543210"
    }

**Example 7: To create an inbound rule in the network ACL**

The following ``create-network-acl-entry`` example creates an inbound allow rule for TCP port 80. ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-0abc1234def567890 \
        --rule-number 100 \
        --protocol tcp \
        --port-range From=80,To=80 \
        --cidr-block 0.0.0.0/0 \
        --rule-action allow \
        --ingress

**Example 8: To describe the custom network ACL and confirm both the subnet association and the rule**

The following ``describe-network-acls`` example retrieves details about the custom network ACL to confirm that it is associated with the subnet and contains the expected rule. ::

    aws ec2 describe-network-acls \
        --network-acl-ids acl-0abc1234def567890

Output::

    {
        "NetworkAcls": [
            {
                "NetworkAclId": "acl-0abc1234def567890",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "Associations": [
                    {
                        "NetworkAclAssociationId": "aclassoc-0fedcba9876543210",
                        "NetworkAclId": "acl-0abc1234def567890",
                        "SubnetId": "subnet-0e99b93155EXAMPLE"
                    }
                ],
                "Entries": [
                    {
                        "RuleNumber": 100,
                        "Protocol": "6",
                        "RuleAction": "allow",
                        "Egress": false,
                        "CidrBlock": "0.0.0.0/0"
                    }
                ]
            }
        ]
    }

**Example 9: To restore the subnet's default network ACL association**

The following ``replace-network-acl-association`` example re-associates the subnet with its default network ACL before the custom ACL is deleted. ::

    aws ec2 replace-network-acl-association \
        --association-id aclassoc-0fedcba9876543210 \
        --network-acl-id acl-0default1234567890

Output::

    {
        "NewAssociationId": "aclassoc-0123456789abcdef0"
    }

**Example 10: To delete the custom network ACL**

The following ``delete-network-acl`` example deletes the specified custom network ACL after the subnet has been moved back to the default ACL. ::

    aws ec2 delete-network-acl \
        --network-acl-id acl-0abc1234def567890

**Example 11: To delete the subnet**

The following ``delete-subnet`` example deletes the specified subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

**Example 12: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after all dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE