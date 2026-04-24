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
class DhcpOptions:
    dhcp_configuration_set: List[Any] = field(default_factory=list)
    dhcp_options_id: str = ""
    owner_id: str = ""
    tag_set: List[Any] = field(default_factory=list)

    # Internal dependency tracking — not in API response
    vpc_ids: List[str] = field(default_factory=list)  # tracks Vpc children


    def to_dict(self) -> Dict[str, Any]:
        return {
            "dhcpConfigurationSet": self.dhcp_configuration_set,
            "dhcpOptionsId": self.dhcp_options_id,
            "ownerId": self.owner_id,
            "tagSet": self.tag_set,
        }

class DhcpOptions_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.dhcp_options  # alias to shared store


    def _get_dhcp_options(self, dhcp_options_id: str) -> Optional[DhcpOptions]:
        return self.resources.get(dhcp_options_id)

    def AssociateDhcpOptions(self, params: Dict[str, Any]):
        """Associates a set of DHCP options (that you've previously created) with the specified VPC, or associates no DHCP options with the VPC. After you associate the options with the VPC, any existing instances and all new instances that you launch in that VPC use the options. You don't need to restart or r"""

        dhcp_options_id = params.get("DhcpOptionsId")
        vpc_id = params.get("VpcId")

        if not dhcp_options_id:
            return create_error_response(
                "MissingParameter",
                "Missing required parameter: DhcpOptionsId",
            )
        if not vpc_id:
            return create_error_response(
                "MissingParameter",
                "Missing required parameter: VpcId",
            )

        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' does not exist.",
            )

        for options in self.resources.values():
            if vpc_id in options.vpc_ids:
                options.vpc_ids.remove(vpc_id)

        if dhcp_options_id != "default":
            dhcp_options = self.resources.get(dhcp_options_id)
            if not dhcp_options:
                return create_error_response(
                    "InvalidDhcpOptionsID.NotFound",
                    f"The ID '{dhcp_options_id}' does not exist",
                )
            if vpc_id not in dhcp_options.vpc_ids:
                dhcp_options.vpc_ids.append(vpc_id)

        if hasattr(vpc, "dhcp_options_id"):
            vpc.dhcp_options_id = dhcp_options_id

        return {
            'return': True,
            }

    def CreateDhcpOptions(self, params: Dict[str, Any]):
        """Creates a custom set of DHCP options. After you create a DHCP option set, you associate
	       it with a VPC. After you associate a DHCP option set with a VPC, all existing and newly 
	       launched instances in the VPC use this set of DHCP options. The following are the individual DHCP options y"""

        dhcp_configurations = params.get("DhcpConfiguration.N", []) or []
        if not dhcp_configurations:
            return create_error_response(
                "MissingParameter",
                "Missing required parameter: DhcpConfiguration.N",
            )

        dhcp_options_id = self._generate_id("dhcp")
        tag_set: List[Dict[str, Any]] = []
        for spec in params.get("TagSpecification.N", []) or []:
            tag_set.extend(spec.get("Tags", []) or [])

        resource = DhcpOptions(
            dhcp_configuration_set=dhcp_configurations,
            dhcp_options_id=dhcp_options_id,
            owner_id="",
            tag_set=tag_set,
        )
        self.resources[dhcp_options_id] = resource

        return {
            'dhcpOptions': [resource.to_dict()],
            }

    def DeleteDhcpOptions(self, params: Dict[str, Any]):
        """Deletes the specified set of DHCP options. You must disassociate the set of DHCP options before you can delete it. You can disassociate the set of DHCP options by associating either a new set of options or the default set of options with the VPC."""

        dhcp_options_id = params.get("DhcpOptionsId")
        if not dhcp_options_id:
            return create_error_response(
                "MissingParameter",
                "Missing required parameter: DhcpOptionsId",
            )

        dhcp_options = self.resources.get(dhcp_options_id)
        if not dhcp_options:
            return create_error_response(
                "InvalidDhcpOptionsID.NotFound",
                f"The ID '{dhcp_options_id}' does not exist",
            )

        if getattr(dhcp_options, "vpc_ids", []):
            return create_error_response(
                "DependencyViolation",
                "DhcpOptions has dependent Vpc(s) and cannot be deleted.",
            )

        del self.resources[dhcp_options_id]

        return {
            'return': True,
            }

    def DescribeDhcpOptions(self, params: Dict[str, Any]):
        """Describes your DHCP option sets. The default is to describe all your DHCP option sets. 
		        Alternatively, you can specify specific DHCP option set IDs or filter the results to
		        include only the DHCP option sets that match specific criteria. For more information, seeDHCP option setsin"""

        dhcp_options_ids = params.get("DhcpOptionsId.N", []) or []
        max_results = int(params.get("MaxResults") or 100)

        if dhcp_options_ids:
            resources: List[DhcpOptions] = []
            for dhcp_options_id in dhcp_options_ids:
                dhcp_options = self.resources.get(dhcp_options_id)
                if not dhcp_options:
                    return create_error_response(
                        "InvalidDhcpOptionsID.NotFound",
                        f"The ID '{dhcp_options_id}' does not exist",
                    )
                resources.append(dhcp_options)
        else:
            resources = list(self.resources.values())

        resources = apply_filters(resources, params.get("Filter.N", []))
        dhcp_options_set = [resource.to_dict() for resource in resources[:max_results]]

        return {
            'dhcpOptionsSet': dhcp_options_set,
            'nextToken': None,
            }

    def _generate_id(self, prefix: str = 'dhcp') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

def parse_dhcp_configurations(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse CreateDhcpOptions DhcpConfiguration.N nested query parameters.

    AWS CLI sends DHCP configurations as EC2 Query-style flattened nested fields,
    for example:
        DhcpConfiguration.1.Key=domain-name
        DhcpConfiguration.1.Value.1=example.com

    get_indexed_list(params, "DhcpConfiguration") only supports scalar indexed
    fields such as DhcpConfiguration.1, so this helper reconstructs the nested
    object list without changing the shared scalar-list parser used by other APIs.
    """
    configs: List[Dict[str, Any]] = []
    index = 1

    while True:
        prefix = f"DhcpConfiguration.{index}"
        key_name = f"{prefix}.Key"

        if key_name not in params:
            break

        key = get_scalar(params, key_name)
        values: List[Dict[str, str]] = []

        value_index = 1
        while True:
            value_name = f"{prefix}.Value.{value_index}"
            if value_name not in params:
                break

            value = get_scalar(params, value_name)
            if value is not None:
                values.append({"value": value})

            value_index += 1

        configs.append({
            "key": key,
            "valueSet": values,
        })

        index += 1

    return configs


class dhcpoptions_RequestParser:
    @staticmethod
    def parse_associate_dhcp_options_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DhcpOptionsId": get_scalar(md, "DhcpOptionsId"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_create_dhcp_options_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DhcpConfiguration.N": parse_dhcp_configurations(md),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_delete_dhcp_options_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DhcpOptionsId": get_scalar(md, "DhcpOptionsId"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_describe_dhcp_options_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DhcpOptionsId.N": get_indexed_list(md, "DhcpOptionsId"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AssociateDhcpOptions": dhcpoptions_RequestParser.parse_associate_dhcp_options_request,
            "CreateDhcpOptions": dhcpoptions_RequestParser.parse_create_dhcp_options_request,
            "DeleteDhcpOptions": dhcpoptions_RequestParser.parse_delete_dhcp_options_request,
            "DescribeDhcpOptions": dhcpoptions_RequestParser.parse_describe_dhcp_options_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class dhcpoptions_ResponseSerializer:
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
                xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_associate_dhcp_options_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AssociateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</AssociateDhcpOptionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_dhcp_options_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(str(request_id))}</requestId>')

        # CreateDhcpOptions is a singular create response.
        # AWS CLI / botocore expects <dhcpOptions>, not <dhcpOptionsSet>.
        param_data = data.get("dhcpOptions") or data.get("DhcpOptions") or []

        if isinstance(param_data, list):
            dhcp_options = param_data[0] if param_data else None
        else:
            dhcp_options = param_data

        if dhcp_options:
            xml_parts.append(f'    <dhcpOptions>')
            xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_nested_fields(dhcp_options, 2))
            xml_parts.append(f'    </dhcpOptions>')
        else:
            xml_parts.append(f'    <dhcpOptions/>')

        xml_parts.append(f'</CreateDhcpOptionsResponse>')
        return '\n'.join(xml_parts)

    @staticmethod
    def serialize_delete_dhcp_options_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteDhcpOptionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_dhcp_options_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize dhcpOptionsSet
        _dhcpOptionsSet_key = None
        if "dhcpOptionsSet" in data:
            _dhcpOptionsSet_key = "dhcpOptionsSet"
        elif "DhcpOptionsSet" in data:
            _dhcpOptionsSet_key = "DhcpOptionsSet"
        elif "DhcpOptionss" in data:
            _dhcpOptionsSet_key = "DhcpOptionss"
        if _dhcpOptionsSet_key:
            param_data = data[_dhcpOptionsSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<dhcpOptionsSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(dhcpoptions_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</dhcpOptionsSet>')
            else:
                xml_parts.append(f'{indent_str}<dhcpOptionsSet/>')
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
        xml_parts.append(f'</DescribeDhcpOptionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AssociateDhcpOptions": dhcpoptions_ResponseSerializer.serialize_associate_dhcp_options_response,
            "CreateDhcpOptions": dhcpoptions_ResponseSerializer.serialize_create_dhcp_options_response,
            "DeleteDhcpOptions": dhcpoptions_ResponseSerializer.serialize_delete_dhcp_options_response,
            "DescribeDhcpOptions": dhcpoptions_ResponseSerializer.serialize_describe_dhcp_options_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)

