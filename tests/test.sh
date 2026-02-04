aws --endpoint-url=http://localhost:4566 ec2 accept-address-transfer --address 100.21.184.216
aws --endpoint-url=http://localhost:4566 ec2 advertise-byoip-cidr --cidr 203.0.113.25/24
aws --endpoint-url=http://localhost:4566 ec2 allocate-address
aws --endpoint-url=http://localhost:4566 ec2 allocate-address --network-border-group us-west-2-lax-1
aws --endpoint-url=http://localhost:4566 ec2 allocate-address --public-ipv4-pool ipv4pool-ec2-1234567890abcdef0
aws --endpoint-url=http://localhost:4566 ec2 allocate-hosts --instance-type m5.large --availability-zone eu-west-1a --quantity 1
aws --endpoint-url=http://localhost:4566 ec2 allocate-hosts --instance-type m5.large --availability-zone eu-west-1a --auto-placement on --host-recovery on --quantity 1
aws --endpoint-url=http://localhost:4566 ec2 allocate-hosts --instance-type m5.large --availability-zone eu-west-1a --quantity 1 --tag-specifications 'ResourceType=dedicated-host,Tags={Key=purpose,Value=production}'
aws --endpoint-url=http://localhost:4566 ec2 associate-address
aws --endpoint-url=http://localhost:4566 ec2 create-capacity-reservation --availability-zone eu-west-1a --instance-type t2.medium --instance-platform Linux/UNIX --instance-count 3
aws --endpoint-url=http://localhost:4566 ec2 create-capacity-reservation --availability-zone eu-west-1a --instance-type m5.large --instance-platform Linux/UNIX --instance-count 3 --end-date-type limited --end-date 2019-08-31T23:59:59Z
aws --endpoint-url=http://localhost:4566 ec2 create-capacity-reservation --availability-zone eu-west-1a --instance-type m5.large --instance-platform Linux/UNIX --instance-count 3 --instance-match-criteria targeted
aws --endpoint-url=http://localhost:4566 ec2 create-customer-gateway --type ipsec.1 --public-ip 12.1.2.3 --bgp-asn 65534
aws --endpoint-url=http://localhost:4566 ec2 create-default-subnet --availability-zone us-east-2a
aws --endpoint-url=http://localhost:4566 ec2 create-default-vpc
aws --endpoint-url=http://localhost:4566 ec2 create-dhcp-options --dhcp-configuration "Key=domain-name-servers,Values=10.2.5.1,10.2.5.2" "Key=domain-name,Values=example.com" "Key=netbios-node-type,Values=2"
aws --endpoint-url=http://localhost:4566 ec2 create-fpga-image --name my-afi --description test-afi --input-storage-location Bucket=my-fpga-bucket,Key=dcp/17_12_22-103226.Developer_CL.tar --logs-storage-location Bucket=my-fpga-bucket,Key=logs
aws --endpoint-url=http://localhost:4566 ec2 create-instance-event-window --region us-east-1 --time-range StartWeekDay=monday,StartHour=2,EndWeekDay=wednesday,EndHour=8 --tag-specifications "ResourceType=instance-event-window,Tags=[{Key=K1,Value=V1}]" --name myEventWindowName
aws --endpoint-url=http://localhost:4566 ec2 create-instance-event-window --region us-east-1 --cron-expression "* 21-23 * * 2,3" --tag-specifications "ResourceType=instance-event-window,Tags=[{Key=K1,Value=V1}]" --name myEventWindowName
aws --endpoint-url=http://localhost:4566 ec2 create-internet-gateway --tag-specifications ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]
aws --endpoint-url=http://localhost:4566 ec2 create-ipam-resource-discovery --description 'Example-resource-discovery' --tag-specifications 'ResourceType=ipam-resource-discovery,Tags=[{Key=cost-center,Value=cc123}]' --operating-regions RegionName='us-west-1' RegionName='us-west-2' --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 create-ipam --description "Example description" --operating-regions "RegionName=us-east-2" "RegionName=us-west-1" --tag-specifications 'ResourceType=ipam,Tags=[{Key=Name,Value=ExampleIPAM}]'
aws --endpoint-url=http://localhost:4566 ec2 create-ipam --description "Example description" --operating-regions "RegionName=us-east-2" "RegionName=us-west-1" --tag-specifications ResourceType=ipam,Tags=[{Key=Name,Value=ExampleIPAM}]
aws --endpoint-url=http://localhost:4566 ec2 create-key-pair --key-name MyKeyPair
aws --endpoint-url=http://localhost:4566 ec2 create-launch-template --launch-template-name TemplateForWebServer --version-description WebVersion1 --launch-template-data '{"NetworkInterfaces":[{"AssociatePublicIpAddress":true,"DeviceIndex":0,"Ipv6AddressCount":1,"SubnetId":"subnet-7b16de0c"}],"ImageId":"ami-8c1be5f6","InstanceType":"t2.small","TagSpecifications":[{"ResourceType":"instance","Tags":[{"Key":"purpose","Value":"webserver"}]}]}'
aws --endpoint-url=http://localhost:4566 ec2 create-launch-template --launch-template-name TemplateForAutoScaling --version-description AutoScalingVersion1 --launch-template-data '{"NetworkInterfaces":[{"DeviceIndex":0,"AssociatePublicIpAddress":true,"Groups":["sg-7c227019,sg-903004f8"],"DeleteOnTermination":true}],"ImageId":"ami-b42209de","InstanceType":"m4.large","TagSpecifications":[{"ResourceType":"instance","Tags":[{"Key":"environment","Value":"production"},{"Key":"purpose","Value":"webserver"}]},{"ResourceType":"volume","Tags":[{"Key":"environment","Value":"production"},{"Key":"cost-center","Value":"cc123"}]}],"BlockDeviceMappings":[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100}}]}' --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 create-managed-prefix-list --address-family IPv4 --max-entries 10 --entries Cidr=10.0.0.0/16,Description=vpc-a Cidr=10.2.0.0/16,Description=vpc-b --prefix-list-name vpc-cidrs
aws --endpoint-url=http://localhost:4566 ec2 create-network-insights-path --source igw-0797cccdc9d73b0e5 --destination i-0495d385ad28331c7 --destination-port 22 --protocol TCP
aws --endpoint-url=http://localhost:4566 ec2 create-placement-group --group-name my-cluster --strategy cluster
aws --endpoint-url=http://localhost:4566 ec2 create-placement-group --group-name HDFS-Group-A --strategy partition --partition-count 5
aws --endpoint-url=http://localhost:4566 ec2 create-restore-image-task --object-key ami-1234567890abcdef0.bin --bucket my-ami-bucket --name 'New AMI Name'
aws --endpoint-url=http://localhost:4566 ec2 create-security-group --group-name MySecurityGroup --description "My security group"
aws --endpoint-url=http://localhost:4566 ec2 create-snapshots --instance-specification InstanceId=i-1234567890abcdef0 --description "This is snapshot of a volume from my-instance"
aws --endpoint-url=http://localhost:4566 ec2 create-snapshots --instance-specification InstanceId=i-1234567890abcdef0 --copy-tags-from-source volume --description "This is snapshot of a volume from my-instance"
aws --endpoint-url=http://localhost:4566 ec2 create-snapshots --instance-specification InstanceId=i-1234567890abcdef0,ExcludeBootVolume=true
aws --endpoint-url=http://localhost:4566 ec2 create-snapshots --instance-specification InstanceId=i-1234567890abcdef0 --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=backup},{Key=costcenter,Value=123}]'
aws --endpoint-url=http://localhost:4566 ec2 create-spot-datafeed-subscription --bucket amzn-s3-demo-bucket --prefix spot-data-feed
aws --endpoint-url=http://localhost:4566 ec2 create-traffic-mirror-filter --description 'TCP Filter'
aws --endpoint-url=http://localhost:4566 ec2 create-transit-gateway --description MyTGW --options AmazonSideAsn=64516,AutoAcceptSharedAttachments=enable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable
aws --endpoint-url=http://localhost:4566 ec2 create-verified-access-instance --tag-specifications ResourceType=verified-access-instance,Tags=[{Key=Name,Value=my-va-instance}]
aws --endpoint-url=http://localhost:4566 ec2 create-verified-access-trust-provider --trust-provider-type user --user-trust-provider-type iam-identity-center --policy-reference-name idc --tag-specifications ResourceType=verified-access-trust-provider,Tags=[{Key=Name,Value=my-va-trust-provider}]
aws --endpoint-url=http://localhost:4566 ec2 create-volume --volume-type gp2 --size 80 --availability-zone us-east-1a
aws --endpoint-url=http://localhost:4566 ec2 create-volume --size 80 --availability-zone us-east-1a
aws --endpoint-url=http://localhost:4566 ec2 create-volume --size 80 --encrypted --availability-zone us-east-1a
aws --endpoint-url=http://localhost:4566 ec2 create-volume --size 80 --availability-zone us-east-1a
aws --endpoint-url=http://localhost:4566 ec2 create-volume --availability-zone us-east-1a --volume-type gp2 --size 80 --tag-specifications 'ResourceType=volume,Tags=[{Key=purpose,Value=production},{Key=cost-center,Value=cc123}]'
aws --endpoint-url=http://localhost:4566 ec2 create-vpc-endpoint-service-configuration --network-load-balancer-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/nlb-vpce/e94221227f1ba532 --acceptance-required
aws --endpoint-url=http://localhost:4566 ec2 create-vpc-endpoint-service-configuration --gateway-load-balancer-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/gwy/GWLBService/123123123123abcc --no-acceptance-required
aws --endpoint-url=http://localhost:4566 ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications ResourceType=vpc,Tags=[{Key=Name,Value=MyVpc}]
aws --endpoint-url=http://localhost:4566 ec2 create-vpc --cidr-block 10.0.0.0/16 --instance-tenancy dedicated
aws --endpoint-url=http://localhost:4566 ec2 create-vpc --cidr-block 10.0.0.0/16 --amazon-provided-ipv6-cidr-block
aws --endpoint-url=http://localhost:4566 ec2 create-vpn-gateway --type ipsec.1
aws --endpoint-url=http://localhost:4566 ec2 create-vpn-gateway --type ipsec.1 --amazon-side-asn 65001
aws --endpoint-url=http://localhost:4566 ec2 delete-key-pair --key-name my-key-pair
aws --endpoint-url=http://localhost:4566 ec2 delete-placement-group --group-name my-cluster
aws --endpoint-url=http://localhost:4566 ec2 delete-security-group --group-name MySecurityGroup
aws --endpoint-url=http://localhost:4566 ec2 delete-spot-datafeed-subscription
aws --endpoint-url=http://localhost:4566 ec2 deprovision-byoip-cidr --cidr 203.0.113.25/24
aws --endpoint-url=http://localhost:4566 ec2 deregister-instance-event-notification-attributes --instance-tag-attribute IncludeAllTagsOfInstance=true
aws --endpoint-url=http://localhost:4566 ec2 deregister-instance-event-notification-attributes --instance-tag-attribute InstanceTagKeys="tag-key2"
aws --endpoint-url=http://localhost:4566 ec2 describe-account-attributes
aws --endpoint-url=http://localhost:4566 ec2 describe-account-attributes --attribute-names supported-platforms
aws --endpoint-url=http://localhost:4566 ec2 describe-addresses
aws --endpoint-url=http://localhost:4566 ec2 describe-addresses --filters "Name=domain,Values=vpc"
aws --endpoint-url=http://localhost:4566 ec2 describe-addresses --filters "Name=private-ip-address,Values=10.251.50.12"
aws --endpoint-url=http://localhost:4566 ec2 describe-addresses --filters "Name=domain,Values=standard"
aws --endpoint-url=http://localhost:4566 ec2 describe-addresses --public-ips 203.0.110.25
aws --endpoint-url=http://localhost:4566 ec2 describe-aggregate-id-format
aws --endpoint-url=http://localhost:4566 ec2 describe-availability-zones
aws --endpoint-url=http://localhost:4566 ec2 describe-aws-network-performance-metric-subscriptions
aws --endpoint-url=http://localhost:4566 ec2 describe-aws-network-performance-metric-subscriptions
aws --endpoint-url=http://localhost:4566 ec2 describe-bundle-tasks
aws --endpoint-url=http://localhost:4566 ec2 describe-byoip-cidrs
aws --endpoint-url=http://localhost:4566 ec2 describe-capacity-reservations
aws --endpoint-url=http://localhost:4566 ec2 describe-carrier-gateways
aws --endpoint-url=http://localhost:4566 ec2 describe-classic-link-instances
aws --endpoint-url=http://localhost:4566 ec2 describe-classic-link-instances --filter "Name=vpc-id,Values=vpc-88888888"
aws --endpoint-url=http://localhost:4566 ec2 describe-client-vpn-endpoints
aws --endpoint-url=http://localhost:4566 ec2 describe-coip-pools
aws --endpoint-url=http://localhost:4566 ec2 describe-customer-gateways
aws --endpoint-url=http://localhost:4566 ec2 describe-dhcp-options
aws --endpoint-url=http://localhost:4566 ec2 describe-dhcp-options --filters Name=key,Values=domain-name-servers Name=value,Values=example.com --query "DhcpOptions[*].[DhcpConfigurations,DhcpOptionsId]"
aws --endpoint-url=http://localhost:4566 ec2 describe-egress-only-internet-gateways
aws --endpoint-url=http://localhost:4566 ec2 describe-fast-launch-images
aws --endpoint-url=http://localhost:4566 ec2 describe-fast-snapshot-restores --filters Name=state,Values=disabled
aws --endpoint-url=http://localhost:4566 ec2 describe-fast-snapshot-restores
aws --endpoint-url=http://localhost:4566 ec2 describe-flow-logs
aws --endpoint-url=http://localhost:4566 ec2 describe-flow-logs --filter "Name=log-group-name,Values=MyFlowLogs"
aws --endpoint-url=http://localhost:4566 ec2 describe-fpga-images --filters Name=owner-id,Values=123456789012
aws --endpoint-url=http://localhost:4566 ec2 describe-host-reservation-offerings --filter Name=instance-family,Values=m4
aws --endpoint-url=http://localhost:4566 ec2 describe-host-reservations
aws --endpoint-url=http://localhost:4566 ec2 describe-hosts --filter "Name=state,Values=available"
aws --endpoint-url=http://localhost:4566 ec2 describe-iam-instance-profile-associations
aws --endpoint-url=http://localhost:4566 ec2 describe-id-format --resource security-group
aws --endpoint-url=http://localhost:4566 ec2 describe-id-format
aws --endpoint-url=http://localhost:4566 ec2 describe-images --owners amazon --filters "Name=platform,Values=windows" "Name=root-device-type,Values=ebs"
aws --endpoint-url=http://localhost:4566 ec2 describe-images --filters "Name=tag:Type,Values=Custom" --query 'Images[*].[ImageId]' --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-event-notification-attributes
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-event-windows --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-event-windows --region us-east-1 --filters Name=instance-id,Values=i-1234567890abcdef0 --max-results 100 --next-token <next-token-value>
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-image-metadata --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-image-metadata --region us-east-1 --filters Name=availability-zone,Values=us-east-1a Name=instance-type,Values=t2.nano,t2.micro
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-topology --region us-west-2
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-type-offerings
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-type-offerings --region us-east-2
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=location,Values=us-east-2a --region us-east-2
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-type-offerings --filters Name=instance-type,Values=c5.xlarge --region us-east-2
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-type-offerings --filters Name=instance-type,Values=c5* --query "InstanceTypeOfferings[].InstanceType" --region us-east-2
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-types --instance-types t2.micro
aws --endpoint-url=http://localhost:4566 ec2 describe-instance-types --filters Name=hibernation-supported,Values=true --query 'InstanceTypes[*].InstanceType'
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters Name=instance-type,Values=m5.large
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters Name=instance-type,Values=t2.micro,t3.micro Name=availability-zone,Values=us-east-2c
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=tag-key,Values=Owner"
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=tag-value,Values=my-team"
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=tag:Owner,Values=my-team"
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --query 'Reservations[*].Instances[*].{Instance:InstanceId,Subnet:SubnetId}' --output json
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --query "Reservations[*].Instances[*].{Instance:InstanceId,Subnet:SubnetId}" --output json
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=instance-type,Values=t2.micro" --query "Reservations[*].Instances[*].[InstanceId]" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters Name=tag-key,Values=Name --query 'Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key==\Name\]|[0].Value}' --output table
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters Name=tag-key,Values=Name --query "Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key=='Name']|[0].Value}" --output table
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=placement-group-name,Values=HDFS-Group-A" "Name=placement-partition-number,Values=7"
aws --endpoint-url=http://localhost:4566 ec2 describe-instances --filters "Name=metadata-options.instance-metadata-tags,Values=enabled" --query "Reservations[*].Instances[*].InstanceId" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-pools --filters Name=owner-id,Values=123456789012 Name=ipam-scope-id,Values=ipam-scope-02fc38cd4c48e7d38
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-pools --filters Name=owner-id,Values=123456789012 Name=ipam-scope-id,Values=ipam-scope-02fc38cd4c48e7d38
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-resource-discoveries --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-resource-discoveries --query "IpamResourceDiscoveries[*].IpamResourceDiscoveryId" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-resource-discovery-associations --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-ipam-scopes --filters Name=owner-id,Values=123456789012 Name=ipam-id,Values=ipam-08440e7a3acde3908
aws --endpoint-url=http://localhost:4566 ec2 describe-ipams --filters Name=owner-id,Values=123456789012
aws --endpoint-url=http://localhost:4566 ec2 describe-ipv6-pools
aws --endpoint-url=http://localhost:4566 ec2 describe-key-pairs --key-names my-key-pair
aws --endpoint-url=http://localhost:4566 ec2 describe-launch-templates
aws --endpoint-url=http://localhost:4566 ec2 describe-local-gateway-route-table-virtual-interface-group-associations
aws --endpoint-url=http://localhost:4566 ec2 describe-local-gateway-route-tables
aws --endpoint-url=http://localhost:4566 ec2 describe-local-gateway-virtual-interface-groups
aws --endpoint-url=http://localhost:4566 ec2 describe-local-gateway-virtual-interfaces
aws --endpoint-url=http://localhost:4566 ec2 describe-local-gateways
aws --endpoint-url=http://localhost:4566 ec2 describe-managed-prefix-lists --filters Name=owner-id,Values=123456789012
aws --endpoint-url=http://localhost:4566 ec2 describe-moving-addresses
aws --endpoint-url=http://localhost:4566 ec2 describe-moving-addresses --filters Name=moving-status,Values=MovingToVpc
aws --endpoint-url=http://localhost:4566 ec2 describe-network-acls
aws --endpoint-url=http://localhost:4566 ec2 describe-network-insights-access-scope-analyses --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-network-insights-access-scopes --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 describe-network-interface-permissions
aws --endpoint-url=http://localhost:4566 ec2 describe-network-interfaces
aws --endpoint-url=http://localhost:4566 ec2 describe-network-interfaces --filters Name=tag:Purpose,Values=Prod
aws --endpoint-url=http://localhost:4566 ec2 describe-placement-groups
aws --endpoint-url=http://localhost:4566 ec2 describe-prefix-lists
aws --endpoint-url=http://localhost:4566 ec2 describe-principal-id-format --resource instance
aws --endpoint-url=http://localhost:4566 ec2 describe-public-ipv4-pools
aws --endpoint-url=http://localhost:4566 ec2 describe-regions
aws --endpoint-url=http://localhost:4566 ec2 describe-regions --filters "Name=endpoint,Values=*us*"
aws --endpoint-url=http://localhost:4566 ec2 describe-regions --all-regions
aws --endpoint-url=http://localhost:4566 ec2 describe-regions --all-regions --query "Regions[].{Name:RegionName}" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-replace-root-volume-tasks --filters Name=instance-id,Values=i-0123456789abcdefa
aws --endpoint-url=http://localhost:4566 ec2 describe-reserved-instances-modifications
aws --endpoint-url=http://localhost:4566 ec2 describe-reserved-instances-offerings
aws --endpoint-url=http://localhost:4566 ec2 describe-reserved-instances-offerings --no-include-marketplace --instance-type "t1.micro" --product-description "Windows (Amazon VPC)" --offering-type "no upfront"
aws --endpoint-url=http://localhost:4566 ec2 describe-reserved-instances
aws --endpoint-url=http://localhost:4566 ec2 describe-reserved-instances --filters Name=duration,Values=94608000 Name=instance-type,Values=t2.micro Name=product-description,Values=Linux/UNIX Name=availability-zone,Values=us-east-1e
aws --endpoint-url=http://localhost:4566 ec2 describe-route-tables
aws --endpoint-url=http://localhost:4566 ec2 describe-scheduled-instance-availability --recurrence Frequency=Weekly,Interval=1,OccurrenceDays=[1] --first-slot-start-time-range EarliestTime=2016-01-31T00:00:00Z,LatestTime=2016-01-31T04:00:00Z
aws --endpoint-url=http://localhost:4566 ec2 describe-scheduled-instances
aws --endpoint-url=http://localhost:4566 ec2 describe-security-group-rules --filters Name="group-id",Values="sg-1234567890abcdef0"
aws --endpoint-url=http://localhost:4566 ec2 describe-security-group-vpc-associations --filters Name=group-id,Values=sg-04dbb43907d3f8a78
aws --endpoint-url=http://localhost:4566 ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22 Name=ip-permission.to-port,Values=22 Name=ip-permission.cidr,Values='0.0.0.0/0' --query "SecurityGroups[*].[GroupName]" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-security-groups --filters Name=group-name,Values=*test* Name=tag:Test,Values=To-delete --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}"
aws --endpoint-url=http://localhost:4566 ec2 describe-snapshot-tier-status --filters "Name=snapshot-id, Values=snap-01234567890abcedf"
aws --endpoint-url=http://localhost:4566 ec2 describe-snapshots --filters Name=volume-id,Values=049df61146c4d7901 --query "Snapshots[*].[SnapshotId]" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-snapshots --filters Name=tag:Stack,Values=prod
aws --endpoint-url=http://localhost:4566 ec2 describe-snapshots --filters "Name=storage-tier,Values=archive"
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-datafeed-subscription
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-fleet-requests
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-instance-requests --filters Name=launch.instance-type,Values=m3.medium Name=launched-availability-zone,Values=us-east-2a --query "SpotInstanceRequests[*].[InstanceId]" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-instance-requests --filters Name=tag:cost-center,Values=cc123
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-price-history --instance-types m1.xlarge --start-time 2014-01-06T07:08:09 --end-time 2014-01-06T08:09:10
aws --endpoint-url=http://localhost:4566 ec2 describe-spot-price-history --instance-types m1.xlarge --product-description "Linux/UNIX (Amazon VPC)" --start-time 2014-01-06T07:08:09 --end-time 2014-01-06T08:09:10
aws --endpoint-url=http://localhost:4566 ec2 describe-store-image-tasks
aws --endpoint-url=http://localhost:4566 ec2 describe-subnets
aws --endpoint-url=http://localhost:4566 ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-3EXAMPLE"
aws --endpoint-url=http://localhost:4566 ec2 describe-subnets --filters "Name=tag:CostCenter,Values=123" --query "Subnets[*].SubnetId" --output text
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters "Name=resource-id,Values=i-1234567890abcdef8"
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters "Name=resource-type,Values=volume"
aws --endpoint-url=http://localhost:4566 ec2 describe-tags
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters Name=key,Values=Stack
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters Name=key,Values=Stack Name=value,Values=Test
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters "Name=tag:Stack,Values=Test"
aws --endpoint-url=http://localhost:4566 ec2 describe-tags --filters "Name=resource-type,Values=instance" "Name=key,Values=Purpose" "Name=value,Values="
aws --endpoint-url=http://localhost:4566 ec2 describe-traffic-mirror-filters
aws --endpoint-url=http://localhost:4566 ec2 describe-traffic-mirror-sessions
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateway-attachments
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateway-multicast-domains
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateway-peering-attachments
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateway-route-tables
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateway-vpc-attachments
aws --endpoint-url=http://localhost:4566 ec2 describe-transit-gateways
aws --endpoint-url=http://localhost:4566 ec2 describe-volume-status --filters Name=volume-status.status,Values=impaired
aws --endpoint-url=http://localhost:4566 ec2 describe-volumes --region us-east-1 --filters Name=attachment.instance-id,Values=i-1234567890abcdef0 Name=attachment.delete-on-termination,Values=true
aws --endpoint-url=http://localhost:4566 ec2 describe-volumes --filters Name=status,Values=available Name=availability-zone,Values=us-east-1a
aws --endpoint-url=http://localhost:4566 ec2 describe-volumes --filters Name=tag:Name,Values=Test* --query "Volumes[*].{ID:VolumeId,Tag:Tags}"
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-classic-link-dns-support
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-classic-link --filter "Name=is-classic-link-enabled,Values=true"
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-associations
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-connection-notifications
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-connections --filters Name=vpc-endpoint-state,Values=pendingAcceptance
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-service-configurations
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-services
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoint-services --filter 'Name=service-type,Values=Interface' Name=service-name,Values=com.amazonaws.us-east-1.s3
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-endpoints
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-peering-connections
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-peering-connections --filters Name=status-code,Values=pending-acceptance
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-peering-connections --filters Name=tag:Owner,Values=Finance
aws --endpoint-url=http://localhost:4566 ec2 describe-vpc-peering-connections --filters Name=requester-vpc-info.vpc-id,Values=vpc-1a2b3c4d
aws --endpoint-url=http://localhost:4566 ec2 describe-vpcs
aws --endpoint-url=http://localhost:4566 ec2 describe-vpn-connections
aws --endpoint-url=http://localhost:4566 ec2 describe-vpn-connections --filters "Name=state,Values=available"
aws --endpoint-url=http://localhost:4566 ec2 describe-vpn-gateways
aws --endpoint-url=http://localhost:4566 ec2 disable-aws-network-performance-metric-subscription --source us-east-1 --destination eu-west-1 --metric aggregate-latency --statistic p50
aws --endpoint-url=http://localhost:4566 ec2 disable-ebs-encryption-by-default
aws --endpoint-url=http://localhost:4566 ec2 disable-image-block-public-access --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 disable-serial-console-access
aws --endpoint-url=http://localhost:4566 ec2 disable-snapshot-block-public-access
aws --endpoint-url=http://localhost:4566 ec2 disassociate-address --public-ip 198.51.100.0
aws --endpoint-url=http://localhost:4566 ec2 enable-aws-network-performance-metric-subscription --source us-east-1 --destination eu-west-1 --metric aggregate-latency --statistic p50
aws --endpoint-url=http://localhost:4566 ec2 enable-ebs-encryption-by-default
aws --endpoint-url=http://localhost:4566 ec2 enable-image-block-public-access --region us-east-1 --image-block-public-access-state block-new-sharing
aws --endpoint-url=http://localhost:4566 ec2 enable-reachability-analyzer-organization-sharing
aws --endpoint-url=http://localhost:4566 ec2 enable-serial-console-access
aws --endpoint-url=http://localhost:4566 ec2 enable-snapshot-block-public-access --state block-all-sharing
aws --endpoint-url=http://localhost:4566 ec2 get-aws-network-performance-data --start-time 2022-10-26T12:00:00.000Z --end-time 2022-10-26T12:30:00.000Z --data-queries Id=my-query,Source=us-east-1,Destination=eu-west-1,Metric=aggregate-latency,Statistic=p50,Period=five-minutes
aws --endpoint-url=http://localhost:4566 ec2 get-default-credit-specification --instance-family t2
aws --endpoint-url=http://localhost:4566 ec2 get-ebs-default-kms-key-id
aws --endpoint-url=http://localhost:4566 ec2 get-ebs-encryption-by-default
aws --endpoint-url=http://localhost:4566 ec2 get-image-block-public-access-state --region us-east-1
aws --endpoint-url=http://localhost:4566 ec2 get-instance-types-from-instance-requirements --region us-east-1 --generate-cli-skeleton input > attributes.json
aws --endpoint-url=http://localhost:4566 ec2 get-serial-console-access-status
aws --endpoint-url=http://localhost:4566 ec2 get-snapshot-block-public-access-state
aws --endpoint-url=http://localhost:4566 ec2 get-spot-placement-scores --region us-east-1 --generate-cli-skeleton input > attributes.json
aws --endpoint-url=http://localhost:4566 ec2 get-vpn-connection-device-types --query "VpnConnectionDeviceTypes[?Vendor==\Palo Alto Networks\]"
aws --endpoint-url=http://localhost:4566 ec2 import-image --disk-containers Format=ova,UserBucket="{S3Bucket=my-import-bucket,S3Key=vms/my-server-vm.ova}"
aws --endpoint-url=http://localhost:4566 ec2 import-key-pair --key-name "my-key" --public-key-material fileb://~/.ssh/my-key.pub
aws --endpoint-url=http://localhost:4566 ec2 import-snapshot --description "My server VMDK" --disk-container Format=VMDK,UserBucket={'S3Bucket=my-import-bucket,S3Key=vms/my-server-vm.vmdk'}
aws --endpoint-url=http://localhost:4566 ec2 list-images-in-recycle-bin
aws --endpoint-url=http://localhost:4566 ec2 modify-availability-zone-group --group-name us-west-2-lax-1 --opt-in-status opted-in
aws --endpoint-url=http://localhost:4566 ec2 modify-default-credit-specification --instance-family t2 --cpu-credits unlimited
aws --endpoint-url=http://localhost:4566 ec2 modify-instance-credit-specification --instance-credit-specification "InstanceId=i-1234567890abcdef0,CpuCredits=unlimited"
aws --endpoint-url=http://localhost:4566 ec2 move-address-to-vpc --public-ip 54.123.4.56
aws --endpoint-url=http://localhost:4566 ec2 provision-byoip-cidr --cidr 203.0.113.25/24 --cidr-authorization-context Message="$text_message",Signature="$signed_message"
aws --endpoint-url=http://localhost:4566 ec2 register-image --name my-image --image-location amzn-s3-demo-bucket/myimage/image.manifest.xml
aws --endpoint-url=http://localhost:4566 ec2 register-image --name my-image --root-device-name /dev/xvda --block-device-mappings DeviceName=/dev/xvda,Ebs={SnapshotId=snap-0db2cf683925d191f} DeviceName=/dev/xvdf,Ebs={VolumeSize=100}
aws --endpoint-url=http://localhost:4566 ec2 register-instance-event-notification-attributes --instance-tag-attribute IncludeAllTagsOfInstance=true
aws --endpoint-url=http://localhost:4566 ec2 register-instance-event-notification-attributes --instance-tag-attribute InstanceTagKeys="tag-key1","tag-key2"
aws --endpoint-url=http://localhost:4566 ec2 release-address --public-ip 198.51.100.0
aws --endpoint-url=http://localhost:4566 ec2 report-instance-status --instances i-1234567890abcdef0 --status impaired --reason-codes unresponsive
aws --endpoint-url=http://localhost:4566 ec2 reset-ebs-default-kms-key-id
aws --endpoint-url=http://localhost:4566 ec2 restore-address-to-classic --public-ip 198.51.100.0
aws --endpoint-url=http://localhost:4566 ec2 revoke-security-group-ingress --group-name mySecurityGroup
aws --endpoint-url=http://localhost:4566 ec2 wait key-pair-exists --key-names my-key-pair
aws --endpoint-url=http://localhost:4566 ec2 wait spot-instance-request-fulfilled --filters Name=launched-availability-zone,Values=us-east-1
aws --endpoint-url=http://localhost:4566 ec2 withdraw-byoip-cidr
