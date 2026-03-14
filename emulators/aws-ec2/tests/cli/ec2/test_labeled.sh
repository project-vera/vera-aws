# ==============================================================================
# Non-EC2 commands (with augmented-ec2 replacements)
# ==============================================================================

# --- configure ---
# label: non-ec2
awscli configure list
# label: augmented-ec2
awscli ec2 describe-regions

# --- ssm ---
# label: non-ec2
awscli ssm get-parameters --names /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2 --region us-east-1
# label: augmented-ec2
awscli ec2 describe-images --owners amazon

# --- sts ---
# label: non-ec2
awscli sts get-caller-identity
# label: augmented-ec2
awscli ec2 describe-account-attributes

# --- elb describe ---
# label: non-ec2
awscli elb describe-load-balancers --load-balancer-names test-elb
# label: augmented-ec2
awscli ec2 describe-instances

# --- elb create ---
# label: non-ec2
awscli elb create-load-balancer --load-balancer-name test-elb-new --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 --availability-zones us-east-1a
# label: augmented-ec2
awscli ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'

# --- elb health check ---
# label: non-ec2
awscli elb configure-health-check --load-balancer-name test-elb --health-check Target=HTTP:80/index.html,Interval=30,Timeout=5,UnhealthyThreshold=2,HealthyThreshold=10
# label: augmented-ec2
awscli ec2 describe-instance-status

# --- elb modify ---
# label: non-ec2
awscli elb modify-load-balancer-attributes --load-balancer-name test-elb --load-balancer-attributes "{\"AccessLog\":{\"Enabled\":false}}"
# label: augmented-ec2
awscli ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'

# --- iam ---
# label: non-ec2
awscli iam upload-server-certificate --server-certificate-name test-domain.com --certificate-body file://cert.pem --private-key file://key.pem --certificate-chain file://chain.pem
# label: augmented-ec2
awscli ec2 describe-key-pairs

# ==============================================================================
# EC2 commands — Read-only / List (no specific ID needed)
# ==============================================================================

# --- Regions ---
# label: ec2
awscli ec2 describe-regions
# label: ec2
awscli ec2 describe-regions --output text

# --- Account ---
# label: ec2
awscli ec2 describe-account-attributes

# --- VPCs (list all) ---
# label: ec2
awscli ec2 describe-vpcs
# label: ec2
awscli ec2 describe-vpcs --query 'Vpcs[].{VPCID:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value|[0]}'
# label: ec2
awscli ec2 describe-vpcs --filters Name=tag:Name,Values=mock-vpc-name --query 'Vpcs[].VpcId' --output text

# --- Subnets (list all) ---
# label: ec2
awscli ec2 describe-subnets
# label: ec2
awscli ec2 describe-subnets --query 'Subnets[].{VPC_id:VpcId,SUB_id:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value|[0]}'

# --- Security Groups (list all) ---
# label: ec2
awscli ec2 describe-security-groups
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[].{SG_id:GroupId,Name:GroupName,Vpc_id:VpcId,Rules:IpPermissions[].{SourceCIDR:IpRanges[].CidrIp|[0],fromport:FromPort,ToPort:ToPort,Protocol:IpProtocol}}'

# --- Route Tables (list all) ---
# label: ec2
awscli ec2 describe-route-tables
# label: ec2
awscli ec2 describe-route-tables --query 'RouteTables[*].{rt_id:RouteTableId,Vpc_id:VpcId,Main:Associations[].Main|[0],Routes:Routes}'

# --- Internet Gateways (list all) ---
# label: ec2
awscli ec2 describe-internet-gateways
# label: ec2
awscli ec2 describe-internet-gateways --query 'InternetGateways[].{Igw_id:InternetGatewayId,Vpc_id:Attachments[].VpcId|[0],State:Attachments[].State|[0]}'

