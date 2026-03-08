**To create a capacity reservation**

The following ``create-capacity-reservation`` example creates a capacity reservation in the specified Availability Zone. ::

    aws ec2 create-capacity-reservation \
        --instance-type t2.micro \
        --instance-platform Linux/UNIX \
        --availability-zone us-east-1a \
        --instance-count 1

Output::

    {
        "CapacityReservation": {
            "CapacityReservationId": "cr-1234567890abcdef0",
            "InstanceType": "t2.micro",
            "InstancePlatform": "Linux/UNIX",
            "AvailabilityZone": "us-east-1a",
            "TotalInstanceCount": 1,
            "AvailableInstanceCount": 1,
            "State": "active",
            "InstanceMatchCriteria": "open",
            "Tags": []
        }
    }
