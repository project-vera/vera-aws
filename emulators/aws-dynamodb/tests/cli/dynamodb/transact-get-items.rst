**To retrieve multiple items atomically from one or more tables**

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

Populate the table with items. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}}'

This command produces no output.

Add another item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Call Me Today"}, "AlbumTitle": {"S": "Somewhat Famous"}}'

This command produces no output.

The following ``transact-get-items`` example retrieves multiple items atomically. ::

    aws dynamodb transact-get-items \
        --transact-items file://transact-items.json \
        --return-consumed-capacity TOTAL

Contents of ``transact-items.json``::

    [
        {
            "Get": {
                "Key": {
                    "Artist": {"S": "Acme Band"},
                    "SongTitle": {"S": "Happy Day"}
                },
                "TableName": "MusicCollection"
            }
        },
        {
            "Get": {
                "Key": {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Call Me Today"}
                },
                "TableName": "MusicCollection"
            }
        }
    ]

Output::

    {
        "ConsumedCapacity": [
            {
                "TableName": "MusicCollection",
                "CapacityUnits": 4.0,
                "ReadCapacityUnits": 4.0
            }
        ],
        "Responses": [
            {
                "Item": {
                    "AlbumTitle": {
                        "S": "Songs About Life"
                    },
                    "Artist": {
                        "S": "Acme Band"
                    },
                    "SongTitle": {
                        "S": "Happy Day"
                    }
                }
            },
            {
                "Item": {
                    "AlbumTitle": {
                        "S": "Somewhat Famous"
                    },
                    "Artist": {
                        "S": "No One You Know"
                    },
                    "SongTitle": {
                        "S": "Call Me Today"
                    }
                }
            }
        ]
    }

For more information, see `Managing Complex Workflows with DynamoDB Transactions <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html>`__ in the *Amazon DynamoDB Developer Guide*.
