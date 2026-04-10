**Example 1: To read an item in a table**

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

Populate the table with an item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}}'

This command produces no output.

The following ``get-item`` example retrieves an item from the ``MusicCollection`` table. The table has a hash-and-range primary key (``Artist`` and ``SongTitle``), so you must specify both of these attributes. The command also requests information about the read capacity consumed by the operation. ::

    aws dynamodb get-item \
        --table-name MusicCollection \
        --key file://key.json \
        --return-consumed-capacity TOTAL

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Output::

    {
        "Item": {
            "AlbumTitle": {
                "S": "Songs About Life"
            },
            "SongTitle": {
                "S": "Happy Day"
            },
            "Artist": {
                "S": "Acme Band"
            }
        },
        "ConsumedCapacity": {
            "TableName": "MusicCollection",
            "CapacityUnits": 0.5
        }
    }

For more information, see `Reading an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ReadingData>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 2: To read an item using a consistent read**

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

Populate the table with an item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}}'

This command produces no output.

The following example retrieves an item from the ``MusicCollection`` table using strongly consistent reads. ::

    aws dynamodb get-item \
        --table-name MusicCollection \
        --key file://key.json \
        --consistent-read \
        --return-consumed-capacity TOTAL

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Output::

    {
        "Item": {
            "AlbumTitle": {
                "S": "Songs About Life"
            },
            "SongTitle": {
                "S": "Happy Day"
            },
            "Artist": {
                "S": "Acme Band"
            }
        },
        "ConsumedCapacity": {
            "TableName": "MusicCollection",
            "CapacityUnits": 1.0
        }
    }

For more information, see `Reading an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ReadingData>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 3: To retrieve specific attributes of an item**

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

Populate the table with an item. ::

    aws dynamodb put-item \
        --table-name ProductCatalog \
        --item '{"Id": {"N": "102"}, "Title": {"S": "Book 102 Title"}, "ProductCategory": {"S": "Book"}, "Price": {"N": "20"}}'

This command produces no output.

The following example uses a projection expression to retrieve only three attributes of the desired item. ::

    aws dynamodb get-item \
        --table-name ProductCatalog \
        --key '{"Id": {"N": "102"}}' \
        --projection-expression "#T, #C, #P" \
        --expression-attribute-names file://names.json

Contents of ``names.json``::

    {
        "#T": "Title",
        "#C": "ProductCategory",
        "#P": "Price"
    }

Output::

    {
        "Item": {
            "Price": {
                "N": "20"
            },
            "Title": {
                "S": "Book 102 Title"
            },
            "ProductCategory": {
                "S": "Book"
            }
        }
    }

For more information, see `Reading an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ReadingData>`__ in the *Amazon DynamoDB Developer Guide*.
