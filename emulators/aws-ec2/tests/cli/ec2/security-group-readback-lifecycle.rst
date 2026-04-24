Security Group Readback Lifecycle
=================================

The following examples validate that security group rules can be written and then read back
through describe APIs. This lifecycle focuses on the path:

create VPC -> create security group -> authorize rule -> describe rule state -> cleanup

**Example 1: To create a VPC for security group readback checks**

The following ``create-vpc`` example creates a VPC for subsequent security group operations. ::

    aws ec2 create-vpc \
        --cidr-block 10.31.0.0/16

Expected behavior:
- A VPC is created and returns a VPC ID.

**Example 2: To create a security group inside the VPC**

The following ``create-security-group`` example creates a security group in the VPC. ::

    aws ec2 create-security-group \
        --group-name sg-readback \
        --description "security group readback lifecycle" \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- A security group is created and returns a group ID.

**Example 3: To authorize an ingress rule in the security group**

The following ``authorize-security-group-ingress`` example adds a TCP/22 rule. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0

Expected behavior:
- The request succeeds.
- The ingress rule is stored on the security group.

**Example 4: To describe the security group and verify the rule**

The following ``describe-security-groups`` example reads back the security group definition. ::

    aws ec2 describe-security-groups \
        --group-ids sg-1234567890abcdef0

Expected behavior:
- The response includes the security group.
- The response includes an ingress permission with:
  - protocol ``tcp``
  - from port ``22``
  - to port ``22``
  - CIDR ``0.0.0.0/0``

**Example 5: To describe the security group rules directly**

The following ``describe-security-group-rules`` example reads back the individual rule objects. ::

    aws ec2 describe-security-group-rules

Expected behavior:
- The response includes a security group rule associated with the target group ID.
- The response includes:
  - ``GroupId = sg-1234567890abcdef0``
  - ``IsEgress = false``
  - ``IpProtocol = tcp``
  - ``FromPort = 22``
  - ``ToPort = 22``
  - ``CidrIpv4 = 0.0.0.0/0``

**Example 6: To delete the security group after validation**

The following ``delete-security-group`` example removes the security group after readback
checks complete. ::

    aws ec2 delete-security-group \
        --group-id sg-1234567890abcdef0

Expected behavior:
- The security group is deleted successfully.

**Example 7: To delete the VPC after validation**

The following ``delete-vpc`` example removes the VPC after the security group is deleted. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- The VPC is deleted successfully.