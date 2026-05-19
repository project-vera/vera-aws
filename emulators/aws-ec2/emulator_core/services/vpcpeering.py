from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
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
class VpcPeering:
    accepter_vpc_info: Dict[str, Any] = field(default_factory=dict)
    expiration_time: str = ""
    requester_vpc_info: Dict[str, Any] = field(default_factory=dict)
    status: Dict[str, Any] = field(default_factory=dict)
    tag_set: List[Any] = field(default_factory=list)
    vpc_peering_connection_id: str = ""

    # Internal dependency tracking — not in API response
    route_table_ids: List[str] = field(default_factory=list)  # tracks RouteTable children


    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepterVpcInfo": self.accepter_vpc_info,
            "expirationTime": self.expiration_time,
            "requesterVpcInfo": self.requester_vpc_info,
            "status": self.status,
            "tagSet": self.tag_set,
            "vpcPeeringConnectionId": self.vpc_peering_connection_id,
        }

class VpcPeering_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.vpc_peering  # alias to shared store

    def _require_param(self, params: Dict[str, Any], key: str):
        if not params.get(key):
            return create_error_response("MissingParameter", f"Missing required parameter: {key}")
        return None

    def _get_peering_or_error(self, vpc_peering_connection_id: str):
        resource = self.resources.get(vpc_peering_connection_id)
        if not resource:
            return None, create_error_response(
                "InvalidVpcPeeringConnectionID.NotFound",
                f"The ID '{vpc_peering_connection_id}' does not exist",
            )
        return resource, None


    def AcceptVpcPeeringConnection(self, params: Dict[str, Any]):
        """Accept a VPC peering connection request. To accept a request, the VPC peering connection must
      be in thepending-acceptancestate, and you must be the owner of the peer VPC.
      UseDescribeVpcPeeringConnectionsto view your outstanding VPC
      peering connection requests. For an inter-Region V"""

        error = self._require_param(params, "VpcPeeringConnectionId")
        if error:
            return error

        vpc_peering_connection_id = params.get("VpcPeeringConnectionId")
        resource, error = self._get_peering_or_error(vpc_peering_connection_id)
        if error:
            return error

        status = resource.status or {}
        if status.get("code") != "pending-acceptance":
            return create_error_response(
                "InvalidStateTransition",
                "Vpc peering connection is not in pending-acceptance state.",
            )

        resource.status = {
            "code": "active",
            "message": "Active",
        }

        return {
            'vpcPeeringConnection': resource.to_dict(),
            }

    def CreateVpcPeeringConnection(self, params: Dict[str, Any]):
        """Requests a VPC peering connection between two VPCs: a requester VPC that you own and
		  an accepter VPC with which to create the connection. The accepter VPC can belong to
		  another AWS account and can be in a different Region to the requester VPC. 
          The requester VPC and accepter VPC ca"""

        error = self._require_param(params, "VpcId")
        if error:
            return error

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"VPC '{vpc_id}' does not exist.")

        peer_vpc_id = params.get("PeerVpcId") or vpc_id
        peer_vpc = self.state.vpcs.get(peer_vpc_id)
        if not peer_vpc:
            return create_error_response("InvalidVpcID.NotFound", f"VPC '{peer_vpc_id}' does not exist.")

        tag_specs = params.get("TagSpecification.N", []) or []
        tag_set: List[Dict[str, Any]] = []
        for spec in tag_specs:
            if spec.get("ResourceType") == "vpc-peering-connection":
                tag_set = spec.get("Tags", []) or []
                break

        def _coerce_cidr_set(associations: List[Any], key: str, snake_key: str, fallback: str):
            cidr_set = []
            for item in associations or []:
                value = None
                if isinstance(item, dict):
                    value = item.get(key) or item.get(snake_key)
                elif isinstance(item, str):
                    value = item
                if value:
                    cidr_set.append({key: value})
            if not cidr_set and fallback:
                cidr_set.append({key: fallback})
            return cidr_set

        def _build_vpc_info(vpc_obj, owner_override: Optional[str], region_override: Optional[str]):
            cidr_block = getattr(vpc_obj, "cidr_block", "") or getattr(vpc_obj, "cidrBlock", "")
            cidr_associations = getattr(vpc_obj, "cidr_block_association_set", None) or getattr(
                vpc_obj, "cidrBlockAssociationSet", None
            )
            ipv6_associations = getattr(vpc_obj, "ipv6_cidr_block_association_set", None) or getattr(
                vpc_obj, "ipv6CidrBlockAssociationSet", None
            )
            owner_id = owner_override if owner_override is not None else getattr(vpc_obj, "owner_id", "")
            region = region_override if region_override is not None else (
                getattr(vpc_obj, "region", "") or getattr(vpc_obj, "region_name", "")
            )
            return {
                "cidrBlock": cidr_block,
                "cidrBlockSet": _coerce_cidr_set(cidr_associations, "cidrBlock", "cidr_block", cidr_block),
                "ipv6CidrBlockSet": _coerce_cidr_set(ipv6_associations, "ipv6CidrBlock", "ipv6_cidr_block", ""),
                "ownerId": owner_id,
                "peeringOptions": {
                    "allowDnsResolutionFromRemoteVpc": False,
                    "allowEgressFromLocalClassicLinkToRemoteVpc": False,
                    "allowEgressFromLocalVpcToRemoteClassicLink": False,
                },
                "region": region,
                "vpcId": getattr(vpc_obj, "vpc_id", "") or getattr(vpc_obj, "vpcId", ""),
            }

        requester_info = _build_vpc_info(vpc, None, None)
        accepter_owner = params.get("PeerOwnerId") or getattr(peer_vpc, "owner_id", "")
        accepter_region = params.get("PeerRegion") or (
            getattr(peer_vpc, "region", "") or getattr(peer_vpc, "region_name", "")
        )
        accepter_info = _build_vpc_info(peer_vpc, accepter_owner, accepter_region)

        vpc_peering_connection_id = self._generate_id("pcx")
        status = {
            "code": "pending-acceptance",
            "message": "Pending Acceptance",
        }

        resource = VpcPeering(
            accepter_vpc_info=accepter_info,
            expiration_time=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
            requester_vpc_info=requester_info,
            status=status,
            tag_set=tag_set,
            vpc_peering_connection_id=vpc_peering_connection_id,
        )
        self.resources[vpc_peering_connection_id] = resource

        return {
            'vpcPeeringConnection': resource.to_dict(),
            }

    def DeleteVpcPeeringConnection(self, params: Dict[str, Any]):
        """Deletes a VPC peering connection. Either the owner of the requester VPC or the owner
            of the accepter VPC can delete the VPC peering connection if it's in theactivestate. The owner of the requester VPC can delete a VPC peering
            connection in thepending-acceptancestate. You cann"""

        error = self._require_param(params, "VpcPeeringConnectionId")
        if error:
            return error

        vpc_peering_connection_id = params.get("VpcPeeringConnectionId")
        resource, error = self._get_peering_or_error(vpc_peering_connection_id)
        if error:
            return error

        if getattr(resource, "route_table_ids", []):
            return create_error_response(
                "DependencyViolation",
                "VpcPeering has dependent RouteTable(s) and cannot be deleted.",
            )

        self.resources.pop(vpc_peering_connection_id, None)

        return {
            'return': True,
            }

    def DescribeVpcPeeringConnections(self, params: Dict[str, Any]):
        """Describes your VPC peering connections. The default is to describe all your VPC peering connections. 
          Alternatively, you can specify specific VPC peering connection IDs or filter the results to
          include only the VPC peering connections that match specific criteria."""

        connection_ids = params.get("VpcPeeringConnectionId.N", []) or []
        resources = []
        if connection_ids:
            for connection_id in connection_ids:
                resource = self.resources.get(connection_id)
                if not resource:
                    return create_error_response(
                        "InvalidVpcPeeringConnectionID.NotFound",
                        f"The ID '{connection_id}' does not exist",
                    )
                resources.append(resource)
        else:
            resources = list(self.resources.values())

        filters = params.get("Filter.N", []) or []
        if filters:
            resources = apply_filters(resources, filters)

        max_results = int(params.get("MaxResults") or 100)
        next_token = params.get("NextToken")
        start_index = int(next_token or 0)
        paged = resources[start_index:start_index + max_results]
        new_next_token = None
        if start_index + max_results < len(resources):
            new_next_token = str(start_index + max_results)

        return {
            'nextToken': new_next_token,
            'vpcPeeringConnectionSet': [resource.to_dict() for resource in paged],
            }

    def ModifyVpcPeeringConnectionOptions(self, params: Dict[str, Any]):
        """Modifies the VPC peering connection options on one side of a VPC peering connection. If the peered VPCs are in the same AWS account, you can enable DNS
            resolution for queries from the local VPC. This ensures that queries from the local VPC
            resolve to private IP addresses in t"""

        error = self._require_param(params, "VpcPeeringConnectionId")
        if error:
            return error

        vpc_peering_connection_id = params.get("VpcPeeringConnectionId")
        resource, error = self._get_peering_or_error(vpc_peering_connection_id)
        if error:
            return error

        def _normalize_options(existing: Optional[Dict[str, Any]], updates: Any) -> Dict[str, Any]:
            options = dict(existing or {})
            for key in (
                "allowDnsResolutionFromRemoteVpc",
                "allowEgressFromLocalClassicLinkToRemoteVpc",
                "allowEgressFromLocalVpcToRemoteClassicLink",
            ):
                if key not in options:
                    options[key] = False
            if isinstance(updates, dict):
                for key in options.keys():
                    if key in updates and updates[key] is not None:
                        value = updates[key]
                        if isinstance(value, str):
                            value = str2bool(value)
                        options[key] = bool(value)
            return options

        accepter_updates = params.get("AccepterPeeringConnectionOptions")
        requester_updates = params.get("RequesterPeeringConnectionOptions")

        accepter_info = resource.accepter_vpc_info or {}
        requester_info = resource.requester_vpc_info or {}

        accepter_info["peeringOptions"] = _normalize_options(
            accepter_info.get("peeringOptions"), accepter_updates
        )
        requester_info["peeringOptions"] = _normalize_options(
            requester_info.get("peeringOptions"), requester_updates
        )

        resource.accepter_vpc_info = accepter_info
        resource.requester_vpc_info = requester_info

        return {
            'accepterPeeringConnectionOptions': [accepter_info.get("peeringOptions", {})],
            'requesterPeeringConnectionOptions': [requester_info.get("peeringOptions", {})],
            }

    def RejectVpcPeeringConnection(self, params: Dict[str, Any]):
        """Rejects a VPC peering connection request. The VPC peering connection must be in thepending-acceptancestate. Use theDescribeVpcPeeringConnectionsrequest
			to view your outstanding VPC peering connection requests. To delete an active VPC peering
			connection, or to delete a VPC peering connection re"""

        error = self._require_param(params, "VpcPeeringConnectionId")
        if error:
            return error

        vpc_peering_connection_id = params.get("VpcPeeringConnectionId")
        resource, error = self._get_peering_or_error(vpc_peering_connection_id)
        if error:
            return error

        status = resource.status or {}
        if status.get("code") != "pending-acceptance":
            return create_error_response(
                "InvalidStateTransition",
                "Vpc peering connection is not in pending-acceptance state.",
            )

        resource.status = {
            "code": "rejected",
            "message": "Rejected",
        }

        return {
            'return': True,
            }

    def _generate_id(self, prefix: str = 'vpc') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class vpcpeering_RequestParser:
    @staticmethod
    def parse_accept_vpc_peering_connection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcPeeringConnectionId": get_scalar(md, "VpcPeeringConnectionId"),
        }

    @staticmethod
    def parse_create_vpc_peering_connection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "PeerOwnerId": get_scalar(md, "PeerOwnerId"),
            "PeerRegion": get_scalar(md, "PeerRegion"),
            "PeerVpcId": get_scalar(md, "PeerVpcId"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_delete_vpc_peering_connection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcPeeringConnectionId": get_scalar(md, "VpcPeeringConnectionId"),
        }

    @staticmethod
    def parse_describe_vpc_peering_connections_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "VpcPeeringConnectionId.N": get_indexed_list(md, "VpcPeeringConnectionId"),
        }

    @staticmethod
    def parse_modify_vpc_peering_connection_options_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AccepterPeeringConnectionOptions": get_scalar(md, "AccepterPeeringConnectionOptions"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "RequesterPeeringConnectionOptions": get_scalar(md, "RequesterPeeringConnectionOptions"),
            "VpcPeeringConnectionId": get_scalar(md, "VpcPeeringConnectionId"),
        }

    @staticmethod
    def parse_reject_vpc_peering_connection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcPeeringConnectionId": get_scalar(md, "VpcPeeringConnectionId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AcceptVpcPeeringConnection": vpcpeering_RequestParser.parse_accept_vpc_peering_connection_request,
            "CreateVpcPeeringConnection": vpcpeering_RequestParser.parse_create_vpc_peering_connection_request,
            "DeleteVpcPeeringConnection": vpcpeering_RequestParser.parse_delete_vpc_peering_connection_request,
            "DescribeVpcPeeringConnections": vpcpeering_RequestParser.parse_describe_vpc_peering_connections_request,
            "ModifyVpcPeeringConnectionOptions": vpcpeering_RequestParser.parse_modify_vpc_peering_connection_options_request,
            "RejectVpcPeeringConnection": vpcpeering_RequestParser.parse_reject_vpc_peering_connection_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class vpcpeering_ResponseSerializer:
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
                xml_parts.extend(vpcpeering_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(vpcpeering_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(vpcpeering_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(vpcpeering_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_accept_vpc_peering_connection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AcceptVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize vpcPeeringConnection
        _vpcPeeringConnection_key = None
        if "vpcPeeringConnection" in data:
            _vpcPeeringConnection_key = "vpcPeeringConnection"
        elif "VpcPeeringConnection" in data:
            _vpcPeeringConnection_key = "VpcPeeringConnection"
        if _vpcPeeringConnection_key:
            param_data = data[_vpcPeeringConnection_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpcPeeringConnection>')
            xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</vpcPeeringConnection>')
        xml_parts.append(f'</AcceptVpcPeeringConnectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_vpc_peering_connection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize vpcPeeringConnection
        _vpcPeeringConnection_key = None
        if "vpcPeeringConnection" in data:
            _vpcPeeringConnection_key = "vpcPeeringConnection"
        elif "VpcPeeringConnection" in data:
            _vpcPeeringConnection_key = "VpcPeeringConnection"
        if _vpcPeeringConnection_key:
            param_data = data[_vpcPeeringConnection_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<vpcPeeringConnection>')
            xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</vpcPeeringConnection>')
        xml_parts.append(f'</CreateVpcPeeringConnectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_vpc_peering_connection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteVpcPeeringConnectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_vpc_peering_connections_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeVpcPeeringConnectionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize vpcPeeringConnectionSet
        _vpcPeeringConnectionSet_key = None
        if "vpcPeeringConnectionSet" in data:
            _vpcPeeringConnectionSet_key = "vpcPeeringConnectionSet"
        elif "VpcPeeringConnectionSet" in data:
            _vpcPeeringConnectionSet_key = "VpcPeeringConnectionSet"
        elif "VpcPeeringConnections" in data:
            _vpcPeeringConnectionSet_key = "VpcPeeringConnections"
        if _vpcPeeringConnectionSet_key:
            param_data = data[_vpcPeeringConnectionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<vpcPeeringConnectionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</vpcPeeringConnectionSet>')
            else:
                xml_parts.append(f'{indent_str}<vpcPeeringConnectionSet/>')
        xml_parts.append(f'</DescribeVpcPeeringConnectionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_vpc_peering_connection_options_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyVpcPeeringConnectionOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize accepterPeeringConnectionOptions
        _accepterPeeringConnectionOptions_key = None
        if "accepterPeeringConnectionOptions" in data:
            _accepterPeeringConnectionOptions_key = "accepterPeeringConnectionOptions"
        elif "AccepterPeeringConnectionOptions" in data:
            _accepterPeeringConnectionOptions_key = "AccepterPeeringConnectionOptions"
        if _accepterPeeringConnectionOptions_key:
            param_data = data[_accepterPeeringConnectionOptions_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<accepterPeeringConnectionOptionsSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</accepterPeeringConnectionOptionsSet>')
            else:
                xml_parts.append(f'{indent_str}<accepterPeeringConnectionOptionsSet/>')
        # Serialize requesterPeeringConnectionOptions
        _requesterPeeringConnectionOptions_key = None
        if "requesterPeeringConnectionOptions" in data:
            _requesterPeeringConnectionOptions_key = "requesterPeeringConnectionOptions"
        elif "RequesterPeeringConnectionOptions" in data:
            _requesterPeeringConnectionOptions_key = "RequesterPeeringConnectionOptions"
        if _requesterPeeringConnectionOptions_key:
            param_data = data[_requesterPeeringConnectionOptions_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<requesterPeeringConnectionOptionsSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(vpcpeering_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</requesterPeeringConnectionOptionsSet>')
            else:
                xml_parts.append(f'{indent_str}<requesterPeeringConnectionOptionsSet/>')
        xml_parts.append(f'</ModifyVpcPeeringConnectionOptionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_reject_vpc_peering_connection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RejectVpcPeeringConnectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</RejectVpcPeeringConnectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AcceptVpcPeeringConnection": vpcpeering_ResponseSerializer.serialize_accept_vpc_peering_connection_response,
            "CreateVpcPeeringConnection": vpcpeering_ResponseSerializer.serialize_create_vpc_peering_connection_response,
            "DeleteVpcPeeringConnection": vpcpeering_ResponseSerializer.serialize_delete_vpc_peering_connection_response,
            "DescribeVpcPeeringConnections": vpcpeering_ResponseSerializer.serialize_describe_vpc_peering_connections_response,
            "ModifyVpcPeeringConnectionOptions": vpcpeering_ResponseSerializer.serialize_modify_vpc_peering_connection_options_response,
            "RejectVpcPeeringConnection": vpcpeering_ResponseSerializer.serialize_reject_vpc_peering_connection_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)