# --- Images ---
# label: ec2
awscli ec2 describe-images --owners amazon
# label: ec2
awscli ec2 describe-images --owners 309956199498 --filters 'Name=name,Values=RHEL-8.*' 'Name=state,Values=available' --query 'reverse(sort_by(Images, &CreationDate))[:1].{Name:Name,Ami:ImageId,Created:CreationDate}' --output table
# label: ec2
awscli ec2 describe-images --owners amazon --filters 'Name=name,Values=amzn2-ami-hvm-2.0.????????.?-x86_64-gp2' 'Name=state,Values=available' --query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' --output text

# --- Instance Types ---
# label: ec2
awscli ec2 describe-instance-types --filters "Name=free-tier-eligible,Values=true" "Name=current-generation,Values=true" --query 'InstanceTypes[].{Instance:InstanceType,Memory:MemoryInfo.SizeInMiB,Ghz:ProcessorInfo.SustainedClockSpeedInGhz,VirType:SupportedVirtualizationTypes|[0]}'

# --- Instances (list all) ---
# label: ec2
awscli ec2 describe-instances
# label: ec2
awscli ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,InstanceType,PrivateIpAddress,Tags[?Key==`Name`].Value[]]' --filters Name=instance-state-name,Values=running --output text
# label: ec2
awscli ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,State:State.Name,AZ:Placement.AvailabilityZone}' --output table

# --- Instance Status ---
# label: ec2
awscli ec2 describe-instance-status
# label: ec2
awscli ec2 describe-instance-status --include-all-instances

# --- Volumes (list all) ---
# label: ec2
awscli ec2 describe-volumes
# label: ec2
awscli ec2 describe-volumes --query 'Volumes[].{ID:VolumeId,Size:Size,State:State,AZ:AvailabilityZone}'

# --- Snapshots ---
# label: ec2
awscli ec2 describe-snapshots --owner-ids self
# label: ec2
awscli ec2 describe-snapshots --owner-ids 123456789012 --filters Name=status,Values=pending

# --- Key Pairs ---
# label: ec2
awscli ec2 describe-key-pairs

# --- Elastic IPs ---
# label: ec2
awscli ec2 describe-addresses

# --- Network ACLs ---
# label: ec2
awscli ec2 describe-network-acls
# label: ec2
awscli ec2 describe-network-acls --query 'NetworkAcls[].{ID:NetworkAclId,VpcId:VpcId,IsDefault:IsDefault}'

# --- Network Interfaces ---
# label: ec2
awscli ec2 describe-network-interfaces

# --- Availability Zones ---
# label: ec2
awscli ec2 describe-availability-zones

# --- Tags ---
# label: ec2
awscli ec2 describe-tags

# ==============================================================================
# EC2 commands — Create from scratch (no pre-existing resources needed)
# ==============================================================================

# --- Create VPC ---
# label: ec2
awscli ec2 create-vpc --cidr-block 10.99.0.0/16

# --- Create Security Group (uses default VPC) ---
# label: ec2
awscli ec2 create-security-group --group-name test-sg-labeled --description "Test security group for labeled tests"

# --- Create Key Pair ---
# label: ec2
awscli ec2 create-key-pair --key-name test-key-labeled --query 'KeyName' --output text

# --- Allocate Elastic IP ---
# label: ec2
awscli ec2 allocate-address --domain vpc

# --- Create Internet Gateway ---
# label: ec2
awscli ec2 create-internet-gateway

# --- DHCP Options (list) ---
# label: ec2
awscli ec2 describe-dhcp-options

# --- Placement Groups ---
# label: ec2
awscli ec2 describe-placement-groups

# --- Create Snapshot (placeholder volume — may NotFound, tests API parsing) ---
# label: ec2
awscli ec2 create-volume --availability-zone us-east-1a --size 1 --volume-type gp2


