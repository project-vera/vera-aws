**Example 1: To update an item in a table**

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

Populate the table with an item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}, "Awards": {"N": "10"}}'

This command produces no output.

The following ``update-item`` example updates an item in the ``MusicCollection`` table. It adds a new attribute (``Year``) and modifies the ``AlbumTitle`` attribute. All of the attributes in the item, as they appear after the update, are returned in the response. ::

    aws dynamodb update-item \
        --table-name MusicCollection \
        --key file://key.json \
        --update-expression "SET #Y = :y, #AT = :t" \
        --expression-attribute-names file://expression-attribute-names.json \
        --expression-attribute-values file://expression-attribute-values.json \
        --return-values ALL_NEW \
        --return-consumed-capacity TOTAL \
        --return-item-collection-metrics SIZE

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Contents of ``expression-attribute-names.json``::

    {
        "#Y":"Year", "#AT":"AlbumTitle"
    }

Contents of ``expression-attribute-values.json``::

    {
        ":y":{"N": "2015"},
        ":t":{"S": "Louder Than Ever"}
    }

Output::

    {
        "Attributes": {
            "AlbumTitle": {
                "S": "Louder Than Ever"
            },
            "Awards": {
                "N": "10"
            },
            "Artist": {
                "S": "Acme Band"
            },
            "Year": {
                "N": "2015"
            },
            "SongTitle": {
                "S": "Happy Day"
            }
        },
        "ConsumedCapacity": {
            "TableName": "MusicCollection",
            "CapacityUnits": 3.0
        },
        "ItemCollectionMetrics": {
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
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 2: To update an item conditionally**

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

Populate the table with an item that has no ``Year`` attribute. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}}'

This command produces no output.

The following example updates an item in the ``MusicCollection`` table, but only if the existing item does not already have a ``Year`` attribute. ::

    aws dynamodb update-item \
        --table-name MusicCollection \
        --key file://key.json \
        --update-expression "SET #Y = :y, #AT = :t" \
        --expression-attribute-names file://expression-attribute-names.json \
        --expression-attribute-values file://expression-attribute-values.json \
        --condition-expression "attribute_not_exists(#Y)"

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Contents of ``expression-attribute-names.json``::

    {
        "#Y":"Year",
        "#AT":"AlbumTitle"
    }

Contents of ``expression-attribute-values.json``::

    {
        ":y":{"N": "2015"},
        ":t":{"S": "Louder Than Ever"}
    }

If the item already has a ``Year`` attribute, DynamoDB returns the following output. ::

    An error occurred (ConditionalCheckFailedException) when calling the UpdateItem operation: The conditional request failed

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.
