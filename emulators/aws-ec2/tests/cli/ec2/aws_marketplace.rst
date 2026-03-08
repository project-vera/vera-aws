**To create a volume**

The following ``create-volume`` example creates a General Purpose SSD volume in the specified Availability Zone. ::

    aws ec2 create-volume \
        --availability-zone us-east-1a \
        --size 10

Output::

    {
        "VolumeId": "vol-0abcdef1234567890",
        "Size": 10,
        "SnapshotId": "",
        "AvailabilityZone": "us-east-1a",
        "State": "available",
        "VolumeType": "gp2",
        "Tags": []
    }