# ==============================================================================
# GitHub-Sourced EC2 CLI Test Cases
# 60 independent test cases scraped from public GitHub repositories
# ==============================================================================
#
# Sources:
#  [1]  github.com/swoodford/aws
#  [2]  github.com/devdennish/automating-aws-vpc-ec2
#  [3]  github.com/rothgar/advanced-aws-cli-examples
#  [4]  github.com/wes-novack/aws-scripting
#  [5]  github.com/aykhanpashayev/vpc-automation-with-aws-cli
#  [6]  github.com/sagespidy/aws
#  [7]  github.com/steven1096-godaddy/aws-cli-cheatsheet
#  [8]  github.com/balfieri/aws
#  [9]  github.com/deanflyer/vpc
#  [10] github.com/kovarus/aws-cli-create-vpcs
#  [11] github.com/miztiik/AWS-Demos
#  [12] github.com/CaseyLabs/aws-ec2-ebs-automatic-snapshot-bash
#  [13] github.com/davidclin/aws-cli-get-security-groups
#  [14] github.com/cotigao/aws-sg-ip-rule
#  [15] github.com/akshaynarang2011/Repos
#  [16] github.com/Thareja/AWS-Create-VPC-Shell-Script

# ==============================================================================
# VPC Operations (TC01-TC10)
# ==============================================================================

# --- TC01: List all VPCs [1] ---
# label: ec2
awscli ec2 describe-vpcs
# label: ec2
awscli ec2 describe-vpcs --query 'Vpcs[].{VPCID:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value|[0]}' --output table

# --- TC02: Filter VPCs by tag [1][3] ---
# label: ec2
awscli ec2 describe-vpcs --filters Name=tag:Name,Values=mock-vpc --query 'Vpcs[].VpcId' --output text

# --- TC03: Create VPC with CIDR [2] ---
# label: ec2
awscli ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text

# --- TC04: Create VPC with tag-specifications [5][9] ---
# label: ec2
awscli ec2 create-vpc --cidr-block 172.16.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=test-labeled-vpc}]' --query 'Vpc.VpcId' --output text

# --- TC05: Modify VPC attributes [2][5] ---
# label: ec2
awscli ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text

# --- TC06: List subnets with query [7][9] ---
# label: ec2
awscli ec2 describe-subnets
# label: ec2
awscli ec2 describe-subnets --query 'Subnets[].{VPC_id:VpcId,SUB_id:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,AutoIP:MapPublicIpOnLaunch,Name:Tags[?Key==`Name`].Value|[0]}' --output table

# --- TC07: Filter subnets by VPC [9][10] ---
# label: ec2
awscli ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-0123456789abcdef0" --query 'Subnets[].SubnetId' --output text

# --- TC08: Describe route tables with complex query [5] ---
# label: ec2
awscli ec2 describe-route-tables
# label: ec2
awscli ec2 describe-route-tables --query 'RouteTables[*].{rt_id:RouteTableId,Vpc_id:VpcId,Main:Associations[].Main|[0],Routes:Routes}'

# --- TC09: Route table — filter main RT of a VPC [10] ---
# label: ec2
awscli ec2 describe-route-tables --filters Name=association.main,Values=true --query 'RouteTables[*].{RouteTableId:RouteTableId,VpcId:VpcId}' --output text

# --- TC10: Describe route table non-default routes [5] ---
# label: ec2
awscli ec2 describe-route-tables --query "RouteTables[].Routes[?Origin!='CreateRouteTable'].{Dest:DestinationCidrBlock,Target:GatewayId}" --output table

# ==============================================================================
# Internet Gateway & NAT (TC11-TC14)
# ==============================================================================

# --- TC11: List internet gateways [9] ---
# label: ec2
awscli ec2 describe-internet-gateways
# label: ec2
awscli ec2 describe-internet-gateways --query 'InternetGateways[].{Igw_id:InternetGatewayId,Vpc_id:Attachments[].VpcId|[0],State:Attachments[].State|[0]}'

# --- TC12: Create internet gateway [9][11] ---
# label: ec2
awscli ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text

# --- TC13: NAT gateway listing [10][15] ---
# label: ec2
awscli ec2 describe-nat-gateways
# label: ec2
awscli ec2 describe-nat-gateways --query 'NatGateways[*].{ID:NatGatewayId,State:State,SubnetId:SubnetId}' --output table

