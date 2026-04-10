**To view Contributor Insights settings for a DynamoDB table**

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

Enable Contributor Insights on the ``AlbumTitle-index`` global secondary index. ::

    aws dynamodb update-contributor-insights \
        --table-name MusicCollection \
        --index-name AlbumTitle-index \
        --contributor-insights-action ENABLE

Output::

    {
        "TableName": "MusicCollection",
        "IndexName": "AlbumTitle-index",
        "ContributorInsightsStatus": "ENABLING"
    }

The following ``describe-contributor-insights`` example displays the Contributor Insights settings for the ``MusicCollection`` table and the ``AlbumTitle-index`` global secondary index. ::

    aws dynamodb describe-contributor-insights \
        --table-name MusicCollection \
        --index-name AlbumTitle-index

Output::

    {
        "TableName": "MusicCollection",
        "IndexName": "AlbumTitle-index",
        "ContributorInsightsRuleList": [
            "DynamoDBContributorInsights-PKC-MusicCollection-1576629651520",
            "DynamoDBContributorInsights-SKC-MusicCollection-1576629651520",
            "DynamoDBContributorInsights-PKT-MusicCollection-1576629651520",
            "DynamoDBContributorInsights-SKT-MusicCollection-1576629651520"
        ],
        "ContributorInsightsStatus": "ENABLED",
        "LastUpdateDateTime": 1576629654.78
    }

For more information, see `Analyzing Data Access Using CloudWatch Contributor Insights for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html>`__ in the *Amazon DynamoDB Developer Guide*.