**Example 1: To add an item to a table**

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

The following ``put-item`` example adds a new item to the *MusicCollection* table. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item file://item.json \
        --return-consumed-capacity TOTAL \
        --return-item-collection-metrics SIZE

Contents of ``item.json``::

    {
        "Artist": {"S": "No One You Know"},
        "SongTitle": {"S": "Call Me Today"},
        "AlbumTitle": {"S": "Greatest Hits"}
    }

Output::

    {
        "ConsumedCapacity": {
            "TableName": "MusicCollection",
            "CapacityUnits": 1.0
        },
        "ItemCollectionMetrics": {
            "ItemCollectionKey": {
                "Artist": {
                    "S": "No One You Know"
                }
            },
            "SizeEstimateRangeGB": [
                0.0,
                1.0
            ]
        }
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 2: To conditionally overwrite an item in a table**

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

Populate the table with the existing item to be overwritten. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Call Me Today"}, "AlbumTitle": {"S": "Greatest Hits"}}'

This command produces no output.

The following ``put-item`` example overwrites an existing item in the ``MusicCollection`` table only if that existing item has an ``AlbumTitle`` attribute with a value of ``Greatest Hits``. The command returns the previous value of the item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item file://item.json \
        --condition-expression "#A = :A" \
        --expression-attribute-names file://names.json \
        --expression-attribute-values file://values.json \
        --return-values ALL_OLD

Contents of ``item.json``::

    {
        "Artist": {"S": "No One You Know"},
        "SongTitle": {"S": "Call Me Today"},
        "AlbumTitle": {"S": "Somewhat Famous"}
    }

Contents of ``names.json``::

    {
        "#A": "AlbumTitle"
    }

Contents of ``values.json``::

    {
        ":A": {"S": "Greatest Hits"}
    }

Output::

    {
        "Attributes": {
            "AlbumTitle": {
                "S": "Greatest Hits"
            },
            "Artist": {
                "S": "No One You Know"
            },
            "SongTitle": {
                "S": "Call Me Today"
            }
        }
    }

If the key already exists, you should see the following output::

    A client error (ConditionalCheckFailedException) occurred when calling the PutItem operation: The conditional request failed.

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.
