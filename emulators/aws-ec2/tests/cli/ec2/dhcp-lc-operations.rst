DHCP options lifecycle
======================

This lifecycle example validates the EC2 DHCP options create, describe, associate,
VPC readback, default reassociation, file input, and cleanup paths.

It covers the parser and response-shape issue where AWS CLI sends nested EC2
Query parameters for ``create-dhcp-options``:

* ``DhcpConfiguration.1.Key``
* ``DhcpConfiguration.1.Value.1``

The backend must reconstruct those fields into the internal
``DhcpConfiguration.N`` list. ``CreateDhcpOptions`` must also serialize the
create response as singular ``dhcpOptions`` so botocore can parse it into
``DhcpOptions``.

Shorthand create / describe / delete
------------------------------------

Create DHCP options using shorthand input::

    aws ec2 create-dhcp-options \
        --dhcp-configurations Key=domain-name,Values=example.com

Expected output shape::

    {
        "DhcpOptions": {
            "DhcpConfigurations": [
                {
                    "Key": "domain-name",
                    "Values": [
                        {
                            "Value": "example.com"
                        }
                    ]
                }
            ],
            "DhcpOptionsId": "dhcp-xxxxxxxxxxxxxxxxx",
            "OwnerId": "",
            "Tags": []
        }
    }

Describe the DHCP options::

    aws ec2 describe-dhcp-options \
        --dhcp-options-ids dhcp-xxxxxxxxxxxxxxxxx

Delete the DHCP options::

    aws ec2 delete-dhcp-options \
        --dhcp-options-id dhcp-xxxxxxxxxxxxxxxxx

VPC association and readback lifecycle
--------------------------------------

Create a VPC::

    aws ec2 create-vpc \
        --cidr-block 10.63.0.0/16

Create DHCP options::

    aws ec2 create-dhcp-options \
        --dhcp-configurations Key=domain-name,Values=example.internal

Associate the DHCP options with the VPC::

    aws ec2 associate-dhcp-options \
        --dhcp-options-id dhcp-xxxxxxxxxxxxxxxxx \
        --vpc-id vpc-xxxxxxxxxxxxxxxxx

Describe the VPC and verify the custom DHCP options association::

    aws ec2 describe-vpcs \
        --vpc-ids vpc-xxxxxxxxxxxxxxxxx

Expected output shape includes::

    {
        "Vpcs": [
            {
                "VpcId": "vpc-xxxxxxxxxxxxxxxxx",
                "DhcpOptionsId": "dhcp-xxxxxxxxxxxxxxxxx"
            }
        ]
    }

Describe the DHCP options after association::

    aws ec2 describe-dhcp-options \
        --dhcp-options-ids dhcp-xxxxxxxxxxxxxxxxx

Reassociate the VPC to the default DHCP options for cleanup::

    aws ec2 associate-dhcp-options \
        --dhcp-options-id default \
        --vpc-id vpc-xxxxxxxxxxxxxxxxx

Describe the VPC again and verify the default reassociation::

    aws ec2 describe-vpcs \
        --vpc-ids vpc-xxxxxxxxxxxxxxxxx

Expected output shape includes::

    {
        "Vpcs": [
            {
                "VpcId": "vpc-xxxxxxxxxxxxxxxxx",
                "DhcpOptionsId": "default"
            }
        ]
    }

Delete the custom DHCP options::

    aws ec2 delete-dhcp-options \
        --dhcp-options-id dhcp-xxxxxxxxxxxxxxxxx

Delete the VPC::

    aws ec2 delete-vpc \
        --vpc-id vpc-xxxxxxxxxxxxxxxxx

File input variant
------------------

The same create / describe / delete path should work when the DHCP configuration
is supplied through ``file://`` input.

Example file, ``dhcp-options.json``::

    [
      {
        "Key": "domain-name",
        "Values": [
          "example.net"
        ]
      }
    ]

Create DHCP options from the file::

    aws ec2 create-dhcp-options \
        --dhcp-configurations file://dhcp-options.json

Expected output shape::

    {
        "DhcpOptions": {
            "DhcpConfigurations": [
                {
                    "Key": "domain-name",
                    "Values": [
                        {
                            "Value": "example.net"
                        }
                    ]
                }
            ],
            "DhcpOptionsId": "dhcp-xxxxxxxxxxxxxxxxx",
            "OwnerId": "",
            "Tags": []
        }
    }

Validation notes
----------------

The important validation chain is:

* ``create-dhcp-options`` accepts nested DHCP configuration input from shorthand.
* ``create-dhcp-options`` accepts nested DHCP configuration input from ``file://``.
* ``CreateDhcpOptions`` returns a parseable singular ``DhcpOptions`` object.
* ``describe-dhcp-options`` can read back the created option set.
* ``associate-dhcp-options`` can associate the custom option set with a VPC.
* ``describe-vpcs`` reads back the custom ``DhcpOptionsId``.
* associating ``default`` disassociates the custom DHCP options.
* ``describe-vpcs`` reads back ``DhcpOptionsId: default`` after reassociation.
* ``delete-dhcp-options`` succeeds after default reassociation.
* cleanup deletes the VPC.

This lifecycle is mirrored by the external runnable JSON suite in
``aws-testcases/cli/ec2_network``:

* ``testcase4.json`` — create / describe / delete lifecycle
* ``testcase5.json`` — create / associate with VPC / VPC readback / default reassociation readback / cleanup
* ``testcase12.json`` — ``file://`` input lifecycle

After the DHCP parser and serializer fixes, the full external network lifecycle
suite passed ``13/13`` against the local Vera EC2 endpoint.
