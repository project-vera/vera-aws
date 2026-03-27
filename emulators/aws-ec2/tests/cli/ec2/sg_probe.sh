#!/usr/bin/env bash
set -u

echo "== create vpc =="
VPC_ID=$(awscli ec2 create-vpc --cidr-block 10.20.0.0/16 | python3 -c "import sys,json; print(json.load(sys.stdin)['Vpc']['VpcId'])")
echo "VPC_ID=$VPC_ID"

awscli ec2 wait vpc-available --vpc-ids "$VPC_ID"

echo
echo "== create security group =="
SG_ID=$(awscli ec2 create-security-group \
  --group-name sg-probe-group \
  --description "probe security group parsing" \
  --vpc-id "$VPC_ID" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['GroupId'])")
echo "SG_ID=$SG_ID"

echo
echo "== probe 1: simple ingress args =="
awscli ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0
echo "probe 1 exit code: $?"

echo
echo "== describe security groups after probe 1 =="
awscli ec2 describe-security-groups --group-ids "$SG_ID"

echo
echo "== probe 2: shorthand ip-permissions ingress =="
awscli ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=0.0.0.0/0}]"
echo "probe 2 exit code: $?"

echo
echo "== describe security groups after probe 2 =="
awscli ec2 describe-security-groups --group-ids "$SG_ID"

echo
echo "== write ip_permissions.json =="
cat > ip_permissions.json <<'EOF'
[
  {
    "IpProtocol": "tcp",
    "FromPort": 22,
    "ToPort": 22,
    "IpRanges": [
      {
        "CidrIp": "0.0.0.0/0"
      }
    ]
  }
]
EOF

cat ip_permissions.json

echo
echo "== probe 3: file:// ip-permissions ingress =="
awscli ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --ip-permissions file://ip_permissions.json
echo "probe 3 exit code: $?"

echo
echo "== describe security groups after probe 3 =="
awscli ec2 describe-security-groups --group-ids "$SG_ID"

echo
echo "== probe 4: shorthand ip-permissions egress =="
awscli ec2 authorize-security-group-egress \
  --group-id "$SG_ID" \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0}]"
echo "probe 4 exit code: $?"

echo
echo "== describe security groups after probe 4 =="
awscli ec2 describe-security-groups --group-ids "$SG_ID"

echo
echo "== cleanup =="
awscli ec2 delete-security-group --group-id "$SG_ID"
awscli ec2 delete-vpc --vpc-id "$VPC_ID"
rm -f ip_permissions.json

echo
echo "done"