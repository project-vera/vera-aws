**Example 1: To create a Verified Access instance**

The following ``create-verified-access-instance`` example creates a Verified Access instance with a Name tag. FIPS 140-2 compliance is disabled by default. ::

    aws ec2 create-verified-access-instance \
        --tag-specifications ResourceType=verified-access-instance,Tags=[{Key=Name,Value=my-va-instance}]

Output::

    {
        "VerifiedAccessInstance": {
            "VerifiedAccessInstanceId": "vai-0ce000c0b7643abea",
            "Description": "",
            "VerifiedAccessTrustProviders": [],
            "FipsEnabled": false,
            "CreationTime": "2023-08-25T18:27:56",
            "LastUpdatedTime": "2023-08-25T18:27:56",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-va-instance"
                }
            ]
        }
    }

For more information, see `Verified Access instances <https://docs.aws.amazon.com/verified-access/latest/ug/verified-access-instances.html>`__ in the *AWS Verified Access User Guide*.

**Example 2: To create a FIPS-enabled Verified Access instance**

The following ``create-verified-access-instance`` example creates a Verified Access instance with FIPS 140-2 validated cryptography enabled. Use ``--fips-enabled`` when your workload must meet federal compliance requirements such as FedRAMP. The output shows ``FipsEnabled: true``. ::

    aws ec2 create-verified-access-instance \
        --fips-enabled \
        --tag-specifications ResourceType=verified-access-instance,Tags=[{Key=Name,Value=my-fips-va-instance}]

Output::

    {
        "VerifiedAccessInstance": {
            "VerifiedAccessInstanceId": "vai-0df111d1e8643bcfb",
            "Description": "",
            "VerifiedAccessTrustProviders": [],
            "FipsEnabled": true,
            "CreationTime": "2023-08-25T19:03:12",
            "LastUpdatedTime": "2023-08-25T19:03:12",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "my-fips-va-instance"
                }
            ]
        }
    }

For more information, see `Verified Access instances <https://docs.aws.amazon.com/verified-access/latest/ug/verified-access-instances.html>`__ in the *AWS Verified Access User Guide*.
