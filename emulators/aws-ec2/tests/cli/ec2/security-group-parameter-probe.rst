Security Group Parameter Probe
=============================

The following examples probe the input parsing paths for security group rule APIs, covering
simple-form parameters, shorthand ``--ip-permissions``, file-based ``--ip-permissions``,
and revoke flows. These examples are intended to verify that multiple valid AWS CLI input
forms are accepted and converted into usable rule objects.

**Example 1: To authorize an ingress rule using simple-form parameters**

The following ``authorize-security-group-ingress`` example adds a TCP/22 ingress rule using
``--protocol``, ``--port``, and ``--cidr``. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0

Expected behavior:
- The request succeeds.
- A security group rule is created for TCP port 22 from ``0.0.0.0/0``.

**Example 2: To authorize an ingress rule using shorthand ip-permissions**

The following ``authorize-security-group-ingress`` example adds a TCP/80 ingress rule using
shorthand ``--ip-permissions`` syntax. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges=[{CidrIp=0.0.0.0/0}]

Expected behavior:
- The request succeeds.
- A security group rule is created for TCP port 80 from ``0.0.0.0/0``.

**Example 3: To authorize an ingress rule using file-based ip-permissions**

The following ``authorize-security-group-ingress`` example adds a TCP/443 ingress rule using
a JSON file passed through ``file://``. Assume the file ``ip-permissions.json`` contains: ::

    [
      {
        "IpProtocol": "tcp",
        "FromPort": 443,
        "ToPort": 443,
        "IpRanges": [
          { "CidrIp": "0.0.0.0/0" }
        ]
      }
    ]

Run command: ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions file://ip-permissions.json

Expected behavior:
- The request succeeds.
- A security group rule is created for TCP port 443 from ``0.0.0.0/0``.

**Example 4: To authorize an egress rule using shorthand ip-permissions**

The following ``authorize-security-group-egress`` example adds a TCP/443 egress rule using
shorthand ``--ip-permissions`` syntax. ::

    aws ec2 authorize-security-group-egress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0}]

Expected behavior:
- The request succeeds.
- An egress rule is created for TCP port 443 to ``0.0.0.0/0``.

**Example 5: To revoke an ingress rule using basic-form parameters**

The following ``revoke-security-group-ingress`` example removes a previously added TCP/22
ingress rule. ::

    aws ec2 revoke-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0

Expected behavior:
- The request succeeds.
- The matching TCP/22 ingress rule is removed.

**Example 6: To revoke an egress rule using basic-form parameters**

The following ``revoke-security-group-egress`` example removes a previously added TCP/443
egress rule. ::

    aws ec2 revoke-security-group-egress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0

Expected behavior:
- The request succeeds.
- The matching TCP/443 egress rule is removed.