**To view auto scaling settings across replicas of a global table**

First, create the ``MusicCollection`` table and set it up as a global table. ::

    aws dynamodb create-table \
        --table-name MusicCollection \
        --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S \
        --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "Artist",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "SongTitle",
                    "AttributeType": "S"
                }
            ],
            "TableName": "MusicCollection",
            "KeySchema": [
                {
                    "AttributeName": "Artist",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "SongTitle",
                    "KeyType": "RANGE"
                }
            ],
            "TableStatus": "CREATING",
            "CreationDateTime": "2024-01-01T00:00:00.000000+00:00",
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0,
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            },
            "TableSizeBytes": 0,
            "ItemCount": 0,
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

Create the global table with replicas. ::

    aws dynamodb create-global-table \
        --global-table-name MusicCollection \
        --replication-group RegionName=us-east-2 RegionName=us-east-1 \
        --region us-east-2

Output::

    {
        "GlobalTableDescription": {
            "ReplicationGroup": [
                {
                    "RegionName": "us-east-2"
                },
                {
                    "RegionName": "us-east-1"
                }
            ],
            "GlobalTableArn": "arn:aws:dynamodb::123456789012:global-table/MusicCollection",
            "CreationDateTime": 1576625818.532,
            "GlobalTableStatus": "CREATING",
            "GlobalTableName": "MusicCollection"
        }
    }

The following ``describe-table-replica-auto-scaling`` example displays auto scaling settings across replicas of the ``MusicCollection`` global table. ::

    aws dynamodb describe-table-replica-auto-scaling \
        --table-name MusicCollection

Output::

    {
        "TableAutoScalingDescription": {
            "TableName": "MusicCollection",
            "TableStatus": "ACTIVE",
            "Replicas": [
                {
                    "RegionName": "us-east-1",
                    "GlobalSecondaryIndexes": [],
                    "ReplicaProvisionedReadCapacityAutoScalingSettings": {
                        "MinimumUnits": 5,
                        "MaximumUnits": 40000,
                        "AutoScalingRoleArn": "arn:aws:iam::123456789012:role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable",
                        "ScalingPolicies": [
                            {
                                "PolicyName": "DynamoDBReadCapacityUtilization:table/MusicCollection",
                                "TargetTrackingScalingPolicyConfiguration": {
                                    "TargetValue": 70.0
                                }
                            }
                        ]
                    },
                    "ReplicaProvisionedWriteCapacityAutoScalingSettings": {
                        "MinimumUnits": 5,
                        "MaximumUnits": 40000,
                        "AutoScalingRoleArn": "arn:aws:iam::123456789012:role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable",
                        "ScalingPolicies": [
                            {
                                "PolicyName": "DynamoDBWriteCapacityUtilization:table/MusicCollection",
                                "TargetTrackingScalingPolicyConfiguration": {
                                    "TargetValue": 70.0
                                }
                            }
                        ]
                    },
                    "ReplicaStatus": "ACTIVE"
                },
                {
                    "RegionName": "us-east-2",
                    "GlobalSecondaryIndexes": [],
                    "ReplicaProvisionedReadCapacityAutoScalingSettings": {
                        "MinimumUnits": 5,
                        "MaximumUnits": 40000,
                        "AutoScalingRoleArn": "arn:aws:iam::123456789012:role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable",
                        "ScalingPolicies": [
                            {
                                "PolicyName": "DynamoDBReadCapacityUtilization:table/MusicCollection",
                                "TargetTrackingScalingPolicyConfiguration": {
                                    "TargetValue": 70.0
                                }
                            }
                        ]
                    },
                    "ReplicaProvisionedWriteCapacityAutoScalingSettings": {
                        "MinimumUnits": 5,
                        "MaximumUnits": 40000,
                        "AutoScalingRoleArn": "arn:aws:iam::123456789012:role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable",
                        "ScalingPolicies": [
                            {
                                "PolicyName": "DynamoDBWriteCapacityUtilization:table/MusicCollection",
                                "TargetTrackingScalingPolicyConfiguration": {
                                    "TargetValue": 70.0
                                }
                            }
                        ]
                    },
                    "ReplicaStatus": "ACTIVE"
                }
            ]
        }
    }

For more information, see `DynamoDB Global Tables <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html>`__ in the *Amazon DynamoDB Developer Guide*.
