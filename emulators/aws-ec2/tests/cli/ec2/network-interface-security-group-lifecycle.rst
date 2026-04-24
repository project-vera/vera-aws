Network Interface Security Group Lifecycle
==========================================

The following examples validate the lifecycle of attaching a security group to a network
interface and reading that relationship back through ``describe-network-interfaces``.

**Example 1: To create a VPC**

The following ``create-vpc`` example creates the VPC used by this lifecycle. ::

    aws ec2 create-vpc \
        --cidr-block 10.33.0.0/16

Expected behavior:
- A VPC is created successfully.

**Example 2: To create a subnet in the VPC**

The following ``create-subnet`` example creates a subnet for the network interface. ::

    aws ec2 create-subnet \
        --vpc-id vpc-1234567890abcdef0 \
        --cidr-block 10.33.1.0/24

Expected behavior:
- A subnet is created successfully.

**Example 3: To create a security group in the VPC**

The following ``create-security-group`` example creates a security group for later ENI
association. ::

    aws ec2 create-security-group \
        --group-name sg-eni-lifecycle \
        --description "network interface security group lifecycle" \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- A security group is created successfully.

**Example 4: To create a network interface with the security group**

The following ``create-network-interface`` example creates an ENI and attaches the security
group at creation time. ::

    aws ec2 create-network-interface \
        --subnet-id subnet-1234567890abcdef0 \
        --groups sg-1234567890abcdef0

Expected behavior:
- A network interface is created successfully.
- The network interface stores the security group association.

**Example 5: To describe the network interface and verify the security group**

The following ``describe-network-interfaces`` example reads back the ENI and verifies that
the security group relationship is present. ::

    aws ec2 describe-network-interfaces \
        --network-interface-ids eni-1234567890abcdef0

Expected behavior:
- The response includes the target ENI.
- The response includes the associated security group in the ENI group list.

**Example 6: To delete the network interface after validation**

The following ``delete-network-interface`` example removes the ENI. ::

    aws ec2 delete-network-interface \
        --network-interface-id eni-1234567890abcdef0

Expected behavior:
- The network interface is deleted successfully.

**Example 7: To delete the security group after validation**

The following ``delete-security-group`` example removes the security group. ::

    aws ec2 delete-security-group \
        --group-id sg-1234567890abcdef0

Expected behavior:
- The security group is deleted successfully.

**Example 8: To delete the subnet after validation**

The following ``delete-subnet`` example removes the subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-1234567890abcdef0

Expected behavior:
- The subnet is deleted successfully.

**Example 9: To delete the VPC after validation**

The following ``delete-vpc`` example removes the VPC. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-1234567890abcdef0

Expected behavior:
- The VPC is deleted successfully.