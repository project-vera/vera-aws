**Example 1: To create a security group for EC2-Classic**

The following ``create-security-group`` example creates a security group named ``MySecurityGroup`` for EC2-Classic. Note: EC2-Classic was retired in August 2022 and is no longer available for new accounts. ::

    aws ec2 create-security-group \
        --group-name MySecurityGroup \
        --description "My security group"

Output::

    {
        "GroupId": "sg-903004f8"
    }

For more information, see `Amazon EC2 security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To create a security group for a VPC**

The following ``create-security-group`` example creates a security group named ``MySecurityGroup`` for the specified VPC. ::

    aws ec2 create-security-group \
        --group-name MySecurityGroup \
        --description "My security group" \
        --vpc-id vpc-1a2b3c4d

Output::

    {
        "GroupId": "sg-903004f8"
    }

For more information, see `Amazon EC2 security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.

**Example 3: To create a security group with tags**

The following ``create-security-group`` example creates a security group in the specified VPC and assigns it a name and environment tag using ``--tag-specifications``. The tags are reflected in the output. ::

    aws ec2 create-security-group \
        --group-name MySecurityGroup \
        --description "My security group" \
        --vpc-id vpc-1a2b3c4d \
        --tag-specifications ResourceType=security-group,Tags=[{Key=Name,Value=my-sg},{Key=Environment,Value=production}]

Output::

    {
        "GroupId": "sg-1234567890abcdef0",
        "Tags": [
            {
                "Key": "Name",
                "Value": "my-sg"
            },
            {
                "Key": "Environment",
                "Value": "production"
            }
        ]
    }

For more information, see `Amazon EC2 security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.
