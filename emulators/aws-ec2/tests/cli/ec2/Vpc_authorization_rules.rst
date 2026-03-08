**To describe account attributes**

The following ``describe-account-attributes`` example describes the attributes for your AWS account. ::

    aws ec2 describe-account-attributes

Output::

    {
        "AccountAttributes": [
            {
                "AttributeName": "supported-platforms",
                "AttributeValues": [
                    {
                        "AttributeValue": "VPC"
                    }
                ]
            },
            {
                "AttributeName": "default-vpc",
                "AttributeValues": [
                    {
                        "AttributeValue": "none"
                    }
                ]
            }
        ]
    }
