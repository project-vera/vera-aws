**Example 1: To create an RSA key pair**

The following ``create-key-pair`` example creates a 2048-bit RSA key pair named ``MyKeyPair`` and saves the private key directly to a file. ::

    aws ec2 create-key-pair \
        --key-name MyKeyPair \
        --query "KeyMaterial" \
        --output text > MyKeyPair.pem

Output::

    {
        "KeyFingerprint": "1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f",
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4PAtEsHnEb9X5OKIQhwLajgboEt\n...\n-----END RSA PRIVATE KEY-----",
        "KeyName": "MyKeyPair",
        "KeyPairId": "key-0123456789abcdef0"
    }

For more information, see `Create a key pair using Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To create an ED25519 key pair**

The following ``create-key-pair`` example creates an ED25519 key pair named ``MyKeyPair``. ED25519 keys are shorter and offer improved security and performance compared to RSA keys. ::

    aws ec2 create-key-pair \
        --key-name MyKeyPair \
        --key-type ed25519

Output::

    {
        "KeyFingerprint": "SHA256:EXAMPLEaHfnJe8EXAMPLE0sD5EXAMPLE2/EXAMPLE",
        "KeyMaterial": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA...\n-----END OPENSSH PRIVATE KEY-----",
        "KeyName": "MyKeyPair",
        "KeyPairId": "key-0123456789abcdef0",
        "KeyType": "ed25519"
    }

For more information, see `Create a key pair using Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html>`__ in the *Amazon EC2 User Guide*.
