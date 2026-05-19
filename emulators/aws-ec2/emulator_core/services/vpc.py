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
class Vpc:
    block_public_access_states: Dict[str, Any] = field(default_factory=dict)
    cidr_block: str = ""
    cidr_block_association_set: List[Any] = field(default_factory=list)
    dhcp_options_id: str = ""
    instance_tenancy: str = ""
    ipv6_cidr_block_association_set: List[Any] = field(default_factory=list)
    is_default: bool = False
    owner_id: str = ""
    state: str = ""
    tag_set: List[Any] = field(default_factory=list)
    vpc_id: str = ""

    # Internal dependency tracking — not in API response
    carrier_gateway_ids: List[str] = field(default_factory=list)  # tracks CarrierGateway children
    client_vpn_endpoint_ids: List[str] = field(default_factory=list)  # tracks ClientVpnEndpoint children
    ec2_instance_connect_endpoint_ids: List[str] = field(default_factory=list)  # tracks Ec2InstanceConnectEndpoint children
    instance_ids: List[str] = field(default_factory=list)  # tracks Instance children
    nat_gateway_ids: List[str] = field(default_factory=list)  # tracks NatGateway children
    network_acl_ids: List[str] = field(default_factory=list)  # tracks NetworkACL children
    security_group_ids: List[str] = field(default_factory=list)  # tracks SecurityGroup children
    subnet_ids: List[str] = field(default_factory=list)  # tracks Subnet children
    target_network_ids: List[str] = field(default_factory=list)  # tracks TargetNetwork children
    vpc_endpoint_ids: List[str] = field(default_factory=list)  # tracks VpcEndpoint children
    route_table_ids: List[str] = field(default_factory=list)  # tracks RouteTable children
    internet_gateway_ids: List[str] = field(default_factory=list)  # tracks InternetGateway children
    vpc_network_interface_ids: List[str] = field(default_factory=list)  # tracks ElasticNetworkInterface children

    enable_dns_support: bool = True
    enable_dns_hostnames: bool = False
    enable_network_address_usage_metrics: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blockPublicAccessStates": self.block_public_access_states,
            "cidrBlock": self.cidr_block,
            "cidrBlockAssociationSet": self.cidr_block_association_set,
            "dhcpOptionsId": self.dhcp_options_id,
            "instanceTenancy": self.instance_tenancy,
            "ipv6CidrBlockAssociationSet": self.ipv6_cidr_block_association_set,
            "isDefault": self.is_default,
            "ownerId": self.owner_id,
            "state": self.state,
            "tagSet": self.tag_set,
            "vpcId": self.vpc_id,
        }

class Vpc_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.vpcs  # alias to shared store

    # Cross-resource parent registration (do this in Create/Delete methods):
    #   Create: self.state.dhcp_options.get(params['dhcp_options_id']).vpc_ids.append(new_id)
    #   Delete: self.state.dhcp_options.get(resource.dhcp_options_id).vpc_ids.remove(resource_id)

    def _get_vpc_or_error(self, vpc_id: str, message: Optional[str] = None):
        vpc = self.resources.get(vpc_id)
        if not vpc:
            return None, create_error_response(
                "InvalidVpcID.NotFound",
                message or f"Vpc '{vpc_id}' does not exist."
            )
        return vpc, None

    def _collect_tags(self, tag_specs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        tags: List[Dict[str, str]] = []
        for spec in tag_specs or []:
            resource_type = spec.get("ResourceType")
            if resource_type and resource_type != "vpc":
                continue
            for tag in spec.get("Tag", []) or []:
                key = tag.get("Key")
                if key is None:
                    continue
                tags.append({"Key": key, "Value": tag.get("Value")})
        return tags

    def _build_cidr_association(self, association_id: str, cidr_block: str) -> Dict[str, Any]:
        return {
            "associationId": association_id,
            "cidrBlock": cidr_block,
            "cidrBlockState": {
                "state": "associated",
                "statusMessage": "",
            },
        }

    def _build_ipv6_association(
        self,
        association_id: str,
        ipv6_cidr_block: str,
        ip_source: str = "amazon",
        ipv6_pool: Optional[str] = None,
        network_border_group: Optional[str] = None,
        ipv6_address_attribute: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "associationId": association_id,
            "ipSource": ip_source,
            "ipv6AddressAttribute": ipv6_address_attribute,
            "ipv6CidrBlock": ipv6_cidr_block,
            "ipv6CidrBlockState": {
                "state": "associated",
                "statusMessage": "",
            },
            "ipv6Pool": ipv6_pool,
            "networkBorderGroup": network_border_group,
        }

    def AssociateVpcCidrBlock(self, params: Dict[str, Any]):
        """Associates a CIDR block with your VPC. You can associate a secondary IPv4 CIDR block,
            an Amazon-provided IPv6 CIDR block, or an IPv6 CIDR block from an IPv6 address pool that
            you provisioned through bring your own IP addresses (BYOIP). You must specify one of the following in"""

        vpc_id = params.get("VpcId")
        if not vpc_id:
            return create_error_response("MissingParameter", "Missing required parameter: VpcId")

        vpc = self.resources.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")

        cidr_block = params.get("CidrBlock") or ""
        ipv6_cidr_block = params.get("Ipv6CidrBlock") or ""
        amazon_ipv6 = str2bool(params.get("AmazonProvidedIpv6CidrBlock"))

        if not cidr_block and not ipv6_cidr_block and not amazon_ipv6:
            return create_error_response(
                "MissingParameter",
                "Missing required parameter: CidrBlock or Ipv6CidrBlock",
            )

        cidr_assoc = None
        ipv6_assoc = None

        if cidr_block or params.get("Ipv4IpamPoolId"):
            if not cidr_block:
                netmask = params.get("Ipv4NetmaskLength") or 16
                cidr_block = f"10.0.0.0/{netmask}"
            cidr_assoc = self._build_cidr_association(self._generate_id("vpc-cidr-assoc"), cidr_block)
            vpc.cidr_block_association_set.append(cidr_assoc)

        if not ipv6_cidr_block and amazon_ipv6:
            ipv6_cidr_block = "2001:db8:0:1::/56"

        if ipv6_cidr_block or params.get("Ipv6Pool") or params.get("Ipv6IpamPoolId"):
            if not ipv6_cidr_block:
                netmask = params.get("Ipv6NetmaskLength") or 56
                ipv6_cidr_block = f"2001:db8:0:1::{netmask}"
            ipv6_assoc = self._build_ipv6_association(
                self._generate_id("vpc-cidr-assoc"),
                ipv6_cidr_block,
                ip_source="amazon" if amazon_ipv6 or not params.get("Ipv6Pool") else "byoip",
                ipv6_pool=params.get("Ipv6Pool") or params.get("Ipv6IpamPoolId"),
                network_border_group=params.get("Ipv6CidrBlockNetworkBorderGroup"),
                ipv6_address_attribute="",
            )
            vpc.ipv6_cidr_block_association_set.append(ipv6_assoc)

        return {
            'cidrBlockAssociation': cidr_assoc or {
                'associationId': None,
                'cidrBlock': None,
                'cidrBlockState': {
                    'state': None,
                    'statusMessage': None,
                    },
                },
            'ipv6CidrBlockAssociation': ipv6_assoc or {
                'associationId': None,
                'ipSource': None,
                'ipv6AddressAttribute': None,
                'ipv6CidrBlock': None,
                'ipv6CidrBlockState': {
                    'state': None,
                    'statusMessage': None,
                    },
                'ipv6Pool': None,
                'networkBorderGroup': None,
                },
            'vpcId': vpc.vpc_id,
            }

    def CreateDefaultVpc(self, params: Dict[str, Any]):
        """Creates a default VPC with a size/16IPv4 CIDR block and a default subnet
			in each Availability Zone. For more information about the components of a default VPC,
			seeDefault VPCsin theAmazon VPC User Guide. You cannot specify the components of the 
		    default VPC yourself. If you deleted your """

        existing_default = next((vpc for vpc in self.resources.values() if vpc.is_default), None)
        if existing_default:
            return create_error_response("DefaultVpcAlreadyExists", "Default VPC already exists.")

        vpc_id = self._generate_id("vpc")
        cidr_block = "172.31.0.0/16"
        cidr_block_association_set = [
            self._build_cidr_association(self._generate_id("vpc-cidr-assoc"), cidr_block)
        ]

        resource = Vpc(
            block_public_access_states={"internetGatewayBlockMode": "off"},
            cidr_block=cidr_block,
            cidr_block_association_set=cidr_block_association_set,
            dhcp_options_id="",
            instance_tenancy="default",
            ipv6_cidr_block_association_set=[],
            is_default=True,
            owner_id="",
            state="available",
            tag_set=[],
            vpc_id=vpc_id,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            enable_network_address_usage_metrics=False,
        )
        self.resources[vpc_id] = resource

        parent = self.state.dhcp_options.get(resource.dhcp_options_id)
        if parent and hasattr(parent, "vpc_ids"):
            parent.vpc_ids.append(vpc_id)

        return {
            'vpc': resource.to_dict(),
            }

    def CreateVpc(self, params: Dict[str, Any]):
        """Creates a VPC with the specified CIDR blocks. A VPC must have an associated IPv4 CIDR block. You can choose an IPv4 CIDR block or an
            IPAM-allocated IPv4 CIDR block. You can optionally associate an IPv6 CIDR block with a
            VPC. You can choose an IPv6 CIDR block, an Amazon-provid"""

        cidr_block = params.get("CidrBlock")
        if not cidr_block:
            return create_error_response("MissingParameter", "Missing required parameter: CidrBlock")

        instance_tenancy = params.get("InstanceTenancy") or "default"
        tag_set = self._collect_tags(params.get("TagSpecification.N", []) or [])

        vpc_id = self._generate_id("vpc")
        cidr_block_association_set = [
            self._build_cidr_association(self._generate_id("vpc-cidr-assoc"), cidr_block)
        ]

        ipv6_cidr_block = params.get("Ipv6CidrBlock") or ""
        amazon_ipv6 = str2bool(params.get("AmazonProvidedIpv6CidrBlock"))
        if not ipv6_cidr_block and amazon_ipv6:
            ipv6_cidr_block = "2001:db8:0:1::/56"

        ipv6_cidr_block_association_set: List[Dict[str, Any]] = []
        if ipv6_cidr_block:
            ipv6_cidr_block_association_set = [
                self._build_ipv6_association(
                    self._generate_id("vpc-cidr-assoc"),
                    ipv6_cidr_block,
                    ip_source="amazon",
                    ipv6_pool=params.get("Ipv6Pool") or params.get("Ipv6IpamPoolId"),
                    network_border_group=params.get("Ipv6CidrBlockNetworkBorderGroup"),
                    ipv6_address_attribute="",
                )
            ]

        resource = Vpc(
            block_public_access_states={"internetGatewayBlockMode": "off"},
            cidr_block=cidr_block,
            cidr_block_association_set=cidr_block_association_set,
            dhcp_options_id="",
            instance_tenancy=instance_tenancy,
            ipv6_cidr_block_association_set=ipv6_cidr_block_association_set,
            is_default=False,
            owner_id="",
            state="available",
            tag_set=tag_set,
            vpc_id=vpc_id,
            enable_dns_support=True,
            enable_dns_hostnames=False,
            enable_network_address_usage_metrics=False,
        )
        self.resources[vpc_id] = resource

        parent = self.state.dhcp_options.get(resource.dhcp_options_id)
        if parent and hasattr(parent, "vpc_ids"):
            parent.vpc_ids.append(vpc_id)

        return {
            'vpc': resource.to_dict(),
            }

    def DeleteVpc(self, params: Dict[str, Any]):
        """Deletes the specified VPC. You must detach or delete all gateways and resources that are associated 
		  with the VPC before you can delete it. For example, you must terminate all instances running in the VPC, 
		  delete all security groups associated with the VPC (except the default one), delete a"""

        vpc_id = params.get("VpcId")
        if not vpc_id:
            return create_error_response("MissingParameter", "Missing required parameter: VpcId")

        vpc = self.resources.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")

        if getattr(vpc, 'carrier_gateway_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent CarrierGateway(s) and cannot be deleted.')
        if getattr(vpc, 'client_vpn_endpoint_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent ClientVpnEndpoint(s) and cannot be deleted.')
        if getattr(vpc, 'ec2_instance_connect_endpoint_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent Ec2InstanceConnectEndpoint(s) and cannot be deleted.')
        if getattr(vpc, 'instance_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent Instance(s) and cannot be deleted.')
        if getattr(vpc, 'nat_gateway_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent NatGateway(s) and cannot be deleted.')
        if getattr(vpc, 'network_acl_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent NetworkACL(s) and cannot be deleted.')
        if getattr(vpc, 'security_group_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent SecurityGroup(s) and cannot be deleted.')
        if getattr(vpc, 'subnet_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent Subnet(s) and cannot be deleted.')
        if getattr(vpc, 'target_network_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent TargetNetwork(s) and cannot be deleted.')
        if getattr(vpc, 'vpc_endpoint_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent VpcEndpoint(s) and cannot be deleted.')
        if getattr(vpc, 'route_table_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent RouteTable(s) and cannot be deleted.')
        if getattr(vpc, 'internet_gateway_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent InternetGateway(s) and cannot be deleted.')
        if getattr(vpc, 'vpc_network_interface_ids', []):
            return create_error_response('DependencyViolation', 'Vpc has dependent ElasticNetworkInterface(s) and cannot be deleted.')

        parent = self.state.dhcp_options.get(vpc.dhcp_options_id)
        if parent and hasattr(parent, 'vpc_ids') and vpc_id in parent.vpc_ids:
            parent.vpc_ids.remove(vpc_id)

        del self.resources[vpc_id]

        return {
            'return': True,
            }

    def DescribeVpcAttribute(self, params: Dict[str, Any]):
        """Describes the specified attribute of the specified VPC. You can specify only one attribute at a time."""

        attribute = params.get("Attribute")
        if not attribute:
            return create_error_response("MissingParameter", "Missing required parameter: Attribute")

        vpc_id = params.get("VpcId")
        if not vpc_id:
            return create_error_response("MissingParameter", "Missing required parameter: VpcId")

        vpc = self.resources.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")

        supported_attributes = {
            "enableDnsSupport": ("enableDnsSupport", vpc.enable_dns_support),
            "enableDnsHostnames": ("enableDnsHostnames", vpc.enable_dns_hostnames),
            "enableNetworkAddressUsageMetrics": (
                "enableNetworkAddressUsageMetrics",
                vpc.enable_network_address_usage_metrics,
            ),
        }
        if attribute not in supported_attributes:
            return create_error_response("InvalidParameterValue", f"Invalid attribute '{attribute}'")

        response_key, value = supported_attributes[attribute]
        return {
            response_key: {
                'value': value,
                },
            'vpcId': vpc.vpc_id,
            }

    def DescribeVpcs(self, params: Dict[str, Any]):
        """Describes your VPCs. The default is to describe all your VPCs. 
          Alternatively, you can specify specific VPC IDs or filter the results to
          include only the VPCs that match specific criteria."""

        vpc_ids = params.get("VpcId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        if vpc_ids:
            resources = []
            for vpc_id in vpc_ids:
                resource = self.resources.get(vpc_id)
                if not resource:
                    return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")
                resources.append(resource)
        else:
            resources = list(self.resources.values())

        filters = params.get("Filter.N", []) or []
        special_filter_names = {
            "cidr-block-association.association-id",
            "ipv6-cidr-block-association.association-id",
        }
        for resource_filter in filters:
            name = resource_filter.get("Name", "")
            values = set(resource_filter.get("Values", []) or [])
            if name not in special_filter_names or not values:
                continue
            association_attr = (
                "ipv6_cidr_block_association_set"
                if name.startswith("ipv6-")
                else "cidr_block_association_set"
            )
            resources = [
                resource
                for resource in resources
                if any(
                    str(association.get("associationId", "")) in values
                    for association in getattr(resource, association_attr, []) or []
                    if isinstance(association, dict)
                )
            ]
        normal_filters = [f for f in filters if f.get("Name", "") not in special_filter_names]
        resources = apply_filters(resources, normal_filters)
        vpc_set = [resource.to_dict() for resource in resources[:max_results]]

        return {
            'nextToken': None,
            'vpcSet': vpc_set,
            }

    def DisassociateVpcCidrBlock(self, params: Dict[str, Any]):
        """Disassociates a CIDR block from a VPC. To disassociate the CIDR block, you must
            specify its association ID. You can get the association ID by usingDescribeVpcs. You must detach or delete all gateways and resources that
            are associated with the CIDR block before you can disasso"""

        association_id = params.get("AssociationId")
        if not association_id:
            return create_error_response("MissingParameter", "Missing required parameter: AssociationId")

        target_vpc = None
        cidr_assoc = None
        ipv6_assoc = None

        for vpc in self.resources.values():
            for assoc in vpc.cidr_block_association_set:
                if assoc.get("associationId") == association_id:
                    target_vpc = vpc
                    cidr_assoc = assoc
                    break
            if cidr_assoc:
                break

        if not cidr_assoc:
            for vpc in self.resources.values():
                for assoc in vpc.ipv6_cidr_block_association_set:
                    if assoc.get("associationId") == association_id:
                        target_vpc = vpc
                        ipv6_assoc = assoc
                        break
                if ipv6_assoc:
                    break

        if not target_vpc or (not cidr_assoc and not ipv6_assoc):
            return create_error_response("InvalidAssociationID.NotFound", f"The ID '{association_id}' does not exist")

        if cidr_assoc:
            state = cidr_assoc.get("cidrBlockState") or {}
            state["state"] = "disassociated"
            state.setdefault("statusMessage", "")
            cidr_assoc["cidrBlockState"] = state
            if cidr_assoc in target_vpc.cidr_block_association_set:
                target_vpc.cidr_block_association_set.remove(cidr_assoc)

        if ipv6_assoc:
            state = ipv6_assoc.get("ipv6CidrBlockState") or {}
            state["state"] = "disassociated"
            state.setdefault("statusMessage", "")
            ipv6_assoc["ipv6CidrBlockState"] = state
            if ipv6_assoc in target_vpc.ipv6_cidr_block_association_set:
                target_vpc.ipv6_cidr_block_association_set.remove(ipv6_assoc)

        return {
            'cidrBlockAssociation': cidr_assoc or {
                'associationId': None,
                'cidrBlock': None,
                'cidrBlockState': {
                    'state': None,
                    'statusMessage': None,
                    },
                },
            'ipv6CidrBlockAssociation': ipv6_assoc or {
                'associationId': None,
                'ipSource': None,
                'ipv6AddressAttribute': None,
                'ipv6CidrBlock': None,
                'ipv6CidrBlockState': {
                    'state': None,
                    'statusMessage': None,
                    },
                'ipv6Pool': None,
                'networkBorderGroup': None,
                },
            'vpcId': target_vpc.vpc_id,
            }

    def ModifyVpcAttribute(self, params: Dict[str, Any]):
        """Modifies the specified attribute of the specified VPC."""

        vpc_id = params.get("VpcId")
        if not vpc_id:
            return create_error_response("MissingParameter", "Missing required parameter: VpcId")

        vpc = self.resources.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")

        def _parse_bool(value: Any) -> bool:
            if isinstance(value, dict):
                value = value.get("Value")
            return str2bool(value)

        if params.get("EnableDnsHostnames") is not None:
            vpc.enable_dns_hostnames = _parse_bool(params.get("EnableDnsHostnames"))

        if params.get("EnableDnsSupport") is not None:
            vpc.enable_dns_support = _parse_bool(params.get("EnableDnsSupport"))

        if params.get("EnableNetworkAddressUsageMetrics") is not None:
            vpc.enable_network_address_usage_metrics = _parse_bool(params.get("EnableNetworkAddressUsageMetrics"))

        return {
            'return': True,
            }

    def ModifyVpcTenancy(self, params: Dict[str, Any]):
        """Modifies the instance tenancy attribute of the specified VPC. You can change the
            instance tenancy attribute of a VPC todefaultonly. You cannot change the
            instance tenancy attribute todedicated. After you modify the tenancy of the VPC, any new instances that you launch into th"""

        instance_tenancy = params.get("InstanceTenancy")
        if not instance_tenancy:
            return create_error_response("MissingParameter", "Missing required parameter: InstanceTenancy")

        vpc_id = params.get("VpcId")
        if not vpc_id:
            return create_error_response("MissingParameter", "Missing required parameter: VpcId")

        vpc = self.resources.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"The ID '{vpc_id}' does not exist")

        if instance_tenancy != "default":
            return create_error_response("InvalidParameterValue", "InstanceTenancy must be 'default'")

        vpc.instance_tenancy = instance_tenancy

        return {
            'return': True,
            }

    def _generate_id(self, prefix: str = 'vpc') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class vpc_RequestParser:
    @staticmethod
    def parse_associate_vpc_cidr_block_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AmazonProvidedIpv6CidrBlock": get_scalar(md, "AmazonProvidedIpv6CidrBlock"),
            "CidrBlock": get_scalar(md, "CidrBlock"),
            "Ipv4IpamPoolId": get_scalar(md, "Ipv4IpamPoolId"),
            "Ipv4NetmaskLength": get_int(md, "Ipv4NetmaskLength"),
            "Ipv6CidrBlock": get_scalar(md, "Ipv6CidrBlock"),
            "Ipv6CidrBlockNetworkBorderGroup": get_scalar(md, "Ipv6CidrBlockNetworkBorderGroup"),
            "Ipv6IpamPoolId": get_scalar(md, "Ipv6IpamPoolId"),
            "Ipv6NetmaskLength": get_int(md, "Ipv6NetmaskLength"),
            "Ipv6Pool": get_scalar(md, "Ipv6Pool"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_create_default_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_create_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AmazonProvidedIpv6CidrBlock": get_scalar(md, "AmazonProvidedIpv6CidrBlock"),
            "CidrBlock": get_scalar(md, "CidrBlock"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InstanceTenancy": get_scalar(md, "InstanceTenancy"),
            "Ipv4IpamPoolId": get_scalar(md, "Ipv4IpamPoolId"),
            "Ipv4NetmaskLength": get_int(md, "Ipv4NetmaskLength"),
            "Ipv6CidrBlock": get_scalar(md, "Ipv6CidrBlock"),
            "Ipv6CidrBlockNetworkBorderGroup": get_scalar(md, "Ipv6CidrBlockNetworkBorderGroup"),
            "Ipv6IpamPoolId": get_scalar(md, "Ipv6IpamPoolId"),
            "Ipv6NetmaskLength": get_int(md, "Ipv6NetmaskLength"),
            "Ipv6Pool": get_scalar(md, "Ipv6Pool"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VpcEncryptionControl": get_scalar(md, "VpcEncryptionControl"),
        }

    @staticmethod
    def parse_delete_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_describe_vpc_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_describe_vpcs_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "VpcId.N": get_indexed_list(md, "VpcId"),
        }

    @staticmethod
    def parse_disassociate_vpc_cidr_block_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AssociationId": get_scalar(md, "AssociationId"),
        }

    @staticmethod
    def parse_modify_vpc_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "EnableDnsHostnames": get_scalar(md, "EnableDnsHostnames")
                or get_scalar(md, "EnableDnsHostnames.Value"),
            "EnableDnsSupport": get_scalar(md, "EnableDnsSupport")
                or get_scalar(md, "EnableDnsSupport.Value"),
            "EnableNetworkAddressUsageMetrics": get_scalar(md, "EnableNetworkAddressUsageMetrics")
                or get_scalar(md, "EnableNetworkAddressUsageMetrics.Value"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_modify_vpc_tenancy_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InstanceTenancy": get_scalar(md, "InstanceTenancy"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AssociateVpcCidrBlock": vpc_RequestParser.parse_associate_vpc_cidr_block_request,
            "CreateDefaultVpc": vpc_RequestParser.parse_create_default_vpc_request,
            "CreateVpc": vpc_RequestParser.parse_create_vpc_request,
            "DeleteVpc": vpc_RequestParser.parse_delete_vpc_request,
            "DescribeVpcAttribute": vpc_RequestParser.parse_describe_vpc_attribute_request,
            "DescribeVpcs": vpc_RequestParser.parse_describe_vpcs_request,
            "DisassociateVpcCidrBlock": vpc_RequestParser.parse_disassociate_vpc_cidr_block_request,
            "ModifyVpcAttribute": vpc_RequestParser.parse_modify_vpc_attribute_request,
            "ModifyVpcTenancy": vpc_RequestParser.parse_modify_vpc_tenancy_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class vpc_ResponseSerializer:
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
                xml_parts.extend(vpc_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(vpc_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(vpc_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(vpc_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_associate_vpc_cidr_block_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AssociateVpcCidrBlockResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize cidrBlockAssociation
        _cidrBlockAssociation_key = None
        if "cidrBlockAssociation" in data:
            _cidrBlockAssociation_key = "cidrBlockAssociation"
        elif "CidrBlockAssociation" in data:
            _cidrBlockAssociation_key = "CidrBlockAssociation"
        if _cidrBlockAssociation_key:
            param_data = data[_cidrBlockAssociation_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<cidrBlockAssociation>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</cidrBlockAssociation>')
        # Serialize ipv6CidrBlockAssociation
        _ipv6CidrBlockAssociation_key = None
        if "ipv6CidrBlockAssociation" in data:
            _ipv6CidrBlockAssociation_key = "ipv6CidrBlockAssociation"
        elif "Ipv6CidrBlockAssociation" in data:
            _ipv6CidrBlockAssociation_key = "Ipv6CidrBlockAssociation"
        if _ipv6CidrBlockAssociation_key:
            param_data = data[_ipv6CidrBlockAssociation_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<ipv6CidrBlockAssociation>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</ipv6CidrBlockAssociation>')
        # Serialize vpcId
        _vpcId_key = None
        if "vpcId" in data:
            _vpcId_key = "vpcId"
        elif "VpcId" in data:
            _vpcId_key = "VpcId"
        if _vpcId_key:
            param_data = data[_vpcId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpcId>{esc(str(param_data))}</vpcId>')
        xml_parts.append(f'</AssociateVpcCidrBlockResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_default_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateDefaultVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize vpc
        _vpc_key = None
        if "vpc" in data:
            _vpc_key = "vpc"
        elif "Vpc" in data:
            _vpc_key = "Vpc"
        if _vpc_key:
            param_data = data[_vpc_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpc>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</vpc>')
        xml_parts.append(f'</CreateDefaultVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize vpc
        _vpc_key = None
        if "vpc" in data:
            _vpc_key = "vpc"
        elif "Vpc" in data:
            _vpc_key = "Vpc"
        if _vpc_key:
            param_data = data[_vpc_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpc>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</vpc>')
        xml_parts.append(f'</CreateVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_vpc_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        def append_attribute(xml_parts: List[str], data_key: str, tag_name: str) -> None:
            if data_key not in data:
                return
            param_data = data[data_key]
            if isinstance(param_data, list):
                param_data = param_data[0] if param_data else {}
            if isinstance(param_data, dict) and "Value" in param_data and "value" not in param_data:
                param_data = {"value": param_data["Value"]}
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<{tag_name}>')
            if isinstance(param_data, dict):
                xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            elif param_data is not None:
                xml_parts.append(f'{indent_str}    <value>{str(param_data).lower()}</value>')
            xml_parts.append(f'{indent_str}</{tag_name}>')

        xml_parts = []
        xml_parts.append(f'<DescribeVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        append_attribute(xml_parts, "enableDnsHostnames", "enableDnsHostnames")
        append_attribute(xml_parts, "EnableDnsHostnames", "enableDnsHostnames")
        append_attribute(xml_parts, "enableDnsSupport", "enableDnsSupport")
        append_attribute(xml_parts, "EnableDnsSupport", "enableDnsSupport")
        append_attribute(
            xml_parts,
            "enableNetworkAddressUsageMetrics",
            "enableNetworkAddressUsageMetrics",
        )
        append_attribute(
            xml_parts,
            "EnableNetworkAddressUsageMetrics",
            "enableNetworkAddressUsageMetrics",
        )
        # Serialize vpcId
        _vpcId_key = None
        if "vpcId" in data:
            _vpcId_key = "vpcId"
        elif "VpcId" in data:
            _vpcId_key = "VpcId"
        if _vpcId_key:
            param_data = data[_vpcId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpcId>{esc(str(param_data))}</vpcId>')
        xml_parts.append(f'</DescribeVpcAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_vpcs_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeVpcsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
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
        # Serialize vpcSet
        _vpcSet_key = None
        if "vpcSet" in data:
            _vpcSet_key = "vpcSet"
        elif "VpcSet" in data:
            _vpcSet_key = "VpcSet"
        elif "Vpcs" in data:
            _vpcSet_key = "Vpcs"
        if _vpcSet_key:
            param_data = data[_vpcSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<vpcSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</vpcSet>')
            else:
                xml_parts.append(f'{indent_str}<vpcSet/>')
        xml_parts.append(f'</DescribeVpcsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disassociate_vpc_cidr_block_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisassociateVpcCidrBlockResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize cidrBlockAssociation
        _cidrBlockAssociation_key = None
        if "cidrBlockAssociation" in data:
            _cidrBlockAssociation_key = "cidrBlockAssociation"
        elif "CidrBlockAssociation" in data:
            _cidrBlockAssociation_key = "CidrBlockAssociation"
        if _cidrBlockAssociation_key:
            param_data = data[_cidrBlockAssociation_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<cidrBlockAssociation>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</cidrBlockAssociation>')
        # Serialize ipv6CidrBlockAssociation
        _ipv6CidrBlockAssociation_key = None
        if "ipv6CidrBlockAssociation" in data:
            _ipv6CidrBlockAssociation_key = "ipv6CidrBlockAssociation"
        elif "Ipv6CidrBlockAssociation" in data:
            _ipv6CidrBlockAssociation_key = "Ipv6CidrBlockAssociation"
        if _ipv6CidrBlockAssociation_key:
            param_data = data[_ipv6CidrBlockAssociation_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<ipv6CidrBlockAssociation>')
            xml_parts.extend(vpc_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</ipv6CidrBlockAssociation>')
        # Serialize vpcId
        _vpcId_key = None
        if "vpcId" in data:
            _vpcId_key = "vpcId"
        elif "VpcId" in data:
            _vpcId_key = "VpcId"
        if _vpcId_key:
            param_data = data[_vpcId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpcId>{esc(str(param_data))}</vpcId>')
        xml_parts.append(f'</DisassociateVpcCidrBlockResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_vpc_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ModifyVpcAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_vpc_tenancy_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyVpcTenancyResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ModifyVpcTenancyResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AssociateVpcCidrBlock": vpc_ResponseSerializer.serialize_associate_vpc_cidr_block_response,
            "CreateDefaultVpc": vpc_ResponseSerializer.serialize_create_default_vpc_response,
            "CreateVpc": vpc_ResponseSerializer.serialize_create_vpc_response,
            "DeleteVpc": vpc_ResponseSerializer.serialize_delete_vpc_response,
            "DescribeVpcAttribute": vpc_ResponseSerializer.serialize_describe_vpc_attribute_response,
            "DescribeVpcs": vpc_ResponseSerializer.serialize_describe_vpcs_response,
            "DisassociateVpcCidrBlock": vpc_ResponseSerializer.serialize_disassociate_vpc_cidr_block_response,
            "ModifyVpcAttribute": vpc_ResponseSerializer.serialize_modify_vpc_attribute_response,
            "ModifyVpcTenancy": vpc_ResponseSerializer.serialize_modify_vpc_tenancy_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)
