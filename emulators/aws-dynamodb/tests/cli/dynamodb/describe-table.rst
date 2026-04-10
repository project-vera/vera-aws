**To describe a table**

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

The following ``describe-table`` example describes the ``MusicCollection`` table. ::

    aws dynamodb describe-table \
        --table-name MusicCollection

Output::

    {
        "Table": {
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
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0, 
                "WriteCapacityUnits": 5, 
                "ReadCapacityUnits": 5
            }, 
            "TableSizeBytes": 0, 
            "TableName": "MusicCollection", 
            "TableStatus": "ACTIVE", 
            "KeySchema": [
                {
                    "KeyType": "HASH", 
                    "AttributeName": "Artist"
                }, 
                {
                    "KeyType": "RANGE", 
                    "AttributeName": "SongTitle"
                }
            ], 
            "ItemCount": 0, 
            "CreationDateTime": 1421866952.062
        }
    }

For more information, see `Describing a Table <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.Basics.html#WorkingWithTables.Basics.DescribeTable>`__ in the *Amazon DynamoDB Developer Guide*.
