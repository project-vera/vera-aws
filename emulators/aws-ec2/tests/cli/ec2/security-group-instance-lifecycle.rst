**Example 1: To create a VPC for the security-group and instance workflow**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and applies a Name tag. ::

    aws ec2 create-vpc \
        --cidr-block 10.7.0.0/16 \
        --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-sg-instance-vpc}]'

Output::

    {
        "Vpc": {
            "CidrBlock": "10.7.0.0/16",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE"
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
        --cidr-block 10.7.1.0/24 \
        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-instance-subnet}]'

Output::

    {
        "Subnet": {
            "SubnetId": "subnet-0e99b93155EXAMPLE",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "CidrBlock": "10.7.1.0/24",
            "State": "available"
        }
    }

**Example 4: To create a security group in the VPC**

The following ``create-security-group`` example creates a security group in the specified VPC. ::

    aws ec2 create-security-group \
        --group-name my-instance-sg \
        --description "Security group for instance workflow" \
        --vpc-id vpc-0a60eb65b4EXAMPLE \
        --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=my-instance-sg}]'

Output::

    {
        "GroupId": "sg-0abc1234def567890",
        "Tags": [
            {
                "Key": "Name",
                "Value": "my-instance-sg"
            }
        ]
    }

**Example 5: To authorize inbound SSH access**

The following ``authorize-security-group-ingress`` example adds an inbound SSH rule to the security group. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-0abc1234def567890 \
        --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp=0.0.0.0/0,Description=SSH}]'

**Example 6: To run an instance in the subnet with the security group**

The following ``run-instances`` example launches an instance in the specified subnet with the specified security group. ::

    aws ec2 run-instances \
        --image-id ami-12345678 \
        --instance-type t2.micro \
        --subnet-id subnet-0e99b93155EXAMPLE \
        --security-group-ids sg-0abc1234def567890 \
        --min-count 1 \
        --max-count 1 \
        --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=my-workflow-instance}]'

Output::

    {
        "Instances": [
            {
                "InstanceId": "i-0123456789abcdef0",
                "SubnetId": "subnet-0e99b93155EXAMPLE",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "State": {
                    "Name": "pending"
                },
                "SecurityGroups": [
                    {
                        "GroupId": "sg-0abc1234def567890",
                        "GroupName": "my-instance-sg"
                    }
                ]
            }
        ]
    }

**Example 7: To wait for the instance to enter the running state**

The following ``wait instance-running`` example pauses and resumes running only after it confirms that the specified instance is in the ``running`` state. ::

    aws ec2 wait instance-running \
        --instance-ids i-0123456789abcdef0

**Example 8: To describe the instance and confirm subnet and security group attachment**

The following ``describe-instances`` example retrieves details about the instance to confirm that it belongs to the specified subnet and uses the specified security group. ::

    aws ec2 describe-instances \
        --instance-ids i-0123456789abcdef0

Output::

    {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-0123456789abcdef0",
                        "SubnetId": "subnet-0e99b93155EXAMPLE",
                        "VpcId": "vpc-0a60eb65b4EXAMPLE",
                        "State": {
                            "Name": "running"
                        },
                        "SecurityGroups": [
                            {
                                "GroupId": "sg-0abc1234def567890",
                                "GroupName": "my-instance-sg"
                            }
                        ]
                    }
                ]
            }
        ]
    }

**Example 9: To describe the security group and confirm the ingress rule configuration**

The following ``describe-security-groups`` example retrieves details about the security group to confirm that the expected ingress rule is present. ::

    aws ec2 describe-security-groups \
        --group-ids sg-0abc1234def567890

Output::

    {
        "SecurityGroups": [
            {
                "GroupId": "sg-0abc1234def567890",
                "GroupName": "my-instance-sg",
                "VpcId": "vpc-0a60eb65b4EXAMPLE",
                "IpPermissions": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22
                    }
                ]
            }
        ]
    }

**Example 10: To terminate the instance**

The following ``terminate-instances`` example terminates the specified instance. ::

    aws ec2 terminate-instances \
        --instance-ids i-0123456789abcdef0

**Example 11: To wait for the instance to terminate**

The following ``wait instance-terminated`` example pauses and resumes running only after it confirms that the specified instance is in the ``terminated`` state. ::

    aws ec2 wait instance-terminated \
        --instance-ids i-0123456789abcdef0

**Example 12: To delete the security group**

The following ``delete-security-group`` example deletes the specified security group after the instance has been terminated. ::

    aws ec2 delete-security-group \
        --group-id sg-0abc1234def567890

**Example 13: To delete the subnet**

The following ``delete-subnet`` example deletes the specified subnet. ::

    aws ec2 delete-subnet \
        --subnet-id subnet-0e99b93155EXAMPLE

**Example 14: To delete the VPC**

The following ``delete-vpc`` example deletes the specified VPC after the dependent resources have been removed. ::

    aws ec2 delete-vpc \
        --vpc-id vpc-0a60eb65b4EXAMPLE