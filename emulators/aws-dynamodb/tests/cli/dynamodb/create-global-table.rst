**To create a global table**

First, create the ``MusicCollection`` table. ::

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

The following ``create-global-table`` example creates a global table from two identical tables in the specified, separate AWS Regions. ::

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

For more information, see `DynamoDB Global Tables <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html>`__ in the *Amazon DynamoDB Developer Guide*.