# --- TC14: VPC endpoints [5] ---
# label: ec2
awscli ec2 describe-vpc-endpoints
# label: ec2
awscli ec2 describe-vpc-endpoints --query 'VpcEndpoints[].{ID:VpcEndpointId,Service:ServiceName,Type:VpcEndpointType,State:State}'

# ==============================================================================
# Security Groups (TC15-TC25)
# ==============================================================================

# --- TC15: List all security groups [13] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[*].GroupId' --output text
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[*].[Description,GroupId,GroupName,OwnerId,VpcId]' --output text

# --- TC16: SG with detailed rules query [1] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[].{SG_id:GroupId,Name:GroupName,Vpc_id:VpcId,Rules:IpPermissions[].{SourceCIDR:IpRanges[].CidrIp|[0],fromport:FromPort,ToPort:ToPort,Protocol:IpProtocol}}'

# --- TC17: SG — list group IDs and VPC IDs [8] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId]' --output text
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[*].[VpcId]' --output text

# --- TC18: Filter SGs by VPC [1][9] ---
# label: ec2
awscli ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-0123456789abcdef0" --output json

# --- TC19: Filter SGs by group name [9] ---
# label: ec2
awscli ec2 describe-security-groups --filters Name=group-name,Values=default --query 'SecurityGroups[].{GroupId:GroupId,GroupName:GroupName}'

# --- TC20: Create security group [6][16] ---
# label: ec2
awscli ec2 create-security-group --group-name test-sg-github-01 --description "Security group from github test cases"

# --- TC21: Create SG with VPC (create VPC first) [2][11] ---
# label: ec2
awscli ec2 create-security-group --group-name test-sg-github-02 --description "SG for VPC testing"

# --- TC22: SG — filter by owner-id [13] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[*].{GroupId:GroupId,GroupName:GroupName,OwnerId:OwnerId}' --output table

# --- TC23: SG — IpPermissions detail query [1][14] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[].{SG:GroupId,Rules:IpPermissions[].{Proto:IpProtocol,From:FromPort,To:ToPort,CIDR:IpRanges[].CidrIp|[0]}}'

# --- TC24: SG — Egress rules query [8] ---
# label: ec2
awscli ec2 describe-security-groups --query 'SecurityGroups[].{SG:GroupId,Egress:IpPermissionsEgress[].{Proto:IpProtocol,From:FromPort,To:ToPort}}'

# --- TC25: SG — filter by description keyword [7] ---
# label: ec2
awscli ec2 describe-security-groups --filters "Name=description,Values=*default*" --query 'SecurityGroups[].{GroupId:GroupId,Description:Description}' --output table

# ==============================================================================
# Instance Queries (TC26-TC35)
# ==============================================================================

# --- TC26: Describe all instances [3] ---
# label: ec2
awscli ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,PublicIpAddress]' --output text

# --- TC27: Instance with Name tag query [3] ---
# label: ec2
awscli ec2 describe-instances --query 'Reservations[].Instances[].[[Tags[?Key==`Name`].Value][0][0],InstanceId]' --output text

# --- TC28: Running instances filter [3][4] ---
# label: ec2
awscli ec2 describe-instances --filter "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].[[Tags[?Key==`Name`].Value][0][0],InstanceId]' --output text

# --- TC29: Filter instances by private IP [4] ---
# label: ec2
awscli ec2 describe-instances --filter Name=private-ip-address,Values="10.0.1.50" --query "Reservations[].Instances[].InstanceId" --output text

# --- TC30: Filter instances by tag name [4] ---
# label: ec2
awscli ec2 describe-instances --filter Name=tag:Name,Values="my-instance" --query "Reservations[].Instances[].PrivateIpAddress" --output text

# --- TC31: Instance type filter [8] ---
# label: ec2
awscli ec2 describe-instances --filters "Name=instance-type,Values=t2.micro" --query 'Reservations[*].Instances[*].[InstanceId,LaunchTime,State.Name,InstanceType,ImageId,Placement.AvailabilityZone]' --output text

# --- TC32: Instance deep attribute queries [8] ---
# label: ec2
awscli ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,State:State.Name,AZ:Placement.AvailabilityZone,VPC:VpcId,Subnet:SubnetId}' --output table

# --- TC33: Instance status listing [existing] ---
# label: ec2
awscli ec2 describe-instance-status
# label: ec2
awscli ec2 describe-instance-status --include-all-instances

# --- TC34: Free-tier instance types [existing] ---
# label: ec2
awscli ec2 describe-instance-types --filters "Name=free-tier-eligible,Values=true" "Name=current-generation,Values=true" --query 'InstanceTypes[].{Instance:InstanceType,Memory:MemoryInfo.SizeInMiB,Ghz:ProcessorInfo.SustainedClockSpeedInGhz,VirType:SupportedVirtualizationTypes|[0]}'

# --- TC35: Instance SecurityGroups and KeyName query [8] ---
# label: ec2
awscli ec2 describe-instances --query 'Reservations[*].Instances[*].SecurityGroups[*].[GroupId]' --output text
# label: ec2
awscli ec2 describe-instances --query 'Reservations[*].Instances[*].Placement.AvailabilityZone' --output text

# ==============================================================================
# Images / AMI (TC36-TC40)
# ==============================================================================

# --- TC36: Describe images — Amazon owner [8] ---
# label: ec2
awscli ec2 describe-images --owners amazon --query 'Images[:5].{ID:ImageId,Name:Name}' --output table

# --- TC37: Amazon Linux 2 AMI with date filter [8][9] ---
# label: ec2
awscli ec2 describe-images --owners amazon --filters 'Name=name,Values=amzn2-ami-hvm-2.0.????????.?-x86_64-gp2' 'Name=state,Values=available' --query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' --output text

# --- TC38: RHEL images query [1] ---
# label: ec2
awscli ec2 describe-images --owners 309956199498 --filters 'Name=name,Values=RHEL-8.*' 'Name=state,Values=available' --query 'reverse(sort_by(Images, &CreationDate))[:1].{Name:Name,Ami:ImageId,Created:CreationDate}' --output table

# --- TC39: Image attributes [8] ---
# label: ec2
awscli ec2 describe-images --owners 123456789012 --query 'Images[*].{ID:ImageId,Time:CreationDate}' --output text

# --- TC40: Image state query [8] ---
# label: ec2
awscli ec2 describe-images --owners self --query 'Images[*].{ID:ImageId,State:State,Arch:Architecture}'

# ==============================================================================
# Volumes & Snapshots (TC41-TC46)
# ==============================================================================

# --- TC41: List volumes with query [8] ---
# label: ec2
awscli ec2 describe-volumes
# label: ec2
awscli ec2 describe-volumes --query 'Volumes[*].{ID:VolumeId,Size:Size,State:State,AZ:AvailabilityZone,Encrypted:Encrypted}' --output table

# --- TC42: Volumes filtered by tag [1] ---
# label: ec2
awscli ec2 describe-volumes --filter Name=tag:Backup,Values="1"

# --- TC43: Create volume [8] ---
# label: ec2
awscli ec2 create-volume --availability-zone us-east-1a --size 1 --volume-type gp2

# --- TC44: Snapshot listing by owner [12] ---
# label: ec2
awscli ec2 describe-snapshots --owner-ids self
# label: ec2
awscli ec2 describe-snapshots --owner-ids self --query 'Snapshots[*].{ID:SnapshotId,Vol:VolumeId,State:State,Time:StartTime}' --output table

# --- TC45: Snapshots with tag filters [1][12] ---
# label: ec2
awscli ec2 describe-snapshots --owner-ids self --filters "Name=tag:CreatedBy,Values=AutomatedBackup" --query 'Snapshots[].SnapshotId' --output text

# --- TC46: Snapshot with volume-id filter [12] ---
# label: ec2
awscli ec2 describe-snapshots --filters "Name=volume-id,Values=vol-0123456789abcdef0" --query 'Snapshots[*].{ID:SnapshotId,Time:StartTime}' --output text

# ==============================================================================
# Key Pairs, Elastic IP, Network (TC47-TC52)
# ==============================================================================

# --- TC47: Create and list key pairs [9][6] ---
# label: ec2
awscli ec2 create-key-pair --key-name test-key-github-01 --query 'KeyName' --output text
# label: ec2
awscli ec2 describe-key-pairs

# --- TC48: Allocate elastic IP [6][10] ---
# label: ec2
awscli ec2 allocate-address --domain vpc
# label: ec2
awscli ec2 describe-addresses

# --- TC49: Network ACL listing [existing] ---
# label: ec2
awscli ec2 describe-network-acls
# label: ec2
awscli ec2 describe-network-acls --query 'NetworkAcls[].{ID:NetworkAclId,VpcId:VpcId,IsDefault:IsDefault}'

# --- TC50: Network interfaces [1] ---
# label: ec2
awscli ec2 describe-network-interfaces
# label: ec2
awscli ec2 describe-network-interfaces --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,VPC:VpcId,Subnet:SubnetId,Status:Status}'

# --- TC51: Availability zones [8][9] ---
# label: ec2
awscli ec2 describe-availability-zones
# label: ec2
awscli ec2 describe-availability-zones --query 'AvailabilityZones[*].{Zone:ZoneName,State:State,Region:RegionName}' --output table

# --- TC52: Tags and regions [1][8] ---
# label: ec2
awscli ec2 describe-tags
# label: ec2
awscli ec2 describe-regions --query 'Regions[*].RegionName' --output text

# ==============================================================================
# Create Resources (TC53-TC55)
# ==============================================================================

# --- TC53: Create VPC for peering scenario [11] ---
# label: ec2
awscli ec2 create-vpc --cidr-block 10.0.1.0/24 --query 'Vpc.VpcId' --output text

# --- TC54: Create security group for testing [11] ---
# label: ec2
awscli ec2 create-security-group --group-name pubSecGrp-test --description "Security Group for public instances"

# --- TC55: DHCP options and placement [existing] ---
# label: ec2
awscli ec2 describe-dhcp-options
# label: ec2
awscli ec2 describe-placement-groups

# ==============================================================================
# Non-EC2 Commands with Augmented EC2 Equivalents (TC56-TC60)
# ==============================================================================

# --- TC56: SSM parameter → describe-images [1] ---
# label: non-ec2
awscli ssm get-parameters --names /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2 --region us-east-1
# label: augmented-ec2
awscli ec2 describe-images --owners amazon --filters 'Name=name,Values=amzn2-ami-hvm-*' 'Name=state,Values=available' --query 'Images[:1].ImageId' --output text

# --- TC57: STS identity → describe-account-attributes [1] ---
# label: non-ec2
awscli sts get-caller-identity
# label: augmented-ec2
awscli ec2 describe-account-attributes

# --- TC58: ELB describe → describe-instances [1] ---
# label: non-ec2
awscli elb describe-load-balancers --load-balancer-names test-elb
# label: augmented-ec2
awscli ec2 describe-instances --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}' --output table

# --- TC59: IAM list-users → describe-key-pairs [7] ---
# label: non-ec2
awscli iam list-users
# label: augmented-ec2
awscli ec2 describe-key-pairs --query 'KeyPairs[].{Name:KeyName,ID:KeyPairId}' --output table

# --- TC60: CloudWatch describe-alarms → describe-instance-status [1][7] ---
# label: non-ec2
awscli cloudwatch describe-alarms
# label: augmented-ec2
awscli ec2 describe-instance-status --include-all-instances --query 'InstanceStatuses[].{ID:InstanceId,State:InstanceState.Name,System:SystemStatus.Status,Instance:InstanceStatus.Status}'
