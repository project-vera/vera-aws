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
class InternetGateway:
    attachment_set: List[Any] = field(default_factory=list)
    internet_gateway_id: str = ""
    owner_id: str = ""
    tag_set: List[Any] = field(default_factory=list)

    is_egress_only: bool = False
    vpc_id: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        return {
            "attachmentSet": self.attachment_set,
            "internetGatewayId": self.internet_gateway_id,
            "ownerId": self.owner_id,
            "tagSet": self.tag_set,
        }

class InternetGateway_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.internet_gateways  # alias to shared store

    # Cross-resource parent registration (do this in Create/Delete methods):
    #   Create: self.state.vpcs.get(params['vpc_id']).internet_gateway_ids.append(new_id)
    #   Delete: self.state.vpcs.get(resource.vpc_id).internet_gateway_ids.remove(resource_id)

    def _require_params(self, params: Dict[str, Any], names: List[str]):
        for name in names:
            if not params.get(name):
                return create_error_response("MissingParameter", f"Missing required parameter: {name}")
        return None

    def _get_resource_or_error(self, store: Dict[str, Any], resource_id: str, error_code: str, message: Optional[str] = None):
        resource = store.get(resource_id)
        if not resource:
            return None, create_error_response(error_code, message or f"The ID '{resource_id}' does not exist")
        return resource, None

    def _get_resources_by_ids(self, store: Dict[str, Any], resource_ids: List[str], error_code: str):
        resources = []
        for resource_id in resource_ids:
            resource = store.get(resource_id)
            if not resource:
                return None, create_error_response(error_code, f"The ID '{resource_id}' does not exist")
            resources.append(resource)
        return resources, None

    def _extract_tags(self, tag_specs: List[Dict[str, Any]], resource_type: str = "internet-gateway") -> List[Dict[str, Any]]:
        tags: List[Dict[str, Any]] = []
        for spec in tag_specs or []:
            spec_type = spec.get("ResourceType")
            if spec_type and spec_type != resource_type:
                continue
            for tag in spec.get("Tag") or spec.get("Tags") or []:
                if tag:
                    tags.append(tag)
        return tags

    def AttachInternetGateway(self, params: Dict[str, Any]):
        """Attaches an internet gateway or a virtual private gateway to a VPC, enabling connectivity 
		        between the internet and the VPC. For more information, seeInternet gatewaysin theAmazon VPC User Guide."""

        error = self._require_params(params, ["InternetGatewayId", "VpcId"])
        if error:
            return error

        internet_gateway_id = params.get("InternetGatewayId")
        resource, error = self._get_resource_or_error(
            self.resources,
            internet_gateway_id,
            "InvalidInternetGatewayID.NotFound",
            f"The ID '{internet_gateway_id}' does not exist",
        )
        if error:
            return error

        if resource.is_egress_only:
            return create_error_response(
                "InvalidInternetGatewayID.NotFound",
                f"The ID '{internet_gateway_id}' does not exist",
            )

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"VPC '{vpc_id}' does not exist.")

        if resource.vpc_id and resource.vpc_id != vpc_id:
            return create_error_response(
                "DependencyViolation",
                "InternetGateway is already attached to another VPC.",
            )
        if hasattr(vpc, "internet_gateway_ids") and vpc.internet_gateway_ids:
            if internet_gateway_id not in vpc.internet_gateway_ids:
                return create_error_response(
                    "DependencyViolation",
                    "VPC already has an internet gateway attached.",
                )

        resource.vpc_id = vpc_id
        resource.attachment_set = [{"state": "available", "vpcId": vpc_id}]

        if hasattr(vpc, "internet_gateway_ids") and internet_gateway_id not in vpc.internet_gateway_ids:
            vpc.internet_gateway_ids.append(internet_gateway_id)

        return {
            'return': True,
            }

    def CreateEgressOnlyInternetGateway(self, params: Dict[str, Any]):
        """[IPv6 only] Creates an egress-only internet gateway for your VPC. An egress-only
			internet gateway is used to enable outbound communication over IPv6 from instances in
			your VPC to the internet, and prevents hosts outside of your VPC from initiating an IPv6
			connection with your instance."""

        error = self._require_params(params, ["VpcId"])
        if error:
            return error

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"VPC '{vpc_id}' does not exist.")

        egress_only_igw_id = self._generate_id("igw")
        tag_set = self._extract_tags(params.get("TagSpecification.N", []), "egress-only-internet-gateway")
        attachment = {"state": "available", "vpcId": vpc_id}
        resource = InternetGateway(
            attachment_set=[attachment],
            internet_gateway_id=egress_only_igw_id,
            owner_id=getattr(vpc, "owner_id", ""),
            tag_set=tag_set,
            is_egress_only=True,
            vpc_id=vpc_id,
        )
        self.resources[egress_only_igw_id] = resource

        if hasattr(vpc, "internet_gateway_ids"):
            vpc.internet_gateway_ids.append(egress_only_igw_id)

        return {
            'clientToken': params.get("ClientToken"),
            'egressOnlyInternetGateway': {
                'attachmentSet': resource.attachment_set,
                'egressOnlyInternetGatewayId': egress_only_igw_id,
                'tagSet': resource.tag_set,
                },
            }

    def CreateInternetGateway(self, params: Dict[str, Any]):
        """Creates an internet gateway for use with a VPC. After creating the internet gateway,
			you attach it to a VPC usingAttachInternetGateway. For more information, seeInternet gatewaysin theAmazon VPC User Guide."""

        internet_gateway_id = self._generate_id("igw")
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))

        resource = InternetGateway(
            attachment_set=[],
            internet_gateway_id=internet_gateway_id,
            owner_id="",
            tag_set=tag_set,
        )
        self.resources[internet_gateway_id] = resource

        return {
            'internetGateway': resource.to_dict(),
            }

    def DeleteEgressOnlyInternetGateway(self, params: Dict[str, Any]):
        """Deletes an egress-only internet gateway."""

        error = self._require_params(params, ["EgressOnlyInternetGatewayId"])
        if error:
            return error

        egress_only_id = params.get("EgressOnlyInternetGatewayId")
        resource, error = self._get_resource_or_error(
            self.resources,
            egress_only_id,
            "InvalidEgressOnlyInternetGatewayId.NotFound",
            f"The ID '{egress_only_id}' does not exist",
        )
        if error:
            return error

        if not resource.is_egress_only:
            return create_error_response(
                "InvalidEgressOnlyInternetGatewayId.NotFound",
                f"The ID '{egress_only_id}' does not exist",
            )

        vpc_id = resource.vpc_id
        if vpc_id:
            vpc = self.state.vpcs.get(vpc_id)
            if vpc and hasattr(vpc, "internet_gateway_ids") and egress_only_id in vpc.internet_gateway_ids:
                vpc.internet_gateway_ids.remove(egress_only_id)

        self.resources.pop(egress_only_id, None)

        return {
            'returnCode': True,
            }

    def DeleteInternetGateway(self, params: Dict[str, Any]):
        """Deletes the specified internet gateway. You must detach the internet gateway from the
			VPC before you can delete it."""

        error = self._require_params(params, ["InternetGatewayId"])
        if error:
            return error

        internet_gateway_id = params.get("InternetGatewayId")
        resource, error = self._get_resource_or_error(
            self.resources,
            internet_gateway_id,
            "InvalidInternetGatewayID.NotFound",
            f"The ID '{internet_gateway_id}' does not exist",
        )
        if error:
            return error

        if resource.is_egress_only:
            return create_error_response(
                "InvalidInternetGatewayID.NotFound",
                f"The ID '{internet_gateway_id}' does not exist",
            )

        attached_vpc_id = resource.vpc_id
        attached = bool(attached_vpc_id)
        if not attached:
            for attachment in resource.attachment_set or []:
                if attachment.get("state") != "detached":
                    attached = True
                    attached_vpc_id = attachment.get("vpcId")
                    break
        if attached:
            return create_error_response(
                "DependencyViolation",
                "InternetGateway is still attached to a VPC.",
            )

        self.resources.pop(internet_gateway_id, None)

        if attached_vpc_id:
            vpc = self.state.vpcs.get(attached_vpc_id)
            if vpc and hasattr(vpc, "internet_gateway_ids") and internet_gateway_id in vpc.internet_gateway_ids:
                vpc.internet_gateway_ids.remove(internet_gateway_id)

        return {
            'return': True,
            }

    def DescribeEgressOnlyInternetGateways(self, params: Dict[str, Any]):
        """Describes your egress-only internet gateways. The default is to describe all your egress-only internet gateways. 
            Alternatively, you can specify specific egress-only internet gateway IDs or filter the results to
            include only the egress-only internet gateways that match specif"""

        egress_only_ids = params.get("EgressOnlyInternetGatewayId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        if egress_only_ids:
            resources = []
            for egress_only_id in egress_only_ids:
                resource = self.resources.get(egress_only_id)
                if not resource or not resource.is_egress_only:
                    return create_error_response(
                        "InvalidEgressOnlyInternetGatewayId.NotFound",
                        f"The ID '{egress_only_id}' does not exist",
                    )
                resources.append(resource)
        else:
            resources = [resource for resource in self.resources.values() if resource.is_egress_only]

        resources = apply_filters(resources, params.get("Filter.N", []))
        egress_only_gateways = [
            {
                "attachmentSet": resource.attachment_set,
                "egressOnlyInternetGatewayId": resource.internet_gateway_id,
                "tagSet": resource.tag_set,
            }
            for resource in resources[:max_results]
        ]

        return {
            'egressOnlyInternetGatewaySet': egress_only_gateways,
            'nextToken': None,
            }

    def DescribeInternetGateways(self, params: Dict[str, Any]):
        """Describes your internet gateways. The default is to describe all your internet gateways. 
            Alternatively, you can specify specific internet gateway IDs or filter the results to
            include only the internet gateways that match specific criteria."""

        internet_gateway_ids = params.get("InternetGatewayId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        if internet_gateway_ids:
            resources = []
            for internet_gateway_id in internet_gateway_ids:
                resource = self.resources.get(internet_gateway_id)
                if not resource or resource.is_egress_only:
                    return create_error_response(
                        "InvalidInternetGatewayID.NotFound",
                        f"The ID '{internet_gateway_id}' does not exist",
                    )
                resources.append(resource)
        else:
            resources = [resource for resource in self.resources.values() if not resource.is_egress_only]

        resources = apply_filters(resources, params.get("Filter.N", []))
        internet_gateways = [resource.to_dict() for resource in resources[:max_results]]

        return {
            'internetGatewaySet': internet_gateways,
            'nextToken': None,
            }

    def DetachInternetGateway(self, params: Dict[str, Any]):
        """Detaches an internet gateway from a VPC, disabling connectivity between the internet
			and the VPC. The VPC must not contain any running instances with Elastic IP addresses or
			public IPv4 addresses."""

        error = self._require_params(params, ["InternetGatewayId", "VpcId"])
        if error:
            return error

        internet_gateway_id = params.get("InternetGatewayId")
        resource, error = self._get_resource_or_error(
            self.resources,
            internet_gateway_id,
            "InvalidInternetGatewayID.NotFound",
            f"The ID '{internet_gateway_id}' does not exist",
        )
        if error:
            return error

        if resource.is_egress_only:
            return create_error_response(
                "InvalidInternetGatewayID.NotFound",
                f"The ID '{internet_gateway_id}' does not exist",
            )

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response("InvalidVpcID.NotFound", f"VPC '{vpc_id}' does not exist.")

        attached = resource.vpc_id == vpc_id
        if not attached:
            for attachment in resource.attachment_set or []:
                if attachment.get("vpcId") == vpc_id and attachment.get("state") != "detached":
                    attached = True
                    break
        if not attached:
            return create_error_response(
                "DependencyViolation",
                "InternetGateway is not attached to the specified VPC.",
            )

        resource.vpc_id = None
        resource.attachment_set = []

        if hasattr(vpc, "internet_gateway_ids") and internet_gateway_id in vpc.internet_gateway_ids:
            vpc.internet_gateway_ids.remove(internet_gateway_id)

        return {
            'return': True,
            }

    def _generate_id(self, prefix: str = 'igw') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class internetgateway_RequestParser:
    @staticmethod
    def parse_attach_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InternetGatewayId": get_scalar(md, "InternetGatewayId"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_create_egress_only_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_create_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_delete_egress_only_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EgressOnlyInternetGatewayId": get_scalar(md, "EgressOnlyInternetGatewayId"),
        }

    @staticmethod
    def parse_delete_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InternetGatewayId": get_scalar(md, "InternetGatewayId"),
        }

    @staticmethod
    def parse_describe_egress_only_internet_gateways_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EgressOnlyInternetGatewayId.N": get_indexed_list(md, "EgressOnlyInternetGatewayId"),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_internet_gateways_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "InternetGatewayId.N": get_indexed_list(md, "InternetGatewayId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_detach_internet_gateway_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InternetGatewayId": get_scalar(md, "InternetGatewayId"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AttachInternetGateway": internetgateway_RequestParser.parse_attach_internet_gateway_request,
            "CreateEgressOnlyInternetGateway": internetgateway_RequestParser.parse_create_egress_only_internet_gateway_request,
            "CreateInternetGateway": internetgateway_RequestParser.parse_create_internet_gateway_request,
            "DeleteEgressOnlyInternetGateway": internetgateway_RequestParser.parse_delete_egress_only_internet_gateway_request,
            "DeleteInternetGateway": internetgateway_RequestParser.parse_delete_internet_gateway_request,
            "DescribeEgressOnlyInternetGateways": internetgateway_RequestParser.parse_describe_egress_only_internet_gateways_request,
            "DescribeInternetGateways": internetgateway_RequestParser.parse_describe_internet_gateways_request,
            "DetachInternetGateway": internetgateway_RequestParser.parse_detach_internet_gateway_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class internetgateway_ResponseSerializer:
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
                xml_parts.extend(internetgateway_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(internetgateway_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(internetgateway_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(internetgateway_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_attach_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AttachInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</AttachInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_egress_only_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateEgressOnlyInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize egressOnlyInternetGateway
        _egressOnlyInternetGateway_key = None
        if "egressOnlyInternetGateway" in data:
            _egressOnlyInternetGateway_key = "egressOnlyInternetGateway"
        elif "EgressOnlyInternetGateway" in data:
            _egressOnlyInternetGateway_key = "EgressOnlyInternetGateway"
        if _egressOnlyInternetGateway_key:
            param_data = data[_egressOnlyInternetGateway_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<egressOnlyInternetGateway>')
            xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</egressOnlyInternetGateway>')
        xml_parts.append(f'</CreateEgressOnlyInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize internetGateway
        _internetGateway_key = None
        if "internetGateway" in data:
            _internetGateway_key = "internetGateway"
        elif "InternetGateway" in data:
            _internetGateway_key = "InternetGateway"
        if _internetGateway_key:
            param_data = data[_internetGateway_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<internetGateway>')
            xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</internetGateway>')
        xml_parts.append(f'</CreateInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_egress_only_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteEgressOnlyInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize returnCode
        _returnCode_key = None
        if "returnCode" in data:
            _returnCode_key = "returnCode"
        elif "ReturnCode" in data:
            _returnCode_key = "ReturnCode"
        if _returnCode_key:
            param_data = data[_returnCode_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<returnCode>{esc(str(param_data))}</returnCode>')
        xml_parts.append(f'</DeleteEgressOnlyInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_egress_only_internet_gateways_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeEgressOnlyInternetGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize egressOnlyInternetGatewaySet
        _egressOnlyInternetGatewaySet_key = None
        if "egressOnlyInternetGatewaySet" in data:
            _egressOnlyInternetGatewaySet_key = "egressOnlyInternetGatewaySet"
        elif "EgressOnlyInternetGatewaySet" in data:
            _egressOnlyInternetGatewaySet_key = "EgressOnlyInternetGatewaySet"
        elif "EgressOnlyInternetGateways" in data:
            _egressOnlyInternetGatewaySet_key = "EgressOnlyInternetGateways"
        if _egressOnlyInternetGatewaySet_key:
            param_data = data[_egressOnlyInternetGatewaySet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<egressOnlyInternetGatewaySet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</egressOnlyInternetGatewaySet>')
            else:
                xml_parts.append(f'{indent_str}<egressOnlyInternetGatewaySet/>')
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
        xml_parts.append(f'</DescribeEgressOnlyInternetGatewaysResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_internet_gateways_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeInternetGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize internetGatewaySet
        _internetGatewaySet_key = None
        if "internetGatewaySet" in data:
            _internetGatewaySet_key = "internetGatewaySet"
        elif "InternetGatewaySet" in data:
            _internetGatewaySet_key = "InternetGatewaySet"
        elif "InternetGateways" in data:
            _internetGatewaySet_key = "InternetGateways"
        if _internetGatewaySet_key:
            param_data = data[_internetGatewaySet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<internetGatewaySet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(internetgateway_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</internetGatewaySet>')
            else:
                xml_parts.append(f'{indent_str}<internetGatewaySet/>')
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
        xml_parts.append(f'</DescribeInternetGatewaysResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_detach_internet_gateway_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DetachInternetGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DetachInternetGatewayResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AttachInternetGateway": internetgateway_ResponseSerializer.serialize_attach_internet_gateway_response,
            "CreateEgressOnlyInternetGateway": internetgateway_ResponseSerializer.serialize_create_egress_only_internet_gateway_response,
            "CreateInternetGateway": internetgateway_ResponseSerializer.serialize_create_internet_gateway_response,
            "DeleteEgressOnlyInternetGateway": internetgateway_ResponseSerializer.serialize_delete_egress_only_internet_gateway_response,
            "DeleteInternetGateway": internetgateway_ResponseSerializer.serialize_delete_internet_gateway_response,
            "DescribeEgressOnlyInternetGateways": internetgateway_ResponseSerializer.serialize_describe_egress_only_internet_gateways_response,
            "DescribeInternetGateways": internetgateway_ResponseSerializer.serialize_describe_internet_gateways_response,
            "DetachInternetGateway": internetgateway_ResponseSerializer.serialize_detach_internet_gateway_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)
