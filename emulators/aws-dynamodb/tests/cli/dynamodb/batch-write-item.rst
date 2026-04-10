**To add multiple items to a table**

First, create the ``MusicCollection`` table with an ``AlbumTitleIndex`` local secondary index. ::

    aws dynamodb create-table \
        --table-name MusicCollection \
        --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S AttributeName=AlbumTitle,AttributeType=S \
        --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE \
        --local-secondary-indexes "IndexName=AlbumTitleIndex,KeySchema=[{AttributeName=Artist,KeyType=HASH},{AttributeName=AlbumTitle,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
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
                },
                {
                    "AttributeName": "AlbumTitle",
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
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "LocalSecondaryIndexes": [
                {
                    "IndexName": "AlbumTitleIndex",
                    "KeySchema": [
                        {
                            "AttributeName": "Artist",
                            "KeyType": "HASH"
                        },
                        {
                            "AttributeName": "AlbumTitle",
                            "KeyType": "RANGE"
                        }
                    ],
                    "Projection": {
                        "ProjectionType": "ALL"
                    },
                    "IndexSizeBytes": 0,
                    "ItemCount": 0,
                    "IndexArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection/index/AlbumTitleIndex"
                }
            ]
        }
    }

The following ``batch-write-item`` example adds three new items to the ``MusicCollection`` table using a batch of three ``PutItem`` requests. It also requests information about the number of write capacity units consumed by the operation and any item collections modified by the operation. ::

    aws dynamodb batch-write-item \
        --request-items file://request-items.json \
        --return-consumed-capacity INDEXES \
        --return-item-collection-metrics SIZE

Contents of ``request-items.json``::

    {
        "MusicCollection": [
            {
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "No One You Know"},
                        "SongTitle": {"S": "Call Me Today"},
                        "AlbumTitle": {"S": "Somewhat Famous"}
                    }
                }
            },
            {
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "Acme Band"},
                        "SongTitle": {"S": "Happy Day"},
                        "AlbumTitle": {"S": "Songs About Life"}
                    }
                }
            },
            {
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "No One You Know"},
                        "SongTitle": {"S": "Scared of My Shadow"},
                        "AlbumTitle": {"S": "Blue Sky Blues"}
                    }
                }
            }
        ]
    }

Output::

    {
        "UnprocessedItems": {},
        "ItemCollectionMetrics": {
            "MusicCollection": [
                {
                    "ItemCollectionKey": {
                        "Artist": {
                            "S": "No One You Know"
                        }
                    },
                    "SizeEstimateRangeGB": [
                        0.0,
                        1.0
                    ]
                },
                {
                    "ItemCollectionKey": {
                        "Artist": {
                            "S": "Acme Band"
                        }
                    },
                    "SizeEstimateRangeGB": [
                        0.0,
                        1.0
                    ]
                }
            ]
        },
        "ConsumedCapacity": [
            {
                "TableName": "MusicCollection",
                "CapacityUnits": 6.0,
                "Table": {
                    "CapacityUnits": 3.0
                },
                "LocalSecondaryIndexes": {
                    "AlbumTitleIndex": {
                        "CapacityUnits": 3.0
                    }
                }
            }
        ]
    }

For more information, see `Batch Operations <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.BatchOperations>`__ in the *Amazon DynamoDB Developer Guide*.
