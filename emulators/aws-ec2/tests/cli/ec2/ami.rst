**To create an AMI from a running instance**

The following ``create-image`` example creates an AMI from the specified instance. ::

    aws ec2 create-image \
        --instance-id i-1234567890abcdef0 \
        --name "My server" \
        --description "An AMI for my server"

Output::

    {
        "ImageId": "ami-0abcdef1234567890"
    }
