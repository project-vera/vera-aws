**Example 1: To view a list of Contributor Insights summaries**

First, create the ``MusicCollection`` table with a local secondary index. ::

    aws dynamodb create-table \
        --table-name MusicCollection \
        --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S AttributeName=AlbumTitle,AttributeType=S \
        --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE \
        --local-secondary-indexes IndexName=AlbumTitle-index,KeySchema=["{AttributeName=Artist,KeyType=HASH}","{AttributeName=AlbumTitle,KeyType=RANGE}"],Projection="{ProjectionType=ALL}" \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "AlbumTitle",
                    "AttributeType": "S"
                },
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

Enable Contributor Insights on the ``AlbumTitle-index`` local secondary index. ::

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

Create and enable Contributor Insights on the ``ProductCatalog`` table. ::

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

    aws dynamodb update-contributor-insights \
        --table-name ProductCatalog \
        --contributor-insights-action ENABLE

Output::

    {
        "TableName": "ProductCatalog",
        "ContributorInsightsStatus": "ENABLING"
    }

Create and enable Contributor Insights on the ``Forum`` table. ::

    aws dynamodb create-table \
        --table-name Forum \
        --attribute-definitions AttributeName=Name,AttributeType=S \
        --key-schema AttributeName=Name,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "Name",
                    "AttributeType": "S"
                }
            ],
            "TableName": "Forum",
            "KeySchema": [
                {
                    "AttributeName": "Name",
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
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/Forum",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
        }
    }

    aws dynamodb update-contributor-insights \
        --table-name Forum \
        --contributor-insights-action ENABLE

Output::

    {
        "TableName": "Forum",
        "ContributorInsightsStatus": "ENABLING"
    }

Create and enable Contributor Insights on the ``Reply`` table. ::

    aws dynamodb create-table \
        --table-name Reply \
        --attribute-definitions AttributeName=Id,AttributeType=S \
        --key-schema AttributeName=Id,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "Id",
                    "AttributeType": "S"
                }
            ],
            "TableName": "Reply",
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
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/Reply",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
        }
    }

    aws dynamodb update-contributor-insights \
        --table-name Reply \
        --contributor-insights-action ENABLE

Output::

    {
        "TableName": "Reply",
        "ContributorInsightsStatus": "ENABLING"
    }

Create and enable Contributor Insights on the ``Thread`` table. ::

    aws dynamodb create-table \
        --table-name Thread \
        --attribute-definitions AttributeName=ForumName,AttributeType=S \
        --key-schema AttributeName=ForumName,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "ForumName",
                    "AttributeType": "S"
                }
            ],
            "TableName": "Thread",
            "KeySchema": [
                {
                    "AttributeName": "ForumName",
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
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/Thread",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
        }
    }

    aws dynamodb update-contributor-insights \
        --table-name Thread \
        --contributor-insights-action ENABLE

Output::

    {
        "TableName": "Thread",
        "ContributorInsightsStatus": "ENABLING"
    }

The following ``list-contributor-insights`` example displays a list of Contributor Insights summaries. ::

    aws dynamodb list-contributor-insights

Output::

    {
        "ContributorInsightsSummaries": [
            {
                "TableName": "MusicCollection",
                "IndexName": "AlbumTitle-index",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "ProductCatalog",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "Forum",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "Reply",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "Thread",
                "ContributorInsightsStatus": "ENABLED"
            }
        ]
    }

For more information, see `Analyzing Data Access Using CloudWatch Contributor Insights for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html>`__ in the *Amazon DynamoDB Developer Guide*.

The following example limits the number of items returned to 4. The response includes a ``NextToken`` value with which to retrieve the next page of results. ::

    aws dynamodb list-contributor-insights \
        --max-results 4

Output::

    {
        "ContributorInsightsSummaries": [
            {
                "TableName": "MusicCollection",
                "IndexName": "AlbumTitle-index",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "ProductCatalog",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "Forum",
                "ContributorInsightsStatus": "ENABLED"
            }
        ],
        "NextToken": "abCDeFGhiJKlmnOPqrSTuvwxYZ1aBCdEFghijK7LM51nOpqRSTuv3WxY3ZabC5dEFGhI2Jk3LmnoPQ6RST9"
    }

For more information, see `Analyzing Data Access Using CloudWatch Contributor Insights for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html>`__ in the *Amazon DynamoDB Developer Guide*.

The following command uses the ``NextToken`` value from a previous call to the ``list-contributor-insights`` command to retrieve another page of results. Since the response in this case does not include a ``NextToken`` value, we know that we have reached the end of the results. ::

    aws dynamodb list-contributor-insights \
        --max-results 4 \
        --next-token abCDeFGhiJKlmnOPqrSTuvwxYZ1aBCdEFghijK7LM51nOpqRSTuv3WxY3ZabC5dEFGhI2Jk3LmnoPQ6RST9

Output::

    {
        "ContributorInsightsSummaries": [
            {
                "TableName": "Reply",
                "ContributorInsightsStatus": "ENABLED"
            },
            {
                "TableName": "Thread",
                "ContributorInsightsStatus": "ENABLED"
            }
        ]
    }

For more information, see `Analyzing Data Access Using CloudWatch Contributor Insights for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights.html>`__ in the *Amazon DynamoDB Developer Guide*.