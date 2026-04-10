**To scan a table**

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
        --item '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Scared of My Shadow"}, "AlbumTitle": {"S": "Blue Sky Blues"}}'

This command produces no output.

Add another item. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}}'

This command produces no output.

The following ``scan`` example scans the entire ``MusicCollection`` table, and then narrows the results to songs by the artist "No One You Know". For each item, only the album title and song title are returned. ::

    aws dynamodb scan \
        --table-name MusicCollection \
        --filter-expression "Artist = :a" \
        --projection-expression "#ST, #AT" \
        --expression-attribute-names file://expression-attribute-names.json \
        --expression-attribute-values file://expression-attribute-values.json

Contents of ``expression-attribute-names.json``::

    {
        "#ST": "SongTitle",
        "#AT":"AlbumTitle"
    }

Contents of ``expression-attribute-values.json``::

    {
        ":a": {"S": "No One You Know"}
    }

Output::

    {
        "Count": 2,
        "Items": [
            {
                "SongTitle": {
                    "S": "Call Me Today"
                },
                "AlbumTitle": {
                    "S": "Somewhat Famous"
                }
            },
            {
                "SongTitle": {
                    "S": "Scared of My Shadow"
                },
                "AlbumTitle": {
                    "S": "Blue Sky Blues"
                }
            }
        ],
        "ScannedCount": 3,
        "ConsumedCapacity": null
    }

For more information, see `Working with Scans in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html>`__ in the *Amazon DynamoDB Developer Guide*.
