**Example 1: To delete an item**

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
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

Populate the table with the item to delete. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Scared of My Shadow"}, "AlbumTitle": {"S": "Blue Sky Blues"}}'

This command produces no output.

The following ``delete-item`` example deletes an item from the ``MusicCollection`` table and requests details about the item that was deleted and the capacity used by the request. ::

    aws dynamodb delete-item \
        --table-name MusicCollection \
        --key file://key.json \
        --return-values ALL_OLD \
        --return-consumed-capacity TOTAL \
        --return-item-collection-metrics SIZE

Contents of ``key.json``::

    {
        "Artist": {"S": "No One You Know"},
        "SongTitle": {"S": "Scared of My Shadow"}
    }

Output::

    {
        "Attributes": {
            "AlbumTitle": {
                "S": "Blue Sky Blues"
            },
            "Artist": {
                "S": "No One You Know"
            },
            "SongTitle": {
                "S": "Scared of My Shadow"
            }
        },
        "ConsumedCapacity": {
            "TableName": "MusicCollection",
            "CapacityUnits": 2.0
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

**Example 2: To delete an item conditionally**

First, create the ``ProductCatalog`` table. ::

    aws dynamodb create-table \
        --table-name ProductCatalog \
        --attribute-definitions AttributeName=Id,AttributeType=N \
        --key-schema AttributeName=Id,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "Id",
                    "AttributeType": "N"
                }
            ],
            "TableName": "ProductCatalog",
            "KeySchema": [
                {
                    "AttributeName": "Id",
                    "KeyType": "HASH"
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
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/ProductCatalog",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

Populate the table with the item to delete. ::

    aws dynamodb put-item \
        --table-name ProductCatalog \
        --item '{"Id": {"N": "456"}, "Price": {"N": "550"}, "ProductCategory": {"S": "Sporting Goods"}}'

This command produces no output.

The following example deletes an item from the ``ProductCatalog`` table only if its ``ProductCategory`` is either ``Sporting Goods`` or ``Gardening Supplies`` and its price is between 500 and 600. It returns details about the item that was deleted. ::

    aws dynamodb delete-item \
        --table-name ProductCatalog \
        --key '{"Id":{"N":"456"}}' \
        --condition-expression "(ProductCategory IN (:cat1, :cat2)) and (#P between :lo and :hi)" \
        --expression-attribute-names file://names.json \
        --expression-attribute-values file://values.json \
        --return-values ALL_OLD

Contents of ``names.json``::

    {
        "#P": "Price"
    }

Contents of ``values.json``::

    {
        ":cat1": {"S": "Sporting Goods"},
        ":cat2": {"S": "Gardening Supplies"},
        ":lo": {"N": "500"},
        ":hi": {"N": "600"}
    }

Output::

    {
        "Attributes": {
            "Id": {
                "N": "456"
            },
            "Price": {
                "N": "550"
            },
            "ProductCategory": {
                "S": "Sporting Goods"
            }
        }
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.
