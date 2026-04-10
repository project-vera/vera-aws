**To retrieve multiple items from a table**

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
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Call Me Today"}, "AlbumTitle": {"S": "Somewhat Famous"}}'

This command produces no output.

Add another item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Louder Than Ever"}}'

This command produces no output.

Add another item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Scared of My Shadow"}, "AlbumTitle": {"S": "Blue Sky Blues"}}'

This command produces no output.

The following ``batch-get-items`` example reads multiple items from the ``MusicCollection`` table using a batch of three ``GetItem`` requests, and requests the number of read capacity units consumed by the operation. The command returns only the ``AlbumTitle`` attribute. ::

    aws dynamodb batch-get-item \
        --request-items file://request-items.json \
        --return-consumed-capacity TOTAL

Contents of ``request-items.json``::

    {
        "MusicCollection": {
            "Keys": [
                {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Call Me Today"}
                },
                {
                    "Artist": {"S": "Acme Band"},
                    "SongTitle": {"S": "Happy Day"}
                },
                {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Scared of My Shadow"}
                }
            ],
            "ProjectionExpression":"AlbumTitle"
        }
    }

Output::

    {
        "Responses": {
            "MusicCollection": [
                {
                    "AlbumTitle": {
                        "S": "Somewhat Famous"
                    }
                },
                {
                    "AlbumTitle": {
                        "S": "Blue Sky Blues"
                    }
                },
                {
                    "AlbumTitle": {
                        "S": "Louder Than Ever"
                    }
                }
            ]
        },
        "UnprocessedKeys": {},
        "ConsumedCapacity": [
            {
                "TableName": "MusicCollection",
                "CapacityUnits": 1.5
            }
        ]
    }

For more information, see `Batch Operations <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.BatchOperations>`__ in the *Amazon DynamoDB Developer Guide*.
