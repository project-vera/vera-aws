Security Group Instance Lifecycle
=================================

The following examples validate the lifecycle of creating a security group rule and then
launching an instance in a subnet with that security group attached.

**Example 1: To create a VPC**

The following ``create-vpc`` example creates the VPC used by this lifecycle. ::

    aws ec2 create-vpc \
        --cidr-block 10.34.0.0/16

Expected behavior:
- A VPC is created successfully.

**Example 2: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet for the instance launch. ::

    aws ec2 create-subnet \
        --vpc-id vpc-1234567890abcdef0 \
        --cidr-block 10.34.1.0/24

Expected behavior:
- A subnet is created successfully.

**Example 3: To create a security group in the VPC**

The following ``create-security-group`` example creates a security group for the instance. ::

    aws ec2 create-security-group \
        --group-name sg-instance-lifecycle \
        --description "security group instance lifecycle" \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- A security group is created successfully.

**Example 4: To authorize an ingress rule for the security group**

The following ``authorize-security-group-ingress`` example adds a TCP/22 rule to the
security group. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0

Expected behavior:
- The request succeeds.
- The ingress rule is stored on the security group.

**Example 5: To describe the security group and verify the rule**

The following ``describe-security-groups`` example verifies the rule was persisted. ::

    aws ec2 describe-security-groups \
        --group-ids sg-1234567890abcdef0

Expected behavior:
- The response includes the target security group.
- The response includes the TCP/22 ingress rule.

**Example 6: To run an instance in the subnet with the security group**

The following ``run-instances`` example launches an instance into the subnet with the
security group attached. ::

    aws ec2 run-instances \
        --image-id ami-1234567890abcdef0 \
        --instance-type t2.micro \
        --subnet-id subnet-1234567890abcdef0 \
        --security-group-ids sg-1234567890abcdef0 \
        --count 1

Expected behavior:
- The instance is launched successfully.
- The instance records the target security group association.

**Example 7: To describe the instance and verify the security group**

The following ``describe-instances`` example verifies the instance security group attachment. ::

    aws ec2 describe-instances \
        --instance-ids i-1234567890abcdef0

Expected behavior:
- The response includes the target instance.
- The response includes the target security group in the instance security group list.

**Example 8: To terminate the instance after validation**

The following ``terminate-instances`` example terminates the instance. ::

    aws ec2 terminate-instances \
        --instance-ids i-1234567890abcdef0

Expected behavior:
- The instance is terminated successfully.

**Example 9: To delete the security group after validation**

The following ``delete-security-group`` example removes the security group. ::

    aws ec2 delete-security-group \
        --group-id sg-1234567890abcdef0

Expected behavior:
- The security group is deleted successfully.

**Example 10: To delete the subnet after validation**

The following ``delete-subnet`` example removes the subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-1234567890abcdef0

Expected behavior:
- The subnet is deleted successfully.

**Example 11: To delete the VPC after validation**

The following ``delete-vpc`` example removes the VPC. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- The VPC is deleted successfully.