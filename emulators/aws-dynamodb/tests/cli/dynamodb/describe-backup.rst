**To get information about an existing backup of a table**

First, create the ``MusicCollection`` table and a backup. ::

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

    aws dynamodb create-backup \
        --table-name MusicCollection \
        --backup-name MusicCollectionBackup

Output::

    {
        "BackupDetails": {
            "BackupArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a",
            "BackupName": "MusicCollectionBackup",
            "BackupSizeBytes": 0,
            "BackupStatus": "CREATING",
            "BackupType": "USER",
            "BackupCreationDateTime": 1576616366.715
        }
    }

The following ``describe-backup`` example displays information about the specified existing backup. ::

    aws dynamodb describe-backup \
        --backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a

Output::

    {
        "BackupDescription": {
            "BackupDetails": {
                "BackupArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a",
                "BackupName": "MusicCollectionBackup",
                "BackupSizeBytes": 0,
                "BackupStatus": "AVAILABLE",
                "BackupType": "USER",
                "BackupCreationDateTime": 1576616366.715
            },
            "SourceTableDetails": {
                "TableName": "MusicCollection",
                "TableId": "b0c04bcc-309b-4352-b2ae-9088af169fe2",
                "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MusicCollection",
                "TableSizeBytes": 0,
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
                "TableCreationDateTime": 1576615228.571,
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                },
                "ItemCount": 0,
                "BillingMode": "PROVISIONED"
            },
            "SourceTableFeatureDetails": {}
        }
    }

For more information, see `On-Demand Backup and Restore for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html>`__ in the *Amazon DynamoDB Developer Guide*.
