**Example 1: To create an ingress network ACL entry for IPv4 traffic**

The following ``create-network-acl-entry`` example creates an ingress rule in the specified network ACL that allows UDP traffic from any IPv4 address on port 53 (DNS). ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 100 \
        --protocol udp \
        --port-range From=53,To=53 \
        --cidr-block 0.0.0.0/0 \
        --rule-action allow

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To create an ingress network ACL entry for IPv6 traffic**

The following ``create-network-acl-entry`` example creates an ingress rule that allows TCP traffic from any IPv6 address on port 80 (HTTP). ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 120 \
        --protocol tcp \
        --port-range From=80,To=80 \
        --ipv6-cidr-block ::/0 \
        --rule-action allow

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 3: To create an egress network ACL entry for IPv4 traffic**

The following ``create-network-acl-entry`` example creates an egress rule that allows outbound TCP traffic to any IPv4 address on port 443 (HTTPS). ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --egress \
        --rule-number 100 \
        --protocol tcp \
        --port-range From=443,To=443 \
        --cidr-block 0.0.0.0/0 \
        --rule-action allow

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 4: To create an egress network ACL entry for IPv6 traffic**

The following ``create-network-acl-entry`` example creates an egress rule that allows outbound TCP traffic to any IPv6 address on port 443 (HTTPS). ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --egress \
        --rule-number 120 \
        --protocol tcp \
        --port-range From=443,To=443 \
        --ipv6-cidr-block ::/0 \
        --rule-action allow

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 5: To create an ingress deny rule**

The following ``create-network-acl-entry`` example creates an ingress rule that denies all traffic from the specified IPv4 CIDR block. Using a lower rule number (50) gives it higher priority than any allow rules with higher numbers, ensuring the block takes effect first. ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 50 \
        --protocol -1 \
        --cidr-block 203.0.113.0/24 \
        --rule-action deny

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.

**Example 6: To create an egress deny rule**

The following ``create-network-acl-entry`` example creates an egress rule that denies all outbound TCP traffic on port 25 (SMTP) to any IPv4 address, which is commonly used to prevent instances from sending spam. ::

    aws ec2 create-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --egress \
        --rule-number 50 \
        --protocol tcp \
        --port-range From=25,To=25 \
        --cidr-block 0.0.0.0/0 \
        --rule-action deny

This command produces no output.

For more information, see `Control traffic to subnets using network ACLs <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.
