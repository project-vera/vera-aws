from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import re
from ..utils import (get_scalar, get_int, get_indexed_list, parse_filters, apply_filters,
                    parse_tags, str2bool, esc, create_error_response,
                    is_error_response, serialize_error_response)
from ..state import EC2State

class ResourceState(Enum):
    PENDING = 'pending'
    AVAILABLE = 'available'
    RUNNING = 'running'
    STOPPED = 'stopped'
    TERMINATED = 'terminated'
    DELETING = 'deleting'
    DELETED = 'deleted'
    NONEXISTENT = 'non-existent'
    FAILED = 'failed'
    SHUTTING_DOWN = 'shutting-down'
    STOPPING = 'stopping'
    STARTING = 'starting'
    REBOOTING = 'rebooting'
    ATTACHED = 'attached'
    IN_USE = 'in-use'
    CREATING = 'creating'

class ErrorCode(Enum):
    INVALID_PARAMETER_VALUE = 'InvalidParameterValue'
    RESOURCE_NOT_FOUND = 'ResourceNotFound'
    INVALID_STATE_TRANSITION = 'InvalidStateTransition'
    DEPENDENCY_VIOLATION = 'DependencyViolation'

@dataclass
class ElasticNetworkInterface:
    group_id: str = ""
    group_name: str = ""

    network_interface_id: str = ""
    subnet_id: str = ""
    vpc_id: str = ""
    description: str = ""
    status: str = "available"
    mac_address: str = ""
    private_dns_name: str = ""
    private_ip_address: str = ""
    private_ip_addresses: List[Dict[str, Any]] = field(default_factory=list)
    ipv6_addresses: List[Dict[str, Any]] = field(default_factory=list)
    ipv4_prefixes: List[Dict[str, Any]] = field(default_factory=list)
    ipv6_prefixes: List[Dict[str, Any]] = field(default_factory=list)
    group_set: List[Dict[str, Any]] = field(default_factory=list)
    tag_set: List[Dict[str, Any]] = field(default_factory=list)
    attachment: Dict[str, Any] = field(default_factory=dict)
    attachment_id: str = ""
    associate_public_ip_address: Optional[bool] = None
    source_dest_check: Optional[bool] = True
    requester_managed: Optional[bool] = False
    requester_id: str = ""
    owner_id: str = ""
    interface_type: str = ""
    availability_zone: str = ""
    availability_zone_id: str = ""
    connection_tracking_configuration: Dict[str, Any] = field(default_factory=dict)
    deny_all_igw_traffic: Optional[bool] = None
    ipv6_native: Optional[bool] = None
    ipv6_address: str = ""
    public_dns_name: str = ""
    public_ip_dns_name_options: Dict[str, Any] = field(default_factory=dict)
    outpost_arn: str = ""
    operator: Dict[str, Any] = field(default_factory=dict)
    association: Dict[str, Any] = field(default_factory=dict)
    associated_subnet_set: List[Dict[str, Any]] = field(default_factory=list)
    permissions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "GroupId": self.group_id,
            "GroupName": self.group_name,
            "networkInterfaceId": self.network_interface_id,
            "subnetId": self.subnet_id,
            "vpcId": self.vpc_id,
            "description": self.description,
            "status": self.status,
            "macAddress": self.mac_address,
            "privateDnsName": self.private_dns_name,
            "privateIpAddress": self.private_ip_address,
            "privateIpAddresses": self.private_ip_addresses,
            "ipv6Addresses": self.ipv6_addresses,
            "ipv4Prefixes": self.ipv4_prefixes,
            "ipv6Prefixes": self.ipv6_prefixes,
            "groupSet": self.group_set,
            "tagSet": self.tag_set,
            "attachment": self.attachment,
            "attachmentId": self.attachment_id,
            "associatePublicIpAddress": self.associate_public_ip_address,
            "sourceDestCheck": self.source_dest_check,
            "requesterManaged": self.requester_managed,
            "requesterId": self.requester_id,
            "ownerId": self.owner_id,
            "interfaceType": self.interface_type,
            "availabilityZone": self.availability_zone,
            "availabilityZoneId": self.availability_zone_id,
            "connectionTrackingConfiguration": self.connection_tracking_configuration,
            "denyAllIgwTraffic": self.deny_all_igw_traffic,
            "ipv6Native": self.ipv6_native,
            "ipv6Address": self.ipv6_address,
            "publicDnsName": self.public_dns_name,
            "publicIpDnsNameOptions": self.public_ip_dns_name_options,
            "outpostArn": self.outpost_arn,
            "operator": self.operator,
            "association": self.association,
            "associatedSubnetSet": self.associated_subnet_set,
            "permissions": self.permissions,
        }

