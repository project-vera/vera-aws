**To remove a tag from a DynamoDB resource**

First, create the ``MusicCollection`` table and add a tag. ::

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

::

    aws dynamodb tag-resource \
        --resource-arn arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection \
        --tags Key=Owner,Value=blueTeam

This command produces no output.

The following ``untag-resource`` example removes the tag with the key ``Owner`` from the ``MusicCollection`` table. ::

    aws dynamodb untag-resource \
        --resource-arn arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection \
        --tag-keys Owner

This command produces no output.

For more information, see `Tagging for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Tagging.html>`__ in the *Amazon DynamoDB Developer Guide*.