class ElasticNetworkInterface_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.elastic_network_interfaces  # alias to shared store

    # Cross-resource parent registration (do this in Create/Delete methods):
    #   Create: self.state.subnets.get(params['subnet_id']).network_interface_ids.append(new_id)
    #   Delete: self.state.subnets.get(resource.subnet_id).network_interface_ids.remove(resource_id)
    #   Create: self.state.vpcs.get(params['vpc_id']).vpc_network_interface_ids.append(new_id)
    #   Delete: self.state.vpcs.get(resource.vpc_id).vpc_network_interface_ids.remove(resource_id)


    def AssignIpv6Addresses(self, params: Dict[str, Any]):
        """Assigns the specified IPv6 addresses to the specified network interface. You can
            specify specific IPv6 addresses, or you can specify the number of IPv6 addresses to be
            automatically assigned from the subnet's IPv6 CIDR block range. You can assign as many
            IPv6 addr"""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        ipv6_addresses_param = params.get("Ipv6Addresses.N", []) or []
        ipv6_count = int(params.get("Ipv6AddressCount") or 0)
        assigned_addresses: List[Dict[str, Any]] = []

        existing_addresses = [entry.get("ipv6Address") for entry in network_interface.ipv6_addresses]
        for address in ipv6_addresses_param:
            if address and address not in existing_addresses:
                assigned_entry = {
                    "ipv6Address": address,
                    "isPrimaryIpv6": False,
                    "publicIpv6DnsName": "",
                }
                network_interface.ipv6_addresses.append(assigned_entry)
                assigned_addresses.append(assigned_entry)
                existing_addresses.append(address)

        if ipv6_count:
            for index in range(ipv6_count):
                candidate = f"2001:db8::{len(existing_addresses) + 1}"
                while candidate in existing_addresses:
                    candidate = f"2001:db8::{len(existing_addresses) + 1}"
                assigned_entry = {
                    "ipv6Address": candidate,
                    "isPrimaryIpv6": False,
                    "publicIpv6DnsName": "",
                }
                network_interface.ipv6_addresses.append(assigned_entry)
                assigned_addresses.append(assigned_entry)
                existing_addresses.append(candidate)

        ipv6_prefixes_param = params.get("Ipv6Prefix.N", []) or []
        ipv6_prefix_count = int(params.get("Ipv6PrefixCount") or 0)
        assigned_prefixes: List[Dict[str, Any]] = []
        existing_prefixes = [entry.get("ipv6Prefix") for entry in network_interface.ipv6_prefixes]
        for prefix in ipv6_prefixes_param:
            if prefix and prefix not in existing_prefixes:
                entry = {"ipv6Prefix": prefix}
                network_interface.ipv6_prefixes.append(entry)
                assigned_prefixes.append(entry)
                existing_prefixes.append(prefix)

        if ipv6_prefix_count:
            for index in range(ipv6_prefix_count):
                candidate = f"2001:db8:1::{len(existing_prefixes) + 1}/64"
                while candidate in existing_prefixes:
                    candidate = f"2001:db8:1::{len(existing_prefixes) + 1}/64"
                entry = {"ipv6Prefix": candidate}
                network_interface.ipv6_prefixes.append(entry)
                assigned_prefixes.append(entry)
                existing_prefixes.append(candidate)

        if network_interface.ipv6_addresses and not network_interface.ipv6_address:
            network_interface.ipv6_address = network_interface.ipv6_addresses[0].get("ipv6Address", "")

        return {
            'assignedIpv6Addresses': [entry.get("ipv6Address") for entry in assigned_addresses],
            'assignedIpv6PrefixSet': assigned_prefixes,
            'networkInterfaceId': network_interface.network_interface_id,
            }

    def AssignPrivateIpAddresses(self, params: Dict[str, Any]):
        """Assigns the specified secondary private IP addresses to the specified network
            interface. You can specify specific secondary IP addresses, or you can specify the number of
            secondary IP addresses to be automatically assigned from the subnet's CIDR block range.
            The n"""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        requested_ips = params.get("PrivateIpAddress.N", []) or []
        secondary_count = int(params.get("SecondaryPrivateIpAddressCount") or 0)
        assigned_private_ips: List[Dict[str, Any]] = []

        existing_ips = [entry.get("privateIpAddress") for entry in network_interface.private_ip_addresses]
        for ip_address in requested_ips:
            if ip_address and ip_address not in existing_ips:
                entry = {
                    "association": {},
                    "primary": False,
                    "privateDnsName": "",
                    "privateIpAddress": ip_address,
                }
                network_interface.private_ip_addresses.append(entry)
                assigned_private_ips.append({"privateIpAddress": ip_address})
                existing_ips.append(ip_address)

        next_index = 2
        while len(assigned_private_ips) < secondary_count:
            candidate = f"10.0.0.{next_index}"
            if candidate not in existing_ips:
                entry = {
                    "association": {},
                    "primary": False,
                    "privateDnsName": "",
                    "privateIpAddress": candidate,
                }
                network_interface.private_ip_addresses.append(entry)
                assigned_private_ips.append({"privateIpAddress": candidate})
                existing_ips.append(candidate)
            next_index += 1

        ipv4_prefixes_param = params.get("Ipv4Prefix.N", []) or []
        ipv4_prefix_count = int(params.get("Ipv4PrefixCount") or 0)
        assigned_prefixes: List[Dict[str, Any]] = []
        existing_prefixes = [entry.get("ipv4Prefix") for entry in network_interface.ipv4_prefixes]
        for prefix in ipv4_prefixes_param:
            if prefix and prefix not in existing_prefixes:
                entry = {"ipv4Prefix": prefix}
                network_interface.ipv4_prefixes.append(entry)
                assigned_prefixes.append(entry)
                existing_prefixes.append(prefix)

        if ipv4_prefix_count:
            for index in range(ipv4_prefix_count):
                candidate = f"10.0.0.{len(existing_prefixes) + 1}.0/28"
                while candidate in existing_prefixes:
                    candidate = f"10.0.0.{len(existing_prefixes) + 1}.0/28"
                entry = {"ipv4Prefix": candidate}
                network_interface.ipv4_prefixes.append(entry)
                assigned_prefixes.append(entry)
                existing_prefixes.append(candidate)

        return {
            'assignedIpv4PrefixSet': assigned_prefixes,
            'assignedPrivateIpAddressesSet': assigned_private_ips,
            'networkInterfaceId': network_interface.network_interface_id,
            }

    def AttachNetworkInterface(self, params: Dict[str, Any]):
        """Attaches a network interface to an instance."""

        if params.get("DeviceIndex") is None:
            return create_error_response("MissingParameter", "Missing required parameter: DeviceIndex")

        instance_id = params.get("InstanceId")
        if not instance_id:
            return create_error_response("MissingParameter", "Missing required parameter: InstanceId")

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        instance = self.state.instances.get(instance_id)
        if not instance:
            return create_error_response("InvalidInstanceID.NotFound", f"The ID '{instance_id}' does not exist")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        attachment_id = self._generate_id("eni-attach")
        attach_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        attachment = {
            "attachmentId": attachment_id,
            "attachTime": attach_time,
            "deleteOnTermination": False,
            "deviceIndex": params.get("DeviceIndex"),
            "enaQueueCount": params.get("EnaQueueCount") or 0,
            "enaSrdSpecification": params.get("EnaSrdSpecification") if isinstance(params.get("EnaSrdSpecification"), dict) else {
                "enaSrdEnabled": False,
                "enaSrdUdpSpecification": {
                    "enaSrdUdpEnabled": False,
                },
            },
            "instanceId": instance_id,
            "instanceOwnerId": "",
            "networkCardIndex": params.get("NetworkCardIndex") or 0,
            "status": "attached",
        }

        network_interface.attachment = attachment
        network_interface.attachment_id = attachment_id
        network_interface.status = "in-use"

        if hasattr(instance, "network_interface_set"):
            instance.network_interface_set.append({
                "attachment": {
                    "attachmentId": attachment_id,
                    "deviceIndex": params.get("DeviceIndex"),
                    "status": "attached",
                },
                "networkInterfaceId": network_interface_id,
                "privateIpAddress": network_interface.private_ip_address,
                "subnetId": network_interface.subnet_id,
                "vpcId": network_interface.vpc_id,
            })
        if hasattr(instance, "network_interface_ids"):
            instance.network_interface_ids.append(network_interface_id)

        return {
            'attachmentId': attachment_id,
            'networkCardIndex': attachment.get("networkCardIndex"),
            }

    def CreateNetworkInterface(self, params: Dict[str, Any]):
        """Creates a network interface in the specified subnet. The number of IP addresses you can assign to a network interface varies by instance
            type. For more information about network interfaces, seeElastic network interfacesin theAmazon EC2 User Guide."""

        subnet_id = params.get("SubnetId")
        if not subnet_id:
            return create_error_response("MissingParameter", "Missing required parameter: SubnetId")

        subnet = self.state.subnets.get(subnet_id)
        if not subnet:
            return create_error_response("InvalidSubnetID.NotFound", f"Subnet '{subnet_id}' does not exist.")

        group_ids = params.get("SecurityGroupId.N", []) or []
        group_set: List[Dict[str, Any]] = []
        for group_id in group_ids:
            sg = self.state.security_groups.get(group_id)
            if not sg:
                return create_error_response("InvalidGroup.NotFound", f"The ID '{group_id}' does not exist")
            group_set.append({
                "groupId": group_id,
                "groupName": getattr(sg, "group_name", ""),
            })

        tag_set: List[Dict[str, Any]] = []
        for spec in params.get("TagSpecification.N", []) or []:
            if not isinstance(spec, dict):
                continue
            resource_type = spec.get("ResourceType")
            if resource_type and resource_type != "network-interface":
                continue
            for tag in spec.get("Tag") or spec.get("Tags") or []:
                if tag:
                    tag_set.append(tag)

        private_ip_addresses_param = params.get("PrivateIpAddresses.N", []) or []
        primary_ip = params.get("PrivateIpAddress") or (private_ip_addresses_param[0] if private_ip_addresses_param else None)
        if not primary_ip:
            primary_ip = "10.0.0.1"
        private_ip_addresses: List[Dict[str, Any]] = [
            {
                "association": {},
                "primary": True,
                "privateDnsName": "",
                "privateIpAddress": primary_ip,
            }
        ]
        for ip_address in private_ip_addresses_param:
            if ip_address and ip_address != primary_ip:
                private_ip_addresses.append({
                    "association": {},
                    "primary": False,
                    "privateDnsName": "",
                    "privateIpAddress": ip_address,
                })

        secondary_count = int(params.get("SecondaryPrivateIpAddressCount") or 0)
        next_index = 2
        while len(private_ip_addresses) - 1 < secondary_count:
            candidate = f"10.0.0.{next_index}"
            if candidate != primary_ip and all(entry["privateIpAddress"] != candidate for entry in private_ip_addresses):
                private_ip_addresses.append({
                    "association": {},
                    "primary": False,
                    "privateDnsName": "",
                    "privateIpAddress": candidate,
                })
            next_index += 1

        ipv4_prefixes = [{"ipv4Prefix": prefix} for prefix in (params.get("Ipv4Prefix.N", []) or [])]
        ipv6_prefixes = [{"ipv6Prefix": prefix} for prefix in (params.get("Ipv6Prefix.N", []) or [])]

        ipv6_addresses_param = params.get("Ipv6Addresses.N", []) or []
        ipv6_count = int(params.get("Ipv6AddressCount") or 0)
        ipv6_addresses: List[Dict[str, Any]] = []
        for addr in ipv6_addresses_param:
            if addr:
                ipv6_addresses.append({
                    "ipv6Address": addr,
                    "isPrimaryIpv6": False,
                    "publicIpv6DnsName": "",
                })
        if not ipv6_addresses and ipv6_count:
            for index in range(ipv6_count):
                ipv6_addresses.append({
                    "ipv6Address": f"2001:db8::{index + 1}",
                    "isPrimaryIpv6": False,
                    "publicIpv6DnsName": "",
                })

        enable_primary_ipv6 = str2bool(params.get("EnablePrimaryIpv6"))
        if ipv6_addresses:
            ipv6_addresses[0]["isPrimaryIpv6"] = enable_primary_ipv6

        ipv6_address = ipv6_addresses[0]["ipv6Address"] if ipv6_addresses else ""

        mac_seed = uuid.uuid4().hex[:12]
        mac_address = "02:" + ":".join(mac_seed[i:i + 2] for i in range(0, 12, 2))

        private_dns_name = ""
        if primary_ip:
            private_dns_name = f"ip-{primary_ip.replace('.', '-')}.ec2.internal"

        eni_id = self._generate_id("eni")
        vpc_id = getattr(subnet, "vpc_id", "")
        availability_zone = getattr(subnet, "availability_zone", "")
        availability_zone_id = getattr(subnet, "availability_zone_id", "")

        connection_tracking_spec = params.get("ConnectionTrackingSpecification")
        connection_tracking_configuration = connection_tracking_spec if isinstance(connection_tracking_spec, dict) else {}
        connection_tracking_configuration = {
            "tcpEstablishedTimeout": connection_tracking_configuration.get("tcpEstablishedTimeout")
            or connection_tracking_configuration.get("TcpEstablishedTimeout")
            or 0,
            "udpStreamTimeout": connection_tracking_configuration.get("udpStreamTimeout")
            or connection_tracking_configuration.get("UdpStreamTimeout")
            or 0,
            "udpTimeout": connection_tracking_configuration.get("udpTimeout")
            or connection_tracking_configuration.get("UdpTimeout")
            or 0,
        }

        operator = params.get("Operator") if isinstance(params.get("Operator"), dict) else {}

        resource = ElasticNetworkInterface(
            network_interface_id=eni_id,
            subnet_id=subnet_id,
            vpc_id=vpc_id,
            description=params.get("Description") or "",
            status="available",
            mac_address=mac_address,
            private_dns_name=private_dns_name,
            private_ip_address=primary_ip,
            private_ip_addresses=private_ip_addresses,
            ipv6_addresses=ipv6_addresses,
            ipv4_prefixes=ipv4_prefixes,
            ipv6_prefixes=ipv6_prefixes,
            group_set=group_set,
            tag_set=tag_set,
            attachment={
                "attachmentId": "",
                "attachTime": "",
                "deleteOnTermination": False,
                "deviceIndex": 0,
                "enaQueueCount": 0,
                "enaSrdSpecification": {
                    "enaSrdEnabled": False,
                    "enaSrdUdpSpecification": {
                        "enaSrdUdpEnabled": False,
                    },
                },
                "instanceId": "",
                "instanceOwnerId": "",
                "networkCardIndex": 0,
                "status": "detached",
            },
            attachment_id="",
            associate_public_ip_address=None,
            source_dest_check=True,
            requester_managed=False,
            requester_id="",
            owner_id="",
            interface_type=params.get("InterfaceType") or "",
            availability_zone=availability_zone,
            availability_zone_id=availability_zone_id,
            connection_tracking_configuration=connection_tracking_configuration,
            deny_all_igw_traffic=False,
            ipv6_native=enable_primary_ipv6,
            ipv6_address=ipv6_address,
            public_dns_name="",
            public_ip_dns_name_options={
                "dnsHostnameType": "",
                "publicDualStackDnsName": "",
                "publicIpv4DnsName": "",
                "publicIpv6DnsName": "",
            },
            outpost_arn="",
            operator=operator,
            association={
                "allocationId": "",
                "associationId": "",
                "carrierIp": "",
                "customerOwnedIp": "",
                "ipOwnerId": "",
                "publicDnsName": "",
                "publicIp": "",
            },
            associated_subnet_set=[],
        )
        self.resources[eni_id] = resource

        if hasattr(subnet, "network_interface_ids"):
            subnet.network_interface_ids.append(eni_id)

        if vpc_id:
            vpc = self.state.vpcs.get(vpc_id)
            if vpc and hasattr(vpc, "vpc_network_interface_ids"):
                vpc.vpc_network_interface_ids.append(eni_id)

        return {
            'clientToken': params.get("ClientToken") or "",
            'networkInterface': {
                'associatedSubnetSet': resource.associated_subnet_set,
                'association': resource.association,
                'attachment': resource.attachment,
                'availabilityZone': resource.availability_zone,
                'availabilityZoneId': resource.availability_zone_id,
                'connectionTrackingConfiguration': resource.connection_tracking_configuration,
                'denyAllIgwTraffic': resource.deny_all_igw_traffic,
                'description': resource.description,
                'groupSet': resource.group_set,
                'interfaceType': resource.interface_type,
                'ipv4PrefixSet': resource.ipv4_prefixes,
                'ipv6Address': resource.ipv6_address,
                'ipv6AddressesSet': resource.ipv6_addresses,
                'ipv6Native': resource.ipv6_native,
                'ipv6PrefixSet': resource.ipv6_prefixes,
                'macAddress': resource.mac_address,
                'networkInterfaceId': resource.network_interface_id,
                'operator': {
                    'managed': resource.operator.get("managed", "") if isinstance(resource.operator, dict) else "",
                    'principal': resource.operator.get("principal", "") if isinstance(resource.operator, dict) else "",
                },
                'outpostArn': resource.outpost_arn,
                'ownerId': resource.owner_id,
                'privateDnsName': resource.private_dns_name,
                'privateIpAddress': resource.private_ip_address,
                'privateIpAddressesSet': resource.private_ip_addresses,
                'publicDnsName': resource.public_dns_name,
                'publicIpDnsNameOptions': resource.public_ip_dns_name_options,
                'requesterId': resource.requester_id,
                'requesterManaged': resource.requester_managed,
                'sourceDestCheck': resource.source_dest_check,
                'status': resource.status,
                'subnetId': resource.subnet_id,
                'tagSet': resource.tag_set,
                'vpcId': resource.vpc_id,
                },
            }

    def CreateNetworkInterfacePermission(self, params: Dict[str, Any]):
        """Grants an AWS-authorized account permission to attach the specified
            network interface to an instance in their account. You can grant permission to a single AWS account only, and only one
            account at a time."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        permission = params.get("Permission")
        if not permission:
            return create_error_response("MissingParameter", "Missing required parameter: Permission")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response("InvalidNetworkInterfaceID.NotFound", f"The ID '{network_interface_id}' does not exist")

        permission_id = self._generate_id("eni-perm")
        interface_permission = {
            "awsAccountId": params.get("AwsAccountId") or "",
            "awsService": params.get("AwsService") or "",
            "networkInterfaceId": network_interface_id,
            "networkInterfacePermissionId": permission_id,
            "permission": permission,
            "permissionState": {
                "state": "granted",
                "statusMessage": "",
            },
        }
        network_interface.permissions.append(interface_permission)

        return {
            'interfacePermission': interface_permission,
            }

    def DeleteNetworkInterface(self, params: Dict[str, Any]):
        """Deletes the specified network interface. You must detach the network interface before
            you can delete it."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        attachment = network_interface.attachment if isinstance(network_interface.attachment, dict) else {}
        if network_interface.attachment_id or attachment.get("status") == "attached" or attachment.get("instanceId"):
            return create_error_response("DependencyViolation", "Network interface is currently attached")

        subnet = self.state.subnets.get(network_interface.subnet_id)
        if subnet and hasattr(subnet, "network_interface_ids"):
            if network_interface_id in subnet.network_interface_ids:
                subnet.network_interface_ids.remove(network_interface_id)

        vpc = self.state.vpcs.get(network_interface.vpc_id)
        if vpc and hasattr(vpc, "vpc_network_interface_ids"):
            if network_interface_id in vpc.vpc_network_interface_ids:
                vpc.vpc_network_interface_ids.remove(network_interface_id)

        del self.resources[network_interface_id]

        return {
            'return': True,
            }

    def DeleteNetworkInterfacePermission(self, params: Dict[str, Any]):
        """Deletes a permission for a network interface. By default, you cannot delete the
            permission if the account for which you're removing the permission has attached the
            network interface to an instance. However, you can force delete the permission,
            regardless of any at"""

        permission_id = params.get("NetworkInterfacePermissionId")
        if not permission_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfacePermissionId")

        for network_interface in self.resources.values():
            permissions = getattr(network_interface, "permissions", []) or []
            for index, permission in enumerate(list(permissions)):
                if permission.get("networkInterfacePermissionId") == permission_id:
                    permissions.pop(index)
                    network_interface.permissions = permissions
                    return {
                        'return': True,
                        }

        return create_error_response(
            "InvalidNetworkInterfacePermissionId.NotFound",
            f"The ID '{permission_id}' does not exist",
        )

    def DescribeNetworkInterfaceAttribute(self, params: Dict[str, Any]):
        """Describes a network interface attribute. You can specify only one attribute at a
            time."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        attachment = network_interface.attachment if isinstance(network_interface.attachment, dict) else {}
        ena_spec = attachment.get("enaSrdSpecification") if isinstance(attachment.get("enaSrdSpecification"), dict) else {}
        ena_udp_spec = ena_spec.get("enaSrdUdpSpecification") if isinstance(ena_spec.get("enaSrdUdpSpecification"), dict) else {}

        return {
            'associatePublicIpAddress': network_interface.associate_public_ip_address,
            'attachment': {
                'attachmentId': attachment.get("attachmentId"),
                'attachTime': attachment.get("attachTime"),
                'deleteOnTermination': attachment.get("deleteOnTermination"),
                'deviceIndex': attachment.get("deviceIndex"),
                'enaQueueCount': attachment.get("enaQueueCount"),
                'enaSrdSpecification': {
                    'enaSrdEnabled': ena_spec.get("enaSrdEnabled"),
                    'enaSrdUdpSpecification': {
                        'enaSrdUdpEnabled': ena_udp_spec.get("enaSrdUdpEnabled"),
                        },
                    },
                'instanceId': attachment.get("instanceId"),
                'instanceOwnerId': attachment.get("instanceOwnerId"),
                'networkCardIndex': attachment.get("networkCardIndex"),
                'status': attachment.get("status"),
                },
            'description': {
                'Value': network_interface.description,
                },
            'groupSet': network_interface.group_set,
            'networkInterfaceId': network_interface.network_interface_id,
            'sourceDestCheck': {
                'Value': network_interface.source_dest_check,
                },
            }

    def DescribeNetworkInterfacePermissions(self, params: Dict[str, Any]):
        """Describes the permissions for your network interfaces."""

        permission_ids = params.get("NetworkInterfacePermissionId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        permissions: List[Dict[str, Any]] = []
        if permission_ids:
            permission_map: Dict[str, Dict[str, Any]] = {}
            for network_interface in self.resources.values():
                for permission in getattr(network_interface, "permissions", []) or []:
                    permission_id = permission.get("networkInterfacePermissionId")
                    if permission_id:
                        permission_map[permission_id] = permission
            for permission_id in permission_ids:
                permission = permission_map.get(permission_id)
                if not permission:
                    return create_error_response(
                        "InvalidNetworkInterfacePermissionId.NotFound",
                        f"The ID '{permission_id}' does not exist",
                    )
                permissions.append(permission)
        else:
            for network_interface in self.resources.values():
                permissions.extend(getattr(network_interface, "permissions", []) or [])

        filters = params.get("Filter.N", []) or []
        for filter_item in filters:
            if not isinstance(filter_item, dict):
                continue
            name = (filter_item.get("Name") or "").lower()
            values = filter_item.get("Values") or []
            if not values:
                continue
            if name == "network-interface-id":
                permissions = [perm for perm in permissions if perm.get("networkInterfaceId") in values]
            elif name == "aws-account-id":
                permissions = [perm for perm in permissions if perm.get("awsAccountId") in values]
            elif name == "aws-service":
                permissions = [perm for perm in permissions if perm.get("awsService") in values]
            elif name == "permission":
                permissions = [perm for perm in permissions if perm.get("permission") in values]
            elif name == "network-interface-permission-id":
                permissions = [perm for perm in permissions if perm.get("networkInterfacePermissionId") in values]

        return {
            'networkInterfacePermissions': permissions[:max_results],
            'nextToken': None,
            }

    def DescribeNetworkInterfaces(self, params: Dict[str, Any]):
        """Describes the specified network interfaces or all your network interfaces. If you have a large number of network interfaces, the operation fails unless you use
            pagination or one of the following filters:group-id,mac-address,private-dns-name,private-ip-address,subnet-id, orvpc-id. We stro"""

        network_interface_ids = params.get("NetworkInterfaceId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        if network_interface_ids:
            resources: List[ElasticNetworkInterface] = []
            for network_interface_id in network_interface_ids:
                network_interface = self.resources.get(network_interface_id)
                if not network_interface:
                    return create_error_response(
                        "InvalidNetworkInterfaceID.NotFound",
                        f"The ID '{network_interface_id}' does not exist",
                    )
                resources.append(network_interface)
        else:
            resources = list(self.resources.values())

        resources = apply_filters(resources, params.get("Filter.N", []))

        network_interfaces: List[Dict[str, Any]] = []
        for network_interface in resources[:max_results]:
            operator = network_interface.operator if isinstance(network_interface.operator, dict) else {}
            network_interfaces.append({
                'associatedSubnetSet': network_interface.associated_subnet_set,
                'association': network_interface.association,
                'attachment': network_interface.attachment,
                'availabilityZone': network_interface.availability_zone,
                'availabilityZoneId': network_interface.availability_zone_id,
                'connectionTrackingConfiguration': network_interface.connection_tracking_configuration,
                'denyAllIgwTraffic': network_interface.deny_all_igw_traffic,
                'description': network_interface.description,
                'groupSet': network_interface.group_set,
                'interfaceType': network_interface.interface_type,
                'ipv4PrefixSet': network_interface.ipv4_prefixes,
                'ipv6Address': network_interface.ipv6_address,
                'ipv6AddressesSet': network_interface.ipv6_addresses,
                'ipv6Native': network_interface.ipv6_native,
                'ipv6PrefixSet': network_interface.ipv6_prefixes,
                'macAddress': network_interface.mac_address,
                'networkInterfaceId': network_interface.network_interface_id,
                'operator': {
                    'managed': operator.get("managed", ""),
                    'principal': operator.get("principal", ""),
                },
                'outpostArn': network_interface.outpost_arn,
                'ownerId': network_interface.owner_id,
                'privateDnsName': network_interface.private_dns_name,
                'privateIpAddress': network_interface.private_ip_address,
                'privateIpAddressesSet': network_interface.private_ip_addresses,
                'publicDnsName': network_interface.public_dns_name,
                'publicIpDnsNameOptions': network_interface.public_ip_dns_name_options,
                'requesterId': network_interface.requester_id,
                'requesterManaged': network_interface.requester_managed,
                'sourceDestCheck': network_interface.source_dest_check,
                'status': network_interface.status,
                'subnetId': network_interface.subnet_id,
                'tagSet': network_interface.tag_set,
                'vpcId': network_interface.vpc_id,
                })

        return {
            'networkInterfaceSet': network_interfaces,
            'nextToken': None,
            }

    def DetachNetworkInterface(self, params: Dict[str, Any]):
        """Detaches a network interface from an instance."""

        attachment_id = params.get("AttachmentId")
        if not attachment_id:
            return create_error_response("MissingParameter", "Missing required parameter: AttachmentId")

        target_interface: Optional[ElasticNetworkInterface] = None
        for network_interface in self.resources.values():
            if network_interface.attachment_id == attachment_id:
                target_interface = network_interface
                break
            attachment = network_interface.attachment if isinstance(network_interface.attachment, dict) else {}
            if attachment.get("attachmentId") == attachment_id:
                target_interface = network_interface
                break

        if not target_interface:
            return create_error_response(
                "InvalidAttachmentID.NotFound",
                f"The ID '{attachment_id}' does not exist",
            )

        attachment = target_interface.attachment if isinstance(target_interface.attachment, dict) else {}
        instance_id = attachment.get("instanceId")
        if instance_id:
            instance = self.state.instances.get(instance_id)
            if instance and hasattr(instance, "network_interface_set"):
                instance.network_interface_set = [
                    item for item in instance.network_interface_set
                    if item.get("attachment", {}).get("attachmentId") != attachment_id
                ]
            if instance and hasattr(instance, "network_interface_ids"):
                if target_interface.network_interface_id in instance.network_interface_ids:
                    instance.network_interface_ids.remove(target_interface.network_interface_id)

        target_interface.attachment = {
            "attachmentId": "",
            "attachTime": "",
            "deleteOnTermination": False,
            "deviceIndex": 0,
            "enaQueueCount": 0,
            "enaSrdSpecification": {
                "enaSrdEnabled": False,
                "enaSrdUdpSpecification": {
                    "enaSrdUdpEnabled": False,
                },
            },
            "instanceId": "",
            "instanceOwnerId": "",
            "networkCardIndex": 0,
            "status": "detached",
        }
        target_interface.attachment_id = ""
        target_interface.status = "available"

        return {
            'return': True,
            }

    def ModifyNetworkInterfaceAttribute(self, params: Dict[str, Any]):
        """Modifies the specified network interface attribute. You can specify only one attribute
            at a time. You can use this action to attach and detach security groups from an existing
            EC2 instance."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        associated_subnets = params.get("AssociatedSubnetId.N", []) or []
        if associated_subnets:
            for subnet_id in associated_subnets:
                if subnet_id and subnet_id not in self.state.subnets:
                    return create_error_response(
                        "InvalidSubnetID.NotFound",
                        f"Subnet '{subnet_id}' does not exist.",
                    )
            network_interface.associated_subnet_set = [
                {"subnetId": subnet_id} for subnet_id in associated_subnets if subnet_id
            ]

        associate_public_ip = params.get("AssociatePublicIpAddress")
        if associate_public_ip is not None:
            network_interface.associate_public_ip_address = str2bool(associate_public_ip)

        attachment_changes = params.get("Attachment")
        if isinstance(attachment_changes, dict):
            instance_id = attachment_changes.get("InstanceId") or attachment_changes.get("instanceId")
            if instance_id and instance_id not in self.state.instances:
                return create_error_response(
                    "InvalidInstanceID.NotFound",
                    f"The ID '{instance_id}' does not exist",
                )
            network_interface.attachment = {
                **(network_interface.attachment or {}),
                **attachment_changes,
            }

        connection_tracking_spec = params.get("ConnectionTrackingSpecification")
        if isinstance(connection_tracking_spec, dict):
            network_interface.connection_tracking_configuration = {
                "tcpEstablishedTimeout": connection_tracking_spec.get("tcpEstablishedTimeout")
                or connection_tracking_spec.get("TcpEstablishedTimeout")
                or 0,
                "udpStreamTimeout": connection_tracking_spec.get("udpStreamTimeout")
                or connection_tracking_spec.get("UdpStreamTimeout")
                or 0,
                "udpTimeout": connection_tracking_spec.get("udpTimeout")
                or connection_tracking_spec.get("UdpTimeout")
                or 0,
            }

        description = params.get("Description")
        if isinstance(description, dict):
            description_value = description.get("Value")
            if description_value is not None:
                network_interface.description = description_value
        elif description is not None:
            network_interface.description = description

        enable_primary_ipv6 = params.get("EnablePrimaryIpv6")
        if enable_primary_ipv6 is not None:
            network_interface.ipv6_native = str2bool(enable_primary_ipv6)
            if network_interface.ipv6_addresses:
                network_interface.ipv6_addresses[0]["isPrimaryIpv6"] = network_interface.ipv6_native

        ena_srd_spec = params.get("EnaSrdSpecification")
        if isinstance(ena_srd_spec, dict):
            attachment = network_interface.attachment or {}
            attachment["enaSrdSpecification"] = ena_srd_spec
            network_interface.attachment = attachment

        group_ids = params.get("SecurityGroupId.N", []) or []
        if group_ids:
            group_set: List[Dict[str, Any]] = []
            for group_id in group_ids:
                sg = self.state.security_groups.get(group_id)
                if not sg:
                    return create_error_response("InvalidGroup.NotFound", f"The ID '{group_id}' does not exist")
                group_set.append({
                    "groupId": group_id,
                    "groupName": getattr(sg, "group_name", ""),
                })
            network_interface.group_set = group_set

        source_dest_check = params.get("SourceDestCheck")
        if isinstance(source_dest_check, dict):
            source_dest_value = source_dest_check.get("Value")
            if source_dest_value is not None:
                network_interface.source_dest_check = str2bool(source_dest_value)
        elif source_dest_check is not None:
            network_interface.source_dest_check = str2bool(source_dest_check)

        return {
            'return': True,
            }

    def ResetNetworkInterfaceAttribute(self, params: Dict[str, Any]):
        """Resets a network interface attribute. You can specify only one attribute at a
            time."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        source_dest_check = params.get("SourceDestCheck")
        if source_dest_check is not None:
            network_interface.source_dest_check = True

        return {
            'return': True,
            }

    def UnassignIpv6Addresses(self, params: Dict[str, Any]):
        """Unassigns the specified IPv6 addresses or Prefix Delegation prefixes from a network
            interface."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        unassigned_addresses: List[str] = []
        ipv6_addresses = params.get("Ipv6Addresses.N", []) or []
        if ipv6_addresses:
            remaining_addresses = []
            for entry in network_interface.ipv6_addresses:
                address = entry.get("ipv6Address")
                if address in ipv6_addresses:
                    unassigned_addresses.append(address)
                else:
                    remaining_addresses.append(entry)
            network_interface.ipv6_addresses = remaining_addresses

        unassigned_prefixes: List[Dict[str, Any]] = []
        ipv6_prefixes = params.get("Ipv6Prefix.N", []) or []
        if ipv6_prefixes:
            remaining_prefixes = []
            for entry in network_interface.ipv6_prefixes:
                prefix = entry.get("ipv6Prefix")
                if prefix in ipv6_prefixes:
                    unassigned_prefixes.append({"ipv6Prefix": prefix})
                else:
                    remaining_prefixes.append(entry)
            network_interface.ipv6_prefixes = remaining_prefixes

        if network_interface.ipv6_address and network_interface.ipv6_address in unassigned_addresses:
            network_interface.ipv6_address = network_interface.ipv6_addresses[0].get("ipv6Address", "") if network_interface.ipv6_addresses else ""

        return {
            'networkInterfaceId': network_interface.network_interface_id,
            'unassignedIpv6Addresses': unassigned_addresses,
            'unassignedIpv6PrefixSet': unassigned_prefixes,
            }

    def UnassignPrivateIpAddresses(self, params: Dict[str, Any]):
        """Unassigns the specified secondary private IP addresses or IPv4 Prefix Delegation
            prefixes from a network interface."""

        network_interface_id = params.get("NetworkInterfaceId")
        if not network_interface_id:
            return create_error_response("MissingParameter", "Missing required parameter: NetworkInterfaceId")

        network_interface = self.resources.get(network_interface_id)
        if not network_interface:
            return create_error_response(
                "InvalidNetworkInterfaceID.NotFound",
                f"The ID '{network_interface_id}' does not exist",
            )

        private_ips = params.get("PrivateIpAddress.N", []) or []
        if private_ips:
            remaining_private_ips = []
            for entry in network_interface.private_ip_addresses:
                ip_address = entry.get("privateIpAddress")
                if ip_address in private_ips and not entry.get("primary"):
                    continue
                remaining_private_ips.append(entry)
            network_interface.private_ip_addresses = remaining_private_ips

        ipv4_prefixes = params.get("Ipv4Prefix.N", []) or []
        if ipv4_prefixes:
            remaining_prefixes = []
            for entry in network_interface.ipv4_prefixes:
                prefix = entry.get("ipv4Prefix")
                if prefix in ipv4_prefixes:
                    continue
                remaining_prefixes.append(entry)
            network_interface.ipv4_prefixes = remaining_prefixes

        return {
            'return': True,
            }

    def _generate_id(self, prefix: str = 'sg') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class elasticnetworkinterface_RequestParser:
    @staticmethod
    def parse_assign_ipv6_addresses_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Ipv6AddressCount": get_int(md, "Ipv6AddressCount"),
            "Ipv6Addresses.N": get_indexed_list(md, "Ipv6Addresses"),
            "Ipv6Prefix.N": get_indexed_list(md, "Ipv6Prefix"),
            "Ipv6PrefixCount": get_int(md, "Ipv6PrefixCount"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
        }

    @staticmethod
    def parse_assign_private_ip_addresses_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AllowReassignment": get_scalar(md, "AllowReassignment"),
            "Ipv4Prefix.N": get_indexed_list(md, "Ipv4Prefix"),
            "Ipv4PrefixCount": get_int(md, "Ipv4PrefixCount"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
            "PrivateIpAddress.N": get_indexed_list(md, "PrivateIpAddress"),
            "SecondaryPrivateIpAddressCount": get_int(md, "SecondaryPrivateIpAddressCount"),
        }

    @staticmethod
    def parse_attach_network_interface_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DeviceIndex": get_int(md, "DeviceIndex"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EnaQueueCount": get_int(md, "EnaQueueCount"),
            "EnaSrdSpecification": get_scalar(md, "EnaSrdSpecification"),
            "InstanceId": get_scalar(md, "InstanceId"),
            "NetworkCardIndex": get_int(md, "NetworkCardIndex"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
        }

    @staticmethod
    def parse_create_network_interface_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "ConnectionTrackingSpecification": get_scalar(md, "ConnectionTrackingSpecification"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EnablePrimaryIpv6": get_scalar(md, "EnablePrimaryIpv6"),
            "InterfaceType": get_scalar(md, "InterfaceType"),
            "Ipv4Prefix.N": get_indexed_list(md, "Ipv4Prefix"),
            "Ipv4PrefixCount": get_int(md, "Ipv4PrefixCount"),
            "Ipv6AddressCount": get_int(md, "Ipv6AddressCount"),
            "Ipv6Addresses.N": get_indexed_list(md, "Ipv6Addresses"),
            "Ipv6Prefix.N": get_indexed_list(md, "Ipv6Prefix"),
            "Ipv6PrefixCount": get_int(md, "Ipv6PrefixCount"),
            "Operator": get_scalar(md, "Operator"),
            "PrivateIpAddress": get_scalar(md, "PrivateIpAddress"),
            "PrivateIpAddresses.N": get_indexed_list(md, "PrivateIpAddresses"),
            "SecondaryPrivateIpAddressCount": get_int(md, "SecondaryPrivateIpAddressCount"),
            "SecurityGroupId.N": get_indexed_list(md, "SecurityGroupId"),
            "SubnetId": get_scalar(md, "SubnetId"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_network_interface_permission_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AwsAccountId": get_scalar(md, "AwsAccountId"),
            "AwsService": get_scalar(md, "AwsService"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
            "Permission": get_scalar(md, "Permission"),
        }

    @staticmethod
    def parse_delete_network_interface_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
        }

    @staticmethod
    def parse_delete_network_interface_permission_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Force": get_scalar(md, "Force"),
            "NetworkInterfacePermissionId": get_scalar(md, "NetworkInterfacePermissionId"),
        }

    @staticmethod
    def parse_describe_network_interface_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
        }

    @staticmethod
    def parse_describe_network_interface_permissions_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NetworkInterfacePermissionId.N": get_indexed_list(md, "NetworkInterfacePermissionId"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_network_interfaces_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NetworkInterfaceId.N": get_indexed_list(md, "NetworkInterfaceId"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_detach_network_interface_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AttachmentId": get_scalar(md, "AttachmentId"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Force": get_scalar(md, "Force"),
        }

    @staticmethod
    def parse_modify_network_interface_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AssociatedSubnetId.N": get_indexed_list(md, "AssociatedSubnetId"),
            "AssociatePublicIpAddress": get_scalar(md, "AssociatePublicIpAddress"),
            "Attachment": get_int(md, "Attachment"),
            "ConnectionTrackingSpecification": get_scalar(md, "ConnectionTrackingSpecification"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EnablePrimaryIpv6": get_scalar(md, "EnablePrimaryIpv6"),
            "EnaSrdSpecification": get_scalar(md, "EnaSrdSpecification"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
            "SecurityGroupId.N": get_indexed_list(md, "SecurityGroupId"),
            "SourceDestCheck": get_scalar(md, "SourceDestCheck"),
        }

    @staticmethod
    def parse_reset_network_interface_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
            "SourceDestCheck": get_scalar(md, "SourceDestCheck"),
        }

    @staticmethod
    def parse_unassign_ipv6_addresses_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Ipv6Addresses.N": get_indexed_list(md, "Ipv6Addresses"),
            "Ipv6Prefix.N": get_indexed_list(md, "Ipv6Prefix"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
        }

    @staticmethod
    def parse_unassign_private_ip_addresses_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Ipv4Prefix.N": get_indexed_list(md, "Ipv4Prefix"),
            "NetworkInterfaceId": get_scalar(md, "NetworkInterfaceId"),
            "PrivateIpAddress.N": get_indexed_list(md, "PrivateIpAddress"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AssignIpv6Addresses": elasticnetworkinterface_RequestParser.parse_assign_ipv6_addresses_request,
            "AssignPrivateIpAddresses": elasticnetworkinterface_RequestParser.parse_assign_private_ip_addresses_request,
            "AttachNetworkInterface": elasticnetworkinterface_RequestParser.parse_attach_network_interface_request,
            "CreateNetworkInterface": elasticnetworkinterface_RequestParser.parse_create_network_interface_request,
            "CreateNetworkInterfacePermission": elasticnetworkinterface_RequestParser.parse_create_network_interface_permission_request,
            "DeleteNetworkInterface": elasticnetworkinterface_RequestParser.parse_delete_network_interface_request,
            "DeleteNetworkInterfacePermission": elasticnetworkinterface_RequestParser.parse_delete_network_interface_permission_request,
            "DescribeNetworkInterfaceAttribute": elasticnetworkinterface_RequestParser.parse_describe_network_interface_attribute_request,
            "DescribeNetworkInterfacePermissions": elasticnetworkinterface_RequestParser.parse_describe_network_interface_permissions_request,
            "DescribeNetworkInterfaces": elasticnetworkinterface_RequestParser.parse_describe_network_interfaces_request,
            "DetachNetworkInterface": elasticnetworkinterface_RequestParser.parse_detach_network_interface_request,
            "ModifyNetworkInterfaceAttribute": elasticnetworkinterface_RequestParser.parse_modify_network_interface_attribute_request,
            "ResetNetworkInterfaceAttribute": elasticnetworkinterface_RequestParser.parse_reset_network_interface_attribute_request,
            "UnassignIpv6Addresses": elasticnetworkinterface_RequestParser.parse_unassign_ipv6_addresses_request,
            "UnassignPrivateIpAddresses": elasticnetworkinterface_RequestParser.parse_unassign_private_ip_addresses_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class elasticnetworkinterface_ResponseSerializer:
    @staticmethod
    def _serialize_dict_to_xml(d: Dict[str, Any], tag_name: str, indent_level: int) -> List[str]:
        """Serialize a dictionary to XML elements."""
        xml_parts = []
        indent = '    ' * indent_level
        for key, value in d.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                xml_parts.append(f'{indent}<{key}>')
                xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
            elif isinstance(value, bool):
                xml_parts.append(f'{indent}<{key}>{str(value).lower()}</{key}>')
            else:
                xml_parts.append(f'{indent}<{key}>{esc(str(value))}</{key}>')
        return xml_parts

    @staticmethod
    def _serialize_list_to_xml(lst: List[Any], tag_name: str, indent_level: int) -> List[str]:
        """Serialize a list to XML elements with <tagName> wrapper and <item> children."""
        xml_parts = []
        indent = '    ' * indent_level
        xml_parts.append(f'{indent}<{tag_name}>')
        for item in lst:
            if isinstance(item, dict):
                xml_parts.append(f'{indent}    <item>')
                xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
            else:
                xml_parts.append(f'{indent}    <item>{esc(str(item))}</item>')
        xml_parts.append(f'{indent}</{tag_name}>')
        return xml_parts

    @staticmethod
    def _serialize_nested_fields(d: Dict[str, Any], indent_level: int) -> List[str]:
        """Serialize nested fields from a dictionary."""
        xml_parts = []
        indent = '    ' * indent_level
        for key, value in d.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                xml_parts.append(f'{indent}<{key}>')
                xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
                        xml_parts.append(f'{indent}    </item>')
                    else:
                        xml_parts.append(f'{indent}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, bool):
                xml_parts.append(f'{indent}<{key}>{str(value).lower()}</{key}>')
            else:
                xml_parts.append(f'{indent}<{key}>{esc(str(value))}</{key}>')
        return xml_parts


    @staticmethod
    def _serialize_group_set(group_set: List[Dict[str, Any]], indent_level: int) -> List[str]:
        xml_parts = []
        indent = '    ' * indent_level
        if group_set:
            xml_parts.append(f'{indent}<groupSet>')
            for item in group_set:
                xml_parts.append(f'{indent}    <item>')
                group_id = item.get("groupId") or item.get("GroupId") or ""
                group_name = item.get("groupName") or item.get("GroupName") or ""
                if group_id != "":
                    xml_parts.append(f'{indent}        <groupId>{esc(str(group_id))}</groupId>')
                if group_name != "":
                    xml_parts.append(f'{indent}        <groupName>{esc(str(group_name))}</groupName>')
                xml_parts.append(f'{indent}    </item>')
            xml_parts.append(f'{indent}</groupSet>')
        else:
            xml_parts.append(f'{indent}<groupSet/>')
        return xml_parts

    @staticmethod
    def serialize_assign_ipv6_addresses_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AssignIpv6AddressesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize assignedIpv6Addresses
        _assignedIpv6Addresses_key = None
        if "assignedIpv6Addresses" in data:
            _assignedIpv6Addresses_key = "assignedIpv6Addresses"
        elif "AssignedIpv6Addresses" in data:
            _assignedIpv6Addresses_key = "AssignedIpv6Addresses"
        if _assignedIpv6Addresses_key:
            param_data = data[_assignedIpv6Addresses_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<assignedIpv6AddressesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</assignedIpv6AddressesSet>')
            else:
                xml_parts.append(f'{indent_str}<assignedIpv6AddressesSet/>')
        # Serialize assignedIpv6PrefixSet
        _assignedIpv6PrefixSet_key = None
        if "assignedIpv6PrefixSet" in data:
            _assignedIpv6PrefixSet_key = "assignedIpv6PrefixSet"
        elif "AssignedIpv6PrefixSet" in data:
            _assignedIpv6PrefixSet_key = "AssignedIpv6PrefixSet"
        elif "AssignedIpv6Prefixs" in data:
            _assignedIpv6PrefixSet_key = "AssignedIpv6Prefixs"
        if _assignedIpv6PrefixSet_key:
            param_data = data[_assignedIpv6PrefixSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<assignedIpv6PrefixSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</assignedIpv6PrefixSet>')
            else:
                xml_parts.append(f'{indent_str}<assignedIpv6PrefixSet/>')
        # Serialize networkInterfaceId
        _networkInterfaceId_key = None
        if "networkInterfaceId" in data:
            _networkInterfaceId_key = "networkInterfaceId"
        elif "NetworkInterfaceId" in data:
            _networkInterfaceId_key = "NetworkInterfaceId"
        if _networkInterfaceId_key:
            param_data = data[_networkInterfaceId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkInterfaceId>{esc(str(param_data))}</networkInterfaceId>')
        xml_parts.append(f'</AssignIpv6AddressesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_assign_private_ip_addresses_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AssignPrivateIpAddressesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize assignedIpv4PrefixSet
        _assignedIpv4PrefixSet_key = None
        if "assignedIpv4PrefixSet" in data:
            _assignedIpv4PrefixSet_key = "assignedIpv4PrefixSet"
        elif "AssignedIpv4PrefixSet" in data:
            _assignedIpv4PrefixSet_key = "AssignedIpv4PrefixSet"
        elif "AssignedIpv4Prefixs" in data:
            _assignedIpv4PrefixSet_key = "AssignedIpv4Prefixs"
        if _assignedIpv4PrefixSet_key:
            param_data = data[_assignedIpv4PrefixSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<assignedIpv4PrefixSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</assignedIpv4PrefixSet>')
            else:
                xml_parts.append(f'{indent_str}<assignedIpv4PrefixSet/>')
        # Serialize assignedPrivateIpAddressesSet
        _assignedPrivateIpAddressesSet_key = None
        if "assignedPrivateIpAddressesSet" in data:
            _assignedPrivateIpAddressesSet_key = "assignedPrivateIpAddressesSet"
        elif "AssignedPrivateIpAddressesSet" in data:
            _assignedPrivateIpAddressesSet_key = "AssignedPrivateIpAddressesSet"
        elif "AssignedPrivateIpAddressess" in data:
            _assignedPrivateIpAddressesSet_key = "AssignedPrivateIpAddressess"
        if _assignedPrivateIpAddressesSet_key:
            param_data = data[_assignedPrivateIpAddressesSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<assignedPrivateIpAddressesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</assignedPrivateIpAddressesSet>')
            else:
                xml_parts.append(f'{indent_str}<assignedPrivateIpAddressesSet/>')
        # Serialize networkInterfaceId
        _networkInterfaceId_key = None
        if "networkInterfaceId" in data:
            _networkInterfaceId_key = "networkInterfaceId"
        elif "NetworkInterfaceId" in data:
            _networkInterfaceId_key = "NetworkInterfaceId"
        if _networkInterfaceId_key:
            param_data = data[_networkInterfaceId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkInterfaceId>{esc(str(param_data))}</networkInterfaceId>')
        xml_parts.append(f'</AssignPrivateIpAddressesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_attach_network_interface_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AttachNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize attachmentId
        _attachmentId_key = None
        if "attachmentId" in data:
            _attachmentId_key = "attachmentId"
        elif "AttachmentId" in data:
            _attachmentId_key = "AttachmentId"
        if _attachmentId_key:
            param_data = data[_attachmentId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<attachmentId>{esc(str(param_data))}</attachmentId>')
        # Serialize networkCardIndex
        _networkCardIndex_key = None
        if "networkCardIndex" in data:
            _networkCardIndex_key = "networkCardIndex"
        elif "NetworkCardIndex" in data:
            _networkCardIndex_key = "NetworkCardIndex"
        if _networkCardIndex_key:
            param_data = data[_networkCardIndex_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkCardIndex>{esc(str(param_data))}</networkCardIndex>')
        xml_parts.append(f'</AttachNetworkInterfaceResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def _serialize_group_set(group_set: List[Dict[str, Any]], indent_level: int) -> List[str]:
        xml_parts = []
        indent = '    ' * indent_level
        if group_set:
            xml_parts.append(f'{indent}<groupSet>')
            for item in group_set:
                xml_parts.append(f'{indent}    <item>')
                group_id = item.get("groupId") or item.get("GroupId") or ""
                group_name = item.get("groupName") or item.get("GroupName") or ""
                if group_id != "":
                    xml_parts.append(f'{indent}        <groupId>{esc(str(group_id))}</groupId>')
                if group_name != "":
                    xml_parts.append(f'{indent}        <groupName>{esc(str(group_name))}</groupName>')
                xml_parts.append(f'{indent}    </item>')
            xml_parts.append(f'{indent}</groupSet>')
        else:
            xml_parts.append(f'{indent}<groupSet/>')
        return xml_parts

    @staticmethod
    def serialize_create_network_interface_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize clientToken
        _clientToken_key = None
        if "clientToken" in data:
            _clientToken_key = "clientToken"
        elif "ClientToken" in data:
            _clientToken_key = "ClientToken"
        if _clientToken_key:
            param_data = data[_clientToken_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<clientToken>{esc(str(param_data))}</clientToken>')
        # Serialize networkInterface
        _networkInterface_key = None
        if "networkInterface" in data:
            _networkInterface_key = "networkInterface"
        elif "NetworkInterface" in data:
            _networkInterface_key = "NetworkInterface"
        if _networkInterface_key:
            param_data = data[_networkInterface_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkInterface>')
            for key, value in param_data.items():
                if key == "groupSet":
                    xml_parts.extend(
                        elasticnetworkinterface_ResponseSerializer._serialize_group_set(
                            value, 2
                        )
                    )
                elif value is None:
                    continue
                elif isinstance(value, dict):
                    xml_parts.append(f'        <{key}>')
                    xml_parts.extend(
                        elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(
                            value, 3
                        )
                    )
                    xml_parts.append(f'        </{key}>')
                elif isinstance(value, list):
                    xml_parts.append(f'        <{key}>')
                    for item in value:
                        if isinstance(item, dict):
                            xml_parts.append(f'            <item>')
                            xml_parts.extend(
                                elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(
                                    item, 4
                                )
                            )
                            xml_parts.append(f'            </item>')
                        else:
                            xml_parts.append(f'            <item>{esc(str(item))}</item>')
                    xml_parts.append(f'        </{key}>')
                elif isinstance(value, bool):
                    xml_parts.append(f'        <{key}>{str(value).lower()}</{key}>')
                else:
                    xml_parts.append(f'        <{key}>{esc(str(value))}</{key}>')
            xml_parts.append(f'{indent_str}</networkInterface>')
        xml_parts.append(f'</CreateNetworkInterfaceResponse>')
        return "".join(xml_parts)

    @staticmethod
    def serialize_create_network_interface_permission_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateNetworkInterfacePermissionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize interfacePermission
        _interfacePermission_key = None
        if "interfacePermission" in data:
            _interfacePermission_key = "interfacePermission"
        elif "InterfacePermission" in data:
            _interfacePermission_key = "InterfacePermission"
        if _interfacePermission_key:
            param_data = data[_interfacePermission_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<interfacePermission>')
            xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</interfacePermission>')
        xml_parts.append(f'</CreateNetworkInterfacePermissionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_network_interface_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</DeleteNetworkInterfaceResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_network_interface_permission_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteNetworkInterfacePermissionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</DeleteNetworkInterfacePermissionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_network_interface_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeNetworkInterfaceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize associatePublicIpAddress
        _associatePublicIpAddress_key = None
        if "associatePublicIpAddress" in data:
            _associatePublicIpAddress_key = "associatePublicIpAddress"
        elif "AssociatePublicIpAddress" in data:
            _associatePublicIpAddress_key = "AssociatePublicIpAddress"
        if _associatePublicIpAddress_key:
            param_data = data[_associatePublicIpAddress_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<associatePublicIpAddressSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</associatePublicIpAddressSet>')
            else:
                xml_parts.append(f'{indent_str}<associatePublicIpAddressSet/>')
        # Serialize attachment
        _attachment_key = None
        if "attachment" in data:
            _attachment_key = "attachment"
        elif "Attachment" in data:
            _attachment_key = "Attachment"
        if _attachment_key:
            param_data = data[_attachment_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<attachment>')
            xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</attachment>')
        # Serialize description
        _description_key = None
        if "description" in data:
            _description_key = "description"
        elif "Description" in data:
            _description_key = "Description"
        if _description_key:
            param_data = data[_description_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<description>')
            xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</description>')
        # Serialize groupSet
        _groupSet_key = None
        if "groupSet" in data:
            _groupSet_key = "groupSet"
        elif "GroupSet" in data:
            _groupSet_key = "GroupSet"
        elif "Groups" in data:
            _groupSet_key = "Groups"
        if _groupSet_key:
            param_data = data[_groupSet_key]
            xml_parts.extend(
                elasticnetworkinterface_ResponseSerializer._serialize_group_set(
                    param_data, 1
                )
            )
        # Serialize networkInterfaceId
        _networkInterfaceId_key = None
        if "networkInterfaceId" in data:
            _networkInterfaceId_key = "networkInterfaceId"
        elif "NetworkInterfaceId" in data:
            _networkInterfaceId_key = "NetworkInterfaceId"
        if _networkInterfaceId_key:
            param_data = data[_networkInterfaceId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkInterfaceId>{esc(str(param_data))}</networkInterfaceId>')
        # Serialize sourceDestCheck
        _sourceDestCheck_key = None
        if "sourceDestCheck" in data:
            _sourceDestCheck_key = "sourceDestCheck"
        elif "SourceDestCheck" in data:
            _sourceDestCheck_key = "SourceDestCheck"
        if _sourceDestCheck_key:
            param_data = data[_sourceDestCheck_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<sourceDestCheck>')
            xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</sourceDestCheck>')
        xml_parts.append(f'</DescribeNetworkInterfaceAttributeResponse>')
        return "".join(xml_parts)

    @staticmethod
    def serialize_describe_network_interface_permissions_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeNetworkInterfacePermissionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize networkInterfacePermissions
        _networkInterfacePermissions_key = None
        if "networkInterfacePermissions" in data:
            _networkInterfacePermissions_key = "networkInterfacePermissions"
        elif "NetworkInterfacePermissions" in data:
            _networkInterfacePermissions_key = "NetworkInterfacePermissions"
        if _networkInterfacePermissions_key:
            param_data = data[_networkInterfacePermissions_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<networkInterfacePermissionsSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</networkInterfacePermissionsSet>')
            else:
                xml_parts.append(f'{indent_str}<networkInterfacePermissionsSet/>')
        # Serialize nextToken
        _nextToken_key = None
        if "nextToken" in data:
            _nextToken_key = "nextToken"
        elif "NextToken" in data:
            _nextToken_key = "NextToken"
        if _nextToken_key:
            param_data = data[_nextToken_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<nextToken>{esc(str(param_data))}</nextToken>')
        xml_parts.append(f'</DescribeNetworkInterfacePermissionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_network_interfaces_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeNetworkInterfacesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize networkInterfaceSet
        _networkInterfaceSet_key = None
        if "networkInterfaceSet" in data:
            _networkInterfaceSet_key = "networkInterfaceSet"
        elif "NetworkInterfaceSet" in data:
            _networkInterfaceSet_key = "NetworkInterfaceSet"
        elif "NetworkInterfaces" in data:
            _networkInterfaceSet_key = "NetworkInterfaces"
        if _networkInterfaceSet_key:
            param_data = data[_networkInterfaceSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<networkInterfaceSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    for key, value in item.items():
                        if key == "groupSet":
                            xml_parts.extend(
                                elasticnetworkinterface_ResponseSerializer._serialize_group_set(
                                    value, 3
                                )
                            )
                        elif value is None:
                            continue
                        elif isinstance(value, dict):
                            xml_parts.append(f'            <{key}>')
                            xml_parts.extend(
                                elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(
                                    value, 4
                                )
                            )
                            xml_parts.append(f'            </{key}>')
                        elif isinstance(value, list):
                            xml_parts.append(f'            <{key}>')
                            for sub_item in value:
                                if isinstance(sub_item, dict):
                                    xml_parts.append(f'                <item>')
                                    xml_parts.extend(
                                        elasticnetworkinterface_ResponseSerializer._serialize_nested_fields(
                                            sub_item, 5
                                        )
                                    )
                                    xml_parts.append(f'                </item>')
                                else:
                                    xml_parts.append(
                                        f'                <item>{esc(str(sub_item))}</item>'
                                    )
                            xml_parts.append(f'            </{key}>')
                        elif isinstance(value, bool):
                            xml_parts.append(f'            <{key}>{str(value).lower()}</{key}>')
                        else:
                            xml_parts.append(f'            <{key}>{esc(str(value))}</{key}>')
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</networkInterfaceSet>')
            else:
                xml_parts.append(f'{indent_str}<networkInterfaceSet/>')
        # Serialize nextToken
        _nextToken_key = None
        if "nextToken" in data:
            _nextToken_key = "nextToken"
        elif "NextToken" in data:
            _nextToken_key = "NextToken"
        if _nextToken_key:
            param_data = data[_nextToken_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<nextToken>{esc(str(param_data))}</nextToken>')
        xml_parts.append(f'</DescribeNetworkInterfacesResponse>')
        return "".join(xml_parts)

    @staticmethod
    def serialize_detach_network_interface_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DetachNetworkInterfaceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</DetachNetworkInterfaceResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_network_interface_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyNetworkInterfaceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</ModifyNetworkInterfaceAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_reset_network_interface_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ResetNetworkInterfaceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</ResetNetworkInterfaceAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_unassign_ipv6_addresses_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<UnassignIpv6AddressesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize networkInterfaceId
        _networkInterfaceId_key = None
        if "networkInterfaceId" in data:
            _networkInterfaceId_key = "networkInterfaceId"
        elif "NetworkInterfaceId" in data:
            _networkInterfaceId_key = "NetworkInterfaceId"
        if _networkInterfaceId_key:
            param_data = data[_networkInterfaceId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<networkInterfaceId>{esc(str(param_data))}</networkInterfaceId>')
        # Serialize unassignedIpv6Addresses
        _unassignedIpv6Addresses_key = None
        if "unassignedIpv6Addresses" in data:
            _unassignedIpv6Addresses_key = "unassignedIpv6Addresses"
        elif "UnassignedIpv6Addresses" in data:
            _unassignedIpv6Addresses_key = "UnassignedIpv6Addresses"
        if _unassignedIpv6Addresses_key:
            param_data = data[_unassignedIpv6Addresses_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<unassignedIpv6AddressesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</unassignedIpv6AddressesSet>')
            else:
                xml_parts.append(f'{indent_str}<unassignedIpv6AddressesSet/>')
        # Serialize unassignedIpv6PrefixSet
        _unassignedIpv6PrefixSet_key = None
        if "unassignedIpv6PrefixSet" in data:
            _unassignedIpv6PrefixSet_key = "unassignedIpv6PrefixSet"
        elif "UnassignedIpv6PrefixSet" in data:
            _unassignedIpv6PrefixSet_key = "UnassignedIpv6PrefixSet"
        elif "UnassignedIpv6Prefixs" in data:
            _unassignedIpv6PrefixSet_key = "UnassignedIpv6Prefixs"
        if _unassignedIpv6PrefixSet_key:
            param_data = data[_unassignedIpv6PrefixSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<unassignedIpv6PrefixSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</unassignedIpv6PrefixSet>')
            else:
                xml_parts.append(f'{indent_str}<unassignedIpv6PrefixSet/>')
        xml_parts.append(f'</UnassignIpv6AddressesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_unassign_private_ip_addresses_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<UnassignPrivateIpAddressesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize return
        _return_key = None
        if "return" in data:
            _return_key = "return"
        elif "Return" in data:
            _return_key = "Return"
        if _return_key:
            param_data = data[_return_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<return>{esc(str(param_data))}</return>')
        xml_parts.append(f'</UnassignPrivateIpAddressesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AssignIpv6Addresses": elasticnetworkinterface_ResponseSerializer.serialize_assign_ipv6_addresses_response,
            "AssignPrivateIpAddresses": elasticnetworkinterface_ResponseSerializer.serialize_assign_private_ip_addresses_response,
            "AttachNetworkInterface": elasticnetworkinterface_ResponseSerializer.serialize_attach_network_interface_response,
            "CreateNetworkInterface": elasticnetworkinterface_ResponseSerializer.serialize_create_network_interface_response,
            "CreateNetworkInterfacePermission": elasticnetworkinterface_ResponseSerializer.serialize_create_network_interface_permission_response,
            "DeleteNetworkInterface": elasticnetworkinterface_ResponseSerializer.serialize_delete_network_interface_response,
            "DeleteNetworkInterfacePermission": elasticnetworkinterface_ResponseSerializer.serialize_delete_network_interface_permission_response,
            "DescribeNetworkInterfaceAttribute": elasticnetworkinterface_ResponseSerializer.serialize_describe_network_interface_attribute_response,
            "DescribeNetworkInterfacePermissions": elasticnetworkinterface_ResponseSerializer.serialize_describe_network_interface_permissions_response,
            "DescribeNetworkInterfaces": elasticnetworkinterface_ResponseSerializer.serialize_describe_network_interfaces_response,
            "DetachNetworkInterface": elasticnetworkinterface_ResponseSerializer.serialize_detach_network_interface_response,
            "ModifyNetworkInterfaceAttribute": elasticnetworkinterface_ResponseSerializer.serialize_modify_network_interface_attribute_response,
            "ResetNetworkInterfaceAttribute": elasticnetworkinterface_ResponseSerializer.serialize_reset_network_interface_attribute_response,
            "UnassignIpv6Addresses": elasticnetworkinterface_ResponseSerializer.serialize_unassign_ipv6_addresses_response,
            "UnassignPrivateIpAddresses": elasticnetworkinterface_ResponseSerializer.serialize_unassign_private_ip_addresses_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)

