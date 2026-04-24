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
class SecurityGroup:
    group_description: str = ""
    group_id: str = ""
    group_name: str = ""
    ip_permissions: List[Any] = field(default_factory=list)
    ip_permissions_egress: List[Any] = field(default_factory=list)
    owner_id: str = ""
    security_group_arn: str = ""
    tag_set: List[Any] = field(default_factory=list)
    vpc_id: str = ""

    # Internal dependency tracking — not in API response
    authorization_rule_ids: List[str] = field(default_factory=list)  # tracks AuthorizationRule children

    associated_vpc_ids: List[str] = field(default_factory=list)
    vpc_association_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    security_group_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)


    def to_dict(self) -> Dict[str, Any]:
        return {
            "groupDescription": self.group_description,
            "groupId": self.group_id,
            "groupName": self.group_name,
            "ipPermissions": self.ip_permissions,
            "ipPermissionsEgress": self.ip_permissions_egress,
            "ownerId": self.owner_id,
            "securityGroupArn": self.security_group_arn,
            "tagSet": self.tag_set,
            "vpcId": self.vpc_id,
        }

class SecurityGroup_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.security_groups  # alias to shared store

    # Cross-resource parent registration (do this in Create/Delete methods):
    #   Create: self.state.vpcs.get(params['vpc_id']).security_group_ids.append(new_id)
    #   Delete: self.state.vpcs.get(resource.vpc_id).security_group_ids.remove(resource_id)

    def _require_params(self, params: Dict[str, Any], names: List[str]) -> Optional[Dict[str, Any]]:
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

    def _get_security_group_by_id_or_name(self, group_id: Optional[str], group_name: Optional[str]):
        if group_id:
            group = self.resources.get(group_id)
            if not group:
                return None, create_error_response(
                    "InvalidGroup.NotFound",
                    f"Security group '{group_id}' does not exist.",
                )
            return group, None
        if group_name:
            for group in self.resources.values():
                if group.group_name == group_name:
                    return group, None
            return None, create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_name}' does not exist.",
            )
        return None, create_error_response("MissingParameter", "GroupId is required.")

    # def _normalize_ip_permissions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    #     ip_permissions = params.get("IpPermissions.N", []) or []
    #     if not ip_permissions and params.get("IpProtocol"):
    #         ip_permissions = [
    #             {
    #                 "IpProtocol": params.get("IpProtocol", "-1"),
    #                 "FromPort": int(params.get("FromPort") or 0),
    #                 "ToPort": int(params.get("ToPort") or 0),
    #                 "IpRanges": [
    #                     {"CidrIp": params.get("CidrIp", "0.0.0.0/0")}
    #                 ],
    #             }
    #         ]
    #     return ip_permissions

    def _to_int_or_none(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except Exception:
            return None

    def _permission_template(self) -> Dict[str, Any]:
        return {
            "IpProtocol": None,
            "FromPort": None,
            "ToPort": None,
            "IpRanges": [],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
            "UserIdGroupPairs": [],
        }

    def _normalize_permission_shape(self, perm: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure every permission has the canonical fields expected by downstream code.
        """
        normalized = self._permission_template()
        normalized["IpProtocol"] = perm.get("IpProtocol", perm.get("ipProtocol"))
        normalized["FromPort"] = self._to_int_or_none(perm.get("FromPort", perm.get("fromPort")))
        normalized["ToPort"] = self._to_int_or_none(perm.get("ToPort", perm.get("toPort")))

        ip_ranges = perm.get("IpRanges", []) or []
        ipv6_ranges = perm.get("Ipv6Ranges", []) or []
        prefix_lists = perm.get("PrefixListIds", []) or []
        user_groups = perm.get("UserIdGroupPairs", []) or []

        normalized["IpRanges"] = ip_ranges if isinstance(ip_ranges, list) else [ip_ranges]
        normalized["Ipv6Ranges"] = ipv6_ranges if isinstance(ipv6_ranges, list) else [ipv6_ranges]
        normalized["PrefixListIds"] = prefix_lists if isinstance(prefix_lists, list) else [prefix_lists]
        normalized["UserIdGroupPairs"] = user_groups if isinstance(user_groups, list) else [user_groups]

        if perm.get("Description") is not None:
            normalized["Description"] = perm.get("Description")

        return normalized

    def _build_permission_from_simple_fields(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback for simple-form inputs such as:
          --protocol tcp --port 22 --cidr 0.0.0.0/0

        Depending on how the request reached the service, these may appear as top-level
        IpProtocol / FromPort / ToPort / CidrIp fields.
        """
        ip_protocol = params.get("IpProtocol")
        from_port = params.get("FromPort")
        to_port = params.get("ToPort")
        cidr_ip = params.get("CidrIp")
        cidr_ipv6 = params.get("CidrIpv6")

        if ip_protocol is None and cidr_ip is None and cidr_ipv6 is None:
            return []

        perm = self._permission_template()
        perm["IpProtocol"] = ip_protocol if ip_protocol is not None else "-1"
        perm["FromPort"] = self._to_int_or_none(from_port)
        perm["ToPort"] = self._to_int_or_none(to_port)

        if cidr_ip is not None:
            perm["IpRanges"].append({"CidrIp": cidr_ip})
        if cidr_ipv6 is not None:
            perm["Ipv6Ranges"].append({"CidrIpv6": cidr_ipv6})

        if params.get("Description") is not None:
            perm["Description"] = params.get("Description")

        return [perm]

    def _parse_ip_permissions_raw(self, raw_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse flattened AWS Query parameters such as:
          IpPermissions.1.IpProtocol=tcp
          IpPermissions.1.FromPort=22
          IpPermissions.1.ToPort=22
          IpPermissions.1.IpRanges.1.CidrIp=0.0.0.0/0

        This is the critical fallback when get_indexed_list(md, "IpPermissions")
        returns [] even though the CLI sent valid flattened parameters.
        """
        if not raw_params:
            return []

        perms: Dict[int, Dict[str, Any]] = {}
        ip_ranges_map: Dict[int, Dict[int, Dict[str, Any]]] = {}
        ipv6_ranges_map: Dict[int, Dict[int, Dict[str, Any]]] = {}
        prefix_lists_map: Dict[int, Dict[int, Dict[str, Any]]] = {}
        user_groups_map: Dict[int, Dict[int, Dict[str, Any]]] = {}

        for raw_key, raw_value in raw_params.items():
            if not isinstance(raw_key, str):
                continue
            if not raw_key.startswith("IpPermissions."):
                continue

            m = re.match(r"^IpPermissions\.(\d+)\.(.+)$", raw_key)
            if not m:
                continue

            perm_idx = int(m.group(1))
            suffix = m.group(2)

            perm = perms.setdefault(perm_idx, self._permission_template())

            if suffix == "IpProtocol":
                perm["IpProtocol"] = raw_value
                continue
            if suffix == "FromPort":
                perm["FromPort"] = self._to_int_or_none(raw_value)
                continue
            if suffix == "ToPort":
                perm["ToPort"] = self._to_int_or_none(raw_value)
                continue
            if suffix == "Description":
                perm["Description"] = raw_value
                continue

            m_v4 = re.match(r"^IpRanges\.(\d+)\.CidrIp$", suffix)
            if m_v4:
                item_idx = int(m_v4.group(1))
                ip_ranges_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["CidrIp"] = raw_value
                continue

            m_v4_desc = re.match(r"^IpRanges\.(\d+)\.Description$", suffix)
            if m_v4_desc:
                item_idx = int(m_v4_desc.group(1))
                ip_ranges_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["Description"] = raw_value
                continue

            m_v6 = re.match(r"^Ipv6Ranges\.(\d+)\.CidrIpv6$", suffix)
            if m_v6:
                item_idx = int(m_v6.group(1))
                ipv6_ranges_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["CidrIpv6"] = raw_value
                continue

            m_v6_desc = re.match(r"^Ipv6Ranges\.(\d+)\.Description$", suffix)
            if m_v6_desc:
                item_idx = int(m_v6_desc.group(1))
                ipv6_ranges_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["Description"] = raw_value
                continue

            m_pl = re.match(r"^PrefixListIds\.(\d+)\.PrefixListId$", suffix)
            if m_pl:
                item_idx = int(m_pl.group(1))
                prefix_lists_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["PrefixListId"] = raw_value
                continue

            m_pl_desc = re.match(r"^PrefixListIds\.(\d+)\.Description$", suffix)
            if m_pl_desc:
                item_idx = int(m_pl_desc.group(1))
                prefix_lists_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["Description"] = raw_value
                continue

            m_ug_gid = re.match(r"^UserIdGroupPairs\.(\d+)\.GroupId$", suffix)
            if m_ug_gid:
                item_idx = int(m_ug_gid.group(1))
                user_groups_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["GroupId"] = raw_value
                continue

            m_ug_uid = re.match(r"^UserIdGroupPairs\.(\d+)\.UserId$", suffix)
            if m_ug_uid:
                item_idx = int(m_ug_uid.group(1))
                user_groups_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["UserId"] = raw_value
                continue

            m_ug_vpc = re.match(r"^UserIdGroupPairs\.(\d+)\.VpcId$", suffix)
            if m_ug_vpc:
                item_idx = int(m_ug_vpc.group(1))
                user_groups_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["VpcId"] = raw_value
                continue

            m_ug_desc = re.match(r"^UserIdGroupPairs\.(\d+)\.Description$", suffix)
            if m_ug_desc:
                item_idx = int(m_ug_desc.group(1))
                user_groups_map.setdefault(perm_idx, {}).setdefault(item_idx, {})["Description"] = raw_value
                continue

        if not perms:
            return []

        for perm_idx, perm in perms.items():
            if perm_idx in ip_ranges_map:
                perm["IpRanges"] = [ip_ranges_map[perm_idx][i] for i in sorted(ip_ranges_map[perm_idx].keys())]
            if perm_idx in ipv6_ranges_map:
                perm["Ipv6Ranges"] = [ipv6_ranges_map[perm_idx][i] for i in sorted(ipv6_ranges_map[perm_idx].keys())]
            if perm_idx in prefix_lists_map:
                perm["PrefixListIds"] = [prefix_lists_map[perm_idx][i] for i in sorted(prefix_lists_map[perm_idx].keys())]
            if perm_idx in user_groups_map:
                perm["UserIdGroupPairs"] = [user_groups_map[perm_idx][i] for i in sorted(user_groups_map[perm_idx].keys())]

        ordered = [self._normalize_permission_shape(perms[i]) for i in sorted(perms.keys())]
        return ordered

    def _normalize_ip_permissions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Priority:
          1. already parsed IpPermissions.N list
          2. raw flattened IpPermissions.* query parameters
          3. simple top-level IpProtocol / FromPort / ToPort / CidrIp fallback
        """
        existing = params.get("IpPermissions.N", []) or []
        if existing:
            return [self._normalize_permission_shape(p) for p in existing]

        raw_params = params.get("IpPermissionsRaw", {}) or {}
        parsed_raw = self._parse_ip_permissions_raw(raw_params)
        if parsed_raw:
            return parsed_raw

        simple = self._build_permission_from_simple_fields(params)
        if simple:
            return [self._normalize_permission_shape(p) for p in simple]

        return []

    def _extract_tags(self, tag_specs: List[Dict[str, Any]], resource_type: str = "security-group") -> List[Dict[str, Any]]:
        tags: List[Dict[str, Any]] = []
        for spec in tag_specs or []:
            spec_type = spec.get("ResourceType")
            if spec_type and spec_type != resource_type:
                continue
            for tag in spec.get("Tags", []) or []:
                key = tag.get("Key")
                if key is None:
                    continue
                tags.append({"Key": key, "Value": tag.get("Value", "")})
        return tags

    def _register_vpc_association(self, group: SecurityGroup, vpc_id: str, state: str = "associated", reason: str = ""):
        if vpc_id not in group.associated_vpc_ids:
            group.associated_vpc_ids.append(vpc_id)
        group.vpc_association_states[vpc_id] = {
            "state": state,
            "stateReason": reason,
        }

    def _deregister_vpc_association(self, group: SecurityGroup, vpc_id: str):
        if vpc_id in group.associated_vpc_ids:
            group.associated_vpc_ids.remove(vpc_id)
        if vpc_id in group.vpc_association_states:
            group.vpc_association_states.pop(vpc_id, None)

    def _generate_rule_id(self) -> str:
        return self._generate_id("sgr")

    def _list_rules(self, group: SecurityGroup) -> List[Dict[str, Any]]:
        return list(group.security_group_rules.values())

    def _permission_to_describe_sg_shape(self, perm: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ipProtocol": perm.get("IpProtocol"),
            "fromPort": perm.get("FromPort"),
            "toPort": perm.get("ToPort"),
            "groups": [
                {
                    "groupId": pair.get("GroupId"),
                    "userId": pair.get("UserId"),
                    "vpcId": pair.get("VpcId"),
                    "description": pair.get("Description"),
                }
                for pair in (perm.get("UserIdGroupPairs", []) or [])
            ],
            "ipRanges": [
                {
                    "cidrIp": r.get("CidrIp"),
                    "description": r.get("Description"),
                }
                for r in (perm.get("IpRanges", []) or [])
            ],
            "ipv6Ranges": [
                {
                    "cidrIpv6": r.get("CidrIpv6"),
                    "description": r.get("Description"),
                }
                for r in (perm.get("Ipv6Ranges", []) or [])
            ],
            "prefixListIds": [
                {
                    "prefixListId": p.get("PrefixListId"),
                    "description": p.get("Description"),
                }
                for p in (perm.get("PrefixListIds", []) or [])
            ],
        }

    def _security_group_to_describe_shape(self, group: SecurityGroup) -> Dict[str, Any]:
        return {
            "groupDescription": group.group_description,
            "groupId": group.group_id,
            "groupName": group.group_name,
            "ipPermissions": [self._permission_to_describe_sg_shape(p) for p in (group.ip_permissions or [])],
            "ipPermissionsEgress": [self._permission_to_describe_sg_shape(p) for p in (group.ip_permissions_egress or [])],
            "ownerId": group.owner_id,
            "securityGroupArn": group.security_group_arn,
            "tagSet": group.tag_set,
            "vpcId": group.vpc_id,
        }

    # - State management: _update_state(resource, new_state: str)
    # - Complex operations: _process_associations(params: Dict) -> Dict
    # Add any helper functions needed by the API methods below.
    # These helpers can be used by multiple API methods.

    def AuthorizeSecurityGroupEgress(self, params: Dict[str, Any]):
        """Adds the specified outbound (egress) rules to a security group. An outbound rule permits instances to send traffic to the specified IPv4 or IPv6 
       address ranges, the IP address ranges specified by a prefix list, or the instances 
       that are associated with a source security group. For mo"""

        error = self._require_params(params, ["GroupId"])
        if error:
            return error

        group_id = params.get("GroupId")
        group = self.resources.get(group_id)
        if not group:
            return create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_id}' does not exist.",
            )

        ip_permissions = self._normalize_ip_permissions(params)
        print("[sg-debug] normalized ip_permissions =", ip_permissions)
        if not ip_permissions:
            return create_error_response("MissingParameter", "Missing required parameter: IpPermissions")

        tags = self._extract_tags(params.get("TagSpecification.N", []), "security-group-rule")
        created_rules: List[Dict[str, Any]] = []

        for perm in ip_permissions:
            group.ip_permissions_egress.append(perm)
            ip_protocol = perm.get("IpProtocol")
            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort")
            ip_ranges = perm.get("IpRanges", []) or []
            ipv6_ranges = perm.get("Ipv6Ranges", []) or []
            prefix_lists = perm.get("PrefixListIds", []) or []
            user_groups = perm.get("UserIdGroupPairs", []) or []

            if not (ip_ranges or ipv6_ranges or prefix_lists or user_groups):
                ip_ranges = [{}]

            for ip_range in ip_ranges:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": ip_range.get("CidrIp"),
                    "cidrIpv6": None,
                    "description": ip_range.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": True,
                    "prefixListId": None,
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for ip_range in ipv6_ranges:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": ip_range.get("CidrIpv6"),
                    "description": ip_range.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": True,
                    "prefixListId": None,
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for prefix in prefix_lists:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": None,
                    "description": prefix.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": True,
                    "prefixListId": prefix.get("PrefixListId"),
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for pair in user_groups:
                ref_group_id = pair.get("GroupId")
                if ref_group_id and ref_group_id not in self.resources:
                    return create_error_response(
                        "InvalidGroup.NotFound",
                        f"Security group '{ref_group_id}' does not exist.",
                    )
                rule_id = self._generate_rule_id()
                referenced_group_info = {
                    "groupId": ref_group_id,
                    "groupOwnerId": pair.get("UserId"),
                    "vpcId": pair.get("VpcId"),
                }
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": None,
                    "description": pair.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": True,
                    "prefixListId": None,
                    "referencedGroupInfo": referenced_group_info,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

        return {
            'return': True,
            'securityGroupRuleSet': created_rules,
            }

    def AuthorizeSecurityGroupIngress(self, params: Dict[str, Any]):
        """Adds the specified inbound (ingress) rules to a security group. An inbound rule permits instances to receive traffic from the specified IPv4 or IPv6 
       address range, the IP address ranges that are specified by a prefix list, or the instances 
       that are associated with a destination secur"""

        group_id = params.get("GroupId")
        group_name = params.get("GroupName")
        group, error = self._get_security_group_by_id_or_name(group_id, group_name)
        if error:
            return error

        ip_permissions = self._normalize_ip_permissions(params)
        print("[sg-debug] normalized ip_permissions =", ip_permissions)
        if not ip_permissions:
            return create_error_response("MissingParameter", "Missing required parameter: IpPermissions")

        tags = self._extract_tags(params.get("TagSpecification.N", []), "security-group-rule")
        created_rules: List[Dict[str, Any]] = []

        for perm in ip_permissions:
            group.ip_permissions.append(perm)
            ip_protocol = perm.get("IpProtocol")
            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort")
            ip_ranges = perm.get("IpRanges", []) or []
            ipv6_ranges = perm.get("Ipv6Ranges", []) or []
            prefix_lists = perm.get("PrefixListIds", []) or []
            user_groups = perm.get("UserIdGroupPairs", []) or []

            if not (ip_ranges or ipv6_ranges or prefix_lists or user_groups):
                ip_ranges = [{}]

            for ip_range in ip_ranges:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": ip_range.get("CidrIp"),
                    "cidrIpv6": None,
                    "description": ip_range.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group.group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": False,
                    "prefixListId": None,
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for ip_range in ipv6_ranges:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": ip_range.get("CidrIpv6"),
                    "description": ip_range.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group.group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": False,
                    "prefixListId": None,
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for prefix in prefix_lists:
                rule_id = self._generate_rule_id()
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": None,
                    "description": prefix.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group.group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": False,
                    "prefixListId": prefix.get("PrefixListId"),
                    "referencedGroupInfo": None,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

            for pair in user_groups:
                ref_group_id = pair.get("GroupId")
                if ref_group_id and ref_group_id not in self.resources:
                    return create_error_response(
                        "InvalidGroup.NotFound",
                        f"Security group '{ref_group_id}' does not exist.",
                    )
                rule_id = self._generate_rule_id()
                referenced_group_info = {
                    "groupId": ref_group_id,
                    "groupOwnerId": pair.get("UserId"),
                    "vpcId": pair.get("VpcId"),
                }
                rule = {
                    "cidrIpv4": None,
                    "cidrIpv6": None,
                    "description": pair.get("Description") or perm.get("Description"),
                    "fromPort": from_port,
                    "groupId": group.group_id,
                    "groupOwnerId": group.owner_id,
                    "ipProtocol": ip_protocol,
                    "isEgress": False,
                    "prefixListId": None,
                    "referencedGroupInfo": referenced_group_info,
                    "securityGroupRuleArn": f"arn:aws:ec2:::security-group-rule/{rule_id}",
                    "securityGroupRuleId": rule_id,
                    "tagSet": tags,
                    "toPort": to_port,
                }
                group.security_group_rules[rule_id] = rule
                created_rules.append(rule)

        return {
            'return': True,
            'securityGroupRuleSet': created_rules,
            }

    def CreateSecurityGroup(self, params: Dict[str, Any]):
        """Creates a security group. A security group acts as a virtual firewall for your instance to control inbound and outbound traffic.
         For more information, seeAmazon EC2 security groupsin 
				theAmazon EC2 User GuideandSecurity groups for your VPCin theAmazon VPC User Guide. When you create a s"""

        error = self._require_params(params, ["GroupDescription", "GroupName"])
        if error:
            return error

        vpc_id = params.get("VpcId")
        vpc = None
        if vpc_id:
            vpc = self.state.vpcs.get(vpc_id)
            if not vpc:
                return create_error_response(
                    "InvalidVpcID.NotFound",
                    f"VPC '{vpc_id}' does not exist.",
                )

        group_id = self._generate_id("sg")
        tags = self._extract_tags(params.get("TagSpecification.N", []))
        security_group_arn = f"arn:aws:ec2:::security-group/{group_id}"
        owner_id = getattr(vpc, "owner_id", "") if vpc else ""

        resource = SecurityGroup(
            group_description=params.get("GroupDescription") or "",
            group_id=group_id,
            group_name=params.get("GroupName") or "",
            owner_id=owner_id,
            security_group_arn=security_group_arn,
            tag_set=tags,
            vpc_id=vpc_id or "",
        )

        self.resources[group_id] = resource

        if vpc_id:
            parent = self.state.vpcs.get(vpc_id)
            if parent and hasattr(parent, "security_group_ids"):
                parent.security_group_ids.append(group_id)

        return {
            'groupId': group_id,
            'securityGroupArn': security_group_arn,
            'tagSet': tags,
            }

    def DeleteSecurityGroup(self, params: Dict[str, Any]):
        """Deletes a security group. If you attempt to delete a security group that is associated with an instance or network interface, is
			  referenced by another security group in the same VPC, or has a VPC association, the operation fails withDependencyViolation."""

        group_id = params.get("GroupId")
        group_name = params.get("GroupName")
        group, error = self._get_security_group_by_id_or_name(group_id, group_name)
        if error:
            return error

        if getattr(group, "authorization_rule_ids", []):
            return create_error_response(
                "DependencyViolation",
                "SecurityGroup has dependent AuthorizationRule(s) and cannot be deleted.",
            )

        # Backward-compat cleanup:
        # older objects may have had the primary VPC incorrectly stored as an association.
        if group.vpc_id and group.associated_vpc_ids == [group.vpc_id]:
            self._deregister_vpc_association(group, group.vpc_id)

        if group.associated_vpc_ids:
            return create_error_response(
                "DependencyViolation",
                "SecurityGroup has VPC associations and cannot be deleted.",
            )

        for other in self.resources.values():
            if other.group_id == group.group_id:
                continue
            for rule in other.security_group_rules.values():
                ref_info = rule.get("referencedGroupInfo") or {}
                if ref_info.get("groupId") == group.group_id:
                    return create_error_response(
                        "DependencyViolation",
                        "SecurityGroup is referenced by another security group.",
                    )

        parent = self.state.vpcs.get(group.vpc_id)
        if parent and hasattr(parent, "security_group_ids") and group.group_id in parent.security_group_ids:
            parent.security_group_ids.remove(group.group_id)

        for vpc_id in list(group.associated_vpc_ids):
            vpc = self.state.vpcs.get(vpc_id)
            if vpc and hasattr(vpc, "security_group_ids") and group.group_id in vpc.security_group_ids:
                vpc.security_group_ids.remove(group.group_id)

        self.resources.pop(group.group_id, None)

        return {
            'groupId': group.group_id,
            'return': True,
            }

    def DescribeSecurityGroupRules(self, params: Dict[str, Any]):
        """Describes one or more of your security group rules."""

        rule_ids = params.get("SecurityGroupRuleId.N", []) or []
        all_rules: List[Dict[str, Any]] = []
        rules_by_id: Dict[str, Dict[str, Any]] = {}
        for group in self.resources.values():
            for rule_id, rule in group.security_group_rules.items():
                rules_by_id[rule_id] = rule
                all_rules.append(rule)

        if rule_ids:
            rules: List[Dict[str, Any]] = []
            for rule_id in rule_ids:
                rule = rules_by_id.get(rule_id)
                if not rule:
                    return create_error_response(
                        "InvalidSecurityGroupRuleId.NotFound",
                        f"The ID '{rule_id}' does not exist",
                    )
                rules.append(rule)
        else:
            rules = apply_filters(all_rules, params.get("Filter.N", []))

        max_results = int(params.get("MaxResults") or 100)
        rules = rules[:max_results] if max_results else rules

        return {
            'nextToken': None,
            'securityGroupRuleSet': rules,
            }

    def DescribeSecurityGroups(self, params: Dict[str, Any]):
        """Describes the specified security groups or all of your security groups."""

        group_ids = params.get("GroupId.N", []) or []
        group_names = params.get("GroupName.N", []) or []

        if group_ids:
            resources, error = self._get_resources_by_ids(
                self.resources,
                group_ids,
                "InvalidGroup.NotFound",
            )
            if error:
                return error
        elif group_names:
            resources = []
            for name in group_names:
                match = next(
                    (group for group in self.resources.values() if group.group_name == name),
                    None,
                )
                if not match:
                    return create_error_response(
                        "InvalidGroup.NotFound",
                        f"The ID '{name}' does not exist",
                    )
                resources.append(match)
        else:
            resources = list(self.resources.values())

        resources = apply_filters(resources, params.get("Filter.N", []))
        max_results = int(params.get("MaxResults") or 100)
        resources = resources[:max_results] if max_results else resources

        return {
            'nextToken': None,
            'securityGroupInfo': [self._security_group_to_describe_shape(resource) for resource in resources],
        }

    def ModifySecurityGroupRules(self, params: Dict[str, Any]):
        """Modifies the rules of a security group."""

        error = self._require_params(params, ["GroupId", "SecurityGroupRule.N"])
        if error:
            return error

        group_id = params.get("GroupId")
        group = self.resources.get(group_id)
        if not group:
            return create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_id}' does not exist.",
            )

        rule_updates = params.get("SecurityGroupRule.N", []) or []
        if not rule_updates:
            return create_error_response("MissingParameter", "Missing required parameter: SecurityGroupRule.N")

        for update in rule_updates:
            rule_id = update.get("SecurityGroupRuleId")
            rule_data = update.get("SecurityGroupRule") or {}
            if not rule_id:
                return create_error_response(
                    "MissingParameter",
                    "Missing required parameter: SecurityGroupRuleId",
                )
            rule = group.security_group_rules.get(rule_id)
            if not rule:
                return create_error_response(
                    "InvalidSecurityGroupRuleId.NotFound",
                    f"The ID '{rule_id}' does not exist",
                )
            for key, value in rule_data.items():
                if value is None:
                    continue
                rule[key] = value
            group.security_group_rules[rule_id] = rule

        return {
            'return': True,
            }

    def RevokeSecurityGroupEgress(self, params: Dict[str, Any]):
        """Removes the specified outbound (egress) rules from the specified security group. You can specify rules using either rule IDs or security group rule properties. If you use
         rule properties, the values that you specify (for example, ports) must match the existing rule's 
         values exactl"""

        error = self._require_params(params, ["GroupId"])
        if error:
            return error

        group_id = params.get("GroupId")
        group = self.resources.get(group_id)
        if not group:
            return create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_id}' does not exist.",
            )

        revoked_rules: List[Dict[str, Any]] = []
        unknown_permissions: List[Dict[str, Any]] = []

        rule_ids = params.get("SecurityGroupRuleId.N", []) or []
        if rule_ids:
            for rule_id in rule_ids:
                rule = group.security_group_rules.get(rule_id)
                if not rule:
                    return create_error_response(
                        "InvalidSecurityGroupRuleId.NotFound",
                        f"The ID '{rule_id}' does not exist",
                    )
                if not rule.get("isEgress"):
                    continue
                revoked_rules.append(
                    {
                        "cidrIpv4": rule.get("cidrIpv4"),
                        "cidrIpv6": rule.get("cidrIpv6"),
                        "description": rule.get("description"),
                        "fromPort": rule.get("fromPort"),
                        "groupId": rule.get("groupId"),
                        "ipProtocol": rule.get("ipProtocol"),
                        "isEgress": True,
                        "prefixListId": rule.get("prefixListId"),
                        "referencedGroupId": (rule.get("referencedGroupInfo") or {}).get("groupId"),
                        "securityGroupRuleId": rule.get("securityGroupRuleId"),
                        "toPort": rule.get("toPort"),
                    }
                )
                group.security_group_rules.pop(rule_id, None)

        ip_permissions = self._normalize_ip_permissions(params)
        print("[sg-debug] normalized ip_permissions =", ip_permissions)
        if ip_permissions:
            for perm in ip_permissions:
                matched = False
                ip_protocol = perm.get("IpProtocol")
                from_port = perm.get("FromPort")
                to_port = perm.get("ToPort")
                ip_ranges = perm.get("IpRanges", []) or []
                ipv6_ranges = perm.get("Ipv6Ranges", []) or []
                prefix_lists = perm.get("PrefixListIds", []) or []
                user_groups = perm.get("UserIdGroupPairs", []) or []

                for rule_id, rule in list(group.security_group_rules.items()):
                    if not rule.get("isEgress"):
                        continue
                    if ip_protocol is not None and rule.get("ipProtocol") != ip_protocol:
                        continue
                    if from_port is not None and rule.get("fromPort") != from_port:
                        continue
                    if to_port is not None and rule.get("toPort") != to_port:
                        continue

                    if rule.get("cidrIpv4") and ip_ranges:
                        if not any(r.get("CidrIp") == rule.get("cidrIpv4") for r in ip_ranges):
                            continue
                    if rule.get("cidrIpv6") and ipv6_ranges:
                        if not any(r.get("CidrIpv6") == rule.get("cidrIpv6") for r in ipv6_ranges):
                            continue
                    if rule.get("prefixListId") and prefix_lists:
                        if not any(p.get("PrefixListId") == rule.get("prefixListId") for p in prefix_lists):
                            continue
                    if rule.get("referencedGroupInfo") and user_groups:
                        ref_group_id = (rule.get("referencedGroupInfo") or {}).get("groupId")
                        if not any(p.get("GroupId") == ref_group_id for p in user_groups):
                            continue

                    matched = True
                    revoked_rules.append(
                        {
                            "cidrIpv4": rule.get("cidrIpv4"),
                            "cidrIpv6": rule.get("cidrIpv6"),
                            "description": rule.get("description"),
                            "fromPort": rule.get("fromPort"),
                            "groupId": rule.get("groupId"),
                            "ipProtocol": rule.get("ipProtocol"),
                            "isEgress": True,
                            "prefixListId": rule.get("prefixListId"),
                            "referencedGroupId": (rule.get("referencedGroupInfo") or {}).get("groupId"),
                            "securityGroupRuleId": rule.get("securityGroupRuleId"),
                            "toPort": rule.get("toPort"),
                        }
                    )
                    group.security_group_rules.pop(rule_id, None)

                if not matched:
                    unknown_permissions.append(
                        {
                            "FromPort": from_port,
                            "ToPort": to_port,
                            "IpProtocol": ip_protocol,
                            "IpRanges": ip_ranges,
                            "Ipv6Ranges": ipv6_ranges,
                            "PrefixListIds": prefix_lists,
                            "UserIdGroupPairs": user_groups,
                        }
                    )

        return {
            'return': True,
            'revokedSecurityGroupRuleSet': revoked_rules,
            'unknownIpPermissionSet': unknown_permissions,
            }

    def RevokeSecurityGroupIngress(self, params: Dict[str, Any]):
        """Removes the specified inbound (ingress) rules from a security group. You can specify rules using either rule IDs or security group rule properties. If you use
           rule properties, the values that you specify (for example, ports) must match the existing rule's 
           values exactly. Each """

        group_id = params.get("GroupId")
        group_name = params.get("GroupName")
        group, error = self._get_security_group_by_id_or_name(group_id, group_name)
        if error:
            return error

        revoked_rules: List[Dict[str, Any]] = []
        unknown_permissions: List[Dict[str, Any]] = []

        rule_ids = params.get("SecurityGroupRuleId.N", []) or []
        if rule_ids:
            for rule_id in rule_ids:
                rule = group.security_group_rules.get(rule_id)
                if not rule:
                    return create_error_response(
                        "InvalidSecurityGroupRuleId.NotFound",
                        f"The ID '{rule_id}' does not exist",
                    )
                if rule.get("isEgress"):
                    continue
                revoked_rules.append(
                    {
                        "cidrIpv4": rule.get("cidrIpv4"),
                        "cidrIpv6": rule.get("cidrIpv6"),
                        "description": rule.get("description"),
                        "fromPort": rule.get("fromPort"),
                        "groupId": rule.get("groupId"),
                        "ipProtocol": rule.get("ipProtocol"),
                        "isEgress": False,
                        "prefixListId": rule.get("prefixListId"),
                        "referencedGroupId": (rule.get("referencedGroupInfo") or {}).get("groupId"),
                        "securityGroupRuleId": rule.get("securityGroupRuleId"),
                        "toPort": rule.get("toPort"),
                    }
                )
                group.security_group_rules.pop(rule_id, None)

        ip_permissions = self._normalize_ip_permissions(params)
        print("[sg-debug] normalized ip_permissions =", ip_permissions)
        if ip_permissions:
            for perm in ip_permissions:
                matched = False
                ip_protocol = perm.get("IpProtocol")
                from_port = perm.get("FromPort")
                to_port = perm.get("ToPort")
                ip_ranges = perm.get("IpRanges", []) or []
                ipv6_ranges = perm.get("Ipv6Ranges", []) or []
                prefix_lists = perm.get("PrefixListIds", []) or []
                user_groups = perm.get("UserIdGroupPairs", []) or []

                for rule_id, rule in list(group.security_group_rules.items()):
                    if rule.get("isEgress"):
                        continue
                    if ip_protocol is not None and rule.get("ipProtocol") != ip_protocol:
                        continue
                    if from_port is not None and rule.get("fromPort") != from_port:
                        continue
                    if to_port is not None and rule.get("toPort") != to_port:
                        continue

                    if rule.get("cidrIpv4") and ip_ranges:
                        if not any(r.get("CidrIp") == rule.get("cidrIpv4") for r in ip_ranges):
                            continue
                    if rule.get("cidrIpv6") and ipv6_ranges:
                        if not any(r.get("CidrIpv6") == rule.get("cidrIpv6") for r in ipv6_ranges):
                            continue
                    if rule.get("prefixListId") and prefix_lists:
                        if not any(p.get("PrefixListId") == rule.get("prefixListId") for p in prefix_lists):
                            continue
                    if rule.get("referencedGroupInfo") and user_groups:
                        ref_group_id = (rule.get("referencedGroupInfo") or {}).get("groupId")
                        if not any(p.get("GroupId") == ref_group_id for p in user_groups):
                            continue

                    matched = True
                    revoked_rules.append(
                        {
                            "cidrIpv4": rule.get("cidrIpv4"),
                            "cidrIpv6": rule.get("cidrIpv6"),
                            "description": rule.get("description"),
                            "fromPort": rule.get("fromPort"),
                            "groupId": rule.get("groupId"),
                            "ipProtocol": rule.get("ipProtocol"),
                            "isEgress": False,
                            "prefixListId": rule.get("prefixListId"),
                            "referencedGroupId": (rule.get("referencedGroupInfo") or {}).get("groupId"),
                            "securityGroupRuleId": rule.get("securityGroupRuleId"),
                            "toPort": rule.get("toPort"),
                        }
                    )
                    group.security_group_rules.pop(rule_id, None)

                if not matched:
                    unknown_permissions.append(
                        {
                            "FromPort": from_port,
                            "ToPort": to_port,
                            "IpProtocol": ip_protocol,
                            "IpRanges": ip_ranges,
                            "Ipv6Ranges": ipv6_ranges,
                            "PrefixListIds": prefix_lists,
                            "UserIdGroupPairs": user_groups,
                        }
                    )

        return {
            'return': True,
            'revokedSecurityGroupRuleSet': revoked_rules,
            'unknownIpPermissionSet': unknown_permissions,
            }

    def UpdateSecurityGroupRuleDescriptionsEgress(self, params: Dict[str, Any]):
        """Updates the description of an egress (outbound) security group rule. You
			can replace an existing description, or add a description to a rule that did not have one
			previously. You can remove a description for a security group rule by omitting the 
			description parameter in the request."""

        group_id = params.get("GroupId")
        group_name = params.get("GroupName")
        group, error = self._get_security_group_by_id_or_name(group_id, group_name)
        if error:
            return error

        descriptions = params.get("SecurityGroupRuleDescription.N", []) or []
        ip_permissions = params.get("IpPermissions.N", []) or []
        if not descriptions and not ip_permissions:
            return create_error_response(
                "MissingParameter",
                "Either SecurityGroupRuleDescription.N or IpPermissions.N is required.",
            )

        for desc_entry in descriptions:
            rule_id = desc_entry.get("SecurityGroupRuleId")
            if not rule_id:
                return create_error_response(
                    "MissingParameter",
                    "Missing required parameter: SecurityGroupRuleId",
                )
            rule = group.security_group_rules.get(rule_id)
            if not rule:
                return create_error_response(
                    "InvalidSecurityGroupRuleId.NotFound",
                    f"The ID '{rule_id}' does not exist",
                )
            if not rule.get("isEgress"):
                continue
            if "Description" in desc_entry:
                rule["description"] = desc_entry.get("Description")
            else:
                rule.pop("description", None)
            group.security_group_rules[rule_id] = rule

        for perm in ip_permissions:
            ip_protocol = perm.get("IpProtocol")
            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort")
            for rule_id, rule in group.security_group_rules.items():
                if not rule.get("isEgress"):
                    continue
                if ip_protocol is not None and rule.get("ipProtocol") != ip_protocol:
                    continue
                if from_port is not None and rule.get("fromPort") != from_port:
                    continue
                if to_port is not None and rule.get("toPort") != to_port:
                    continue
                description = perm.get("Description")
                if description is None:
                    rule.pop("description", None)
                else:
                    rule["description"] = description
                group.security_group_rules[rule_id] = rule

        return {
            'return': True,
            }

    def UpdateSecurityGroupRuleDescriptionsIngress(self, params: Dict[str, Any]):
        """Updates the description of an ingress (inbound) security group rule. You can replace an
			existing description, or add a description to a rule that did not have one previously.
		    You can remove a description for a security group rule by omitting the description 
		    parameter in the request."""

        group_id = params.get("GroupId")
        group_name = params.get("GroupName")
        group, error = self._get_security_group_by_id_or_name(group_id, group_name)
        if error:
            return error

        descriptions = params.get("SecurityGroupRuleDescription.N", []) or []
        ip_permissions = params.get("IpPermissions.N", []) or []
        if not descriptions and not ip_permissions:
            return create_error_response(
                "MissingParameter",
                "Either SecurityGroupRuleDescription.N or IpPermissions.N is required.",
            )

        for desc_entry in descriptions:
            rule_id = desc_entry.get("SecurityGroupRuleId")
            if not rule_id:
                return create_error_response(
                    "MissingParameter",
                    "Missing required parameter: SecurityGroupRuleId",
                )
            rule = group.security_group_rules.get(rule_id)
            if not rule:
                return create_error_response(
                    "InvalidSecurityGroupRuleId.NotFound",
                    f"The ID '{rule_id}' does not exist",
                )
            if rule.get("isEgress"):
                continue
            if "Description" in desc_entry:
                rule["description"] = desc_entry.get("Description")
            else:
                rule.pop("description", None)
            group.security_group_rules[rule_id] = rule

        for perm in ip_permissions:
            ip_protocol = perm.get("IpProtocol")
            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort")
            for rule_id, rule in group.security_group_rules.items():
                if rule.get("isEgress"):
                    continue
                if ip_protocol is not None and rule.get("ipProtocol") != ip_protocol:
                    continue
                if from_port is not None and rule.get("fromPort") != from_port:
                    continue
                if to_port is not None and rule.get("toPort") != to_port:
                    continue
                description = perm.get("Description")
                if description is None:
                    rule.pop("description", None)
                else:
                    rule["description"] = description
                group.security_group_rules[rule_id] = rule

        return {
            'return': True,
            }

    def AssociateSecurityGroupVpc(self, params: Dict[str, Any]):
        """Associates a security group with another VPC in the same Region. This enables you to use the same security group with network interfaces and instances in the specified VPC. The VPC you want to associate the security group with must be in the same Region. You can associate the security group with ano"""

        error = self._require_params(params, ["GroupId", "VpcId"])
        if error:
            return error

        group_id = params.get("GroupId")
        vpc_id = params.get("VpcId")

        group = self.resources.get(group_id)
        if not group:
            return create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_id}' does not exist.",
            )

        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' does not exist.",
            )

        self._register_vpc_association(group, vpc_id, state="associated")
        if hasattr(vpc, "security_group_ids") and group_id not in vpc.security_group_ids:
            vpc.security_group_ids.append(group_id)

        return {
            'state': "associated",
            }

    def DescribeSecurityGroupReferences(self, params: Dict[str, Any]):
        """Describes the VPCs on the other side of a VPC peering or Transit Gateway connection that are referencing the security groups you've specified in this request."""

        error = self._require_params(params, ["GroupId.N"])
        if error:
            return error

        group_ids = params.get("GroupId.N", []) or []
        if not group_ids:
            return create_error_response("MissingParameter", "Missing required parameter: GroupId.N")

        references: List[Dict[str, Any]] = []
        for group_id in group_ids:
            group = self.resources.get(group_id)
            if not group:
                return create_error_response(
                    "InvalidGroup.NotFound",
                    f"The ID '{group_id}' does not exist",
                )
            for sg in self.resources.values():
                for rule in sg.security_group_rules.values():
                    ref_info = rule.get("referencedGroupInfo") or {}
                    if ref_info.get("groupId") != group_id:
                        continue
                    referencing_vpc_id = ref_info.get("vpcId") or sg.vpc_id
                    entry = {
                        "groupId": group_id,
                        "referencingVpcId": referencing_vpc_id,
                        "transitGatewayId": ref_info.get("transitGatewayId"),
                        "vpcPeeringConnectionId": ref_info.get("vpcPeeringConnectionId"),
                    }
                    references.append(entry)

        return {
            'securityGroupReferenceSet': references,
            }

    def DescribeSecurityGroupVpcAssociations(self, params: Dict[str, Any]):
        """Describes security group VPC associations made withAssociateSecurityGroupVpc."""

        associations: List[Dict[str, Any]] = []
        for group in self.resources.values():
            for vpc_id in group.associated_vpc_ids:
                assoc_state = group.vpc_association_states.get(vpc_id, {})
                vpc = self.state.vpcs.get(vpc_id)
                associations.append(
                    {
                        "groupId": group.group_id,
                        "groupOwnerId": group.owner_id,
                        "state": assoc_state.get("state", "associated"),
                        "stateReason": assoc_state.get("stateReason", ""),
                        "vpcId": vpc_id,
                        "vpcOwnerId": getattr(vpc, "owner_id", "") if vpc else "",
                    }
                )

        associations = apply_filters(associations, params.get("Filter.N", []))
        max_results = int(params.get("MaxResults") or 100)
        associations = associations[:max_results] if max_results else associations

        return {
            'nextToken': None,
            'securityGroupVpcAssociationSet': associations,
            }

    def DescribeStaleSecurityGroups(self, params: Dict[str, Any]):
        """Describes the stale security group rules for security groups referenced across a VPC
            peering connection, transit gateway connection, or with a security group VPC
            association. Rules are stale when they reference a deleted security group. Rules can
            also be stale if """

        error = self._require_params(params, ["VpcId"])
        if error:
            return error

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' does not exist.",
            )

        stale_groups: List[Dict[str, Any]] = []
        for group in self.resources.values():
            if group.vpc_id != vpc_id:
                continue
            stale_ingress: List[Dict[str, Any]] = []
            stale_egress: List[Dict[str, Any]] = []
            for rule in group.security_group_rules.values():
                ref_info = rule.get("referencedGroupInfo") or {}
                ref_group_id = ref_info.get("groupId")
                if not ref_group_id or ref_group_id in self.resources:
                    continue
                permission = {
                    "FromPort": rule.get("fromPort"),
                    "ToPort": rule.get("toPort"),
                    "IpProtocol": rule.get("ipProtocol"),
                    "UserIdGroupPairs": [
                        {
                            "GroupId": ref_group_id,
                            "VpcId": ref_info.get("vpcId"),
                        }
                    ],
                }
                if rule.get("isEgress"):
                    stale_egress.append(permission)
                else:
                    stale_ingress.append(permission)

            if stale_ingress or stale_egress:
                stale_groups.append(
                    {
                        "description": group.group_description,
                        "groupId": group.group_id,
                        "groupName": group.group_name,
                        "staleIpPermissions": stale_ingress,
                        "staleIpPermissionsEgress": stale_egress,
                        "vpcId": vpc_id,
                    }
                )

        max_results = int(params.get("MaxResults") or 100)
        stale_groups = stale_groups[:max_results] if max_results else stale_groups

        return {
            'nextToken': None,
            'staleSecurityGroupSet': stale_groups,
            }

    def DisassociateSecurityGroupVpc(self, params: Dict[str, Any]):
        """Disassociates a security group from a VPC. You cannot disassociate the security group if any Elastic network interfaces in the associated VPC are still associated with the security group.
            
            Note that the disassociation is asynchronous and you can check the status of the reques"""

        error = self._require_params(params, ["GroupId", "VpcId"])
        if error:
            return error

        group_id = params.get("GroupId")
        vpc_id = params.get("VpcId")

        group = self.resources.get(group_id)
        if not group:
            return create_error_response(
                "InvalidGroup.NotFound",
                f"Security group '{group_id}' does not exist.",
            )

        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' does not exist.",
            )

        if vpc_id not in group.associated_vpc_ids:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' is not associated with security group '{group_id}'.",
            )

        self._deregister_vpc_association(group, vpc_id)
        if hasattr(vpc, "security_group_ids") and group_id in vpc.security_group_ids:
            vpc.security_group_ids.remove(group_id)

        return {
            'state': "disassociated",
            }

    def GetSecurityGroupsForVpc(self, params: Dict[str, Any]):
        """Gets security groups that can be associated by the AWS account making the request with network interfaces in the specified VPC."""

        error = self._require_params(params, ["VpcId"])
        if error:
            return error

        vpc_id = params.get("VpcId")
        vpc = self.state.vpcs.get(vpc_id)
        if not vpc:
            return create_error_response(
                "InvalidVpcID.NotFound",
                f"VPC '{vpc_id}' does not exist.",
            )

        groups: List[SecurityGroup] = []
        for group in self.resources.values():
            if group.vpc_id == vpc_id or vpc_id in group.associated_vpc_ids:
                groups.append(group)

        groups = apply_filters(groups, params.get("Filter.N", []))
        max_results = int(params.get("MaxResults") or 100)
        groups = groups[:max_results] if max_results else groups

        return {
            'nextToken': None,
            'securityGroupForVpcSet': [
                {
                    "description": group.group_description,
                    "groupId": group.group_id,
                    "groupName": group.group_name,
                    "ownerId": group.owner_id,
                    "primaryVpcId": group.vpc_id,
                    "tagSet": group.tag_set,
                }
                for group in groups
            ],
            }

    def _generate_id(self, prefix: str = 'sg') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class securitygroup_RequestParser:
    
    @staticmethod
    def _extract_prefixed_params(md: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        return {k: v for k, v in md.items() if isinstance(k, str) and k.startswith(prefix)}
    
    @staticmethod
    def parse_authorize_security_group_egress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CidrIp": get_scalar(md, "CidrIp"),
            "CidrIpv6": get_scalar(md, "CidrIpv6"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "FromPort": get_int(md, "FromPort"),
            "GroupId": get_scalar(md, "GroupId"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "IpProtocol": get_scalar(md, "IpProtocol"),
            "SourceSecurityGroupName": get_scalar(md, "SourceSecurityGroupName"),
            "SourceSecurityGroupOwnerId": get_scalar(md, "SourceSecurityGroupOwnerId"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "ToPort": get_int(md, "ToPort"),
        }

    @staticmethod
    def parse_authorize_security_group_ingress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CidrIp": get_scalar(md, "CidrIp"),
            "CidrIpv6": get_scalar(md, "CidrIpv6"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "FromPort": get_int(md, "FromPort"),
            "GroupId": get_scalar(md, "GroupId"),
            "GroupName": get_scalar(md, "GroupName"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "IpProtocol": get_scalar(md, "IpProtocol"),
            "SourceSecurityGroupName": get_scalar(md, "SourceSecurityGroupName"),
            "SourceSecurityGroupOwnerId": get_scalar(md, "SourceSecurityGroupOwnerId"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "ToPort": get_int(md, "ToPort"),
        }

    @staticmethod
    def parse_create_security_group_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupDescription": get_scalar(md, "GroupDescription"),
            "GroupName": get_scalar(md, "GroupName"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_delete_security_group_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "GroupName": get_scalar(md, "GroupName"),
        }

    @staticmethod
    def parse_describe_security_group_rules_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "SecurityGroupRuleId.N": get_indexed_list(md, "SecurityGroupRuleId"),
        }

    @staticmethod
    def parse_describe_security_groups_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "GroupId.N": get_indexed_list(md, "GroupId"),
            "GroupName.N": get_indexed_list(md, "GroupName"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_modify_security_group_rules_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "SecurityGroupRule.N": get_indexed_list(md, "SecurityGroupRule"),
        }

    @staticmethod
    def parse_revoke_security_group_egress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CidrIp": get_scalar(md, "CidrIp"),
            "CidrIpv6": get_scalar(md, "CidrIpv6"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "FromPort": get_int(md, "FromPort"),
            "GroupId": get_scalar(md, "GroupId"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "IpProtocol": get_scalar(md, "IpProtocol"),
            "SecurityGroupRuleId.N": get_indexed_list(md, "SecurityGroupRuleId"),
            "SourceSecurityGroupName": get_scalar(md, "SourceSecurityGroupName"),
            "SourceSecurityGroupOwnerId": get_scalar(md, "SourceSecurityGroupOwnerId"),
            "ToPort": get_int(md, "ToPort"),
        }

    @staticmethod
    def parse_revoke_security_group_ingress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CidrIp": get_scalar(md, "CidrIp"),
            "CidrIpv6": get_scalar(md, "CidrIpv6"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "FromPort": get_int(md, "FromPort"),
            "GroupId": get_scalar(md, "GroupId"),
            "GroupName": get_scalar(md, "GroupName"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "IpProtocol": get_scalar(md, "IpProtocol"),
            "SecurityGroupRuleId.N": get_indexed_list(md, "SecurityGroupRuleId"),
            "SourceSecurityGroupName": get_scalar(md, "SourceSecurityGroupName"),
            "SourceSecurityGroupOwnerId": get_scalar(md, "SourceSecurityGroupOwnerId"),
            "ToPort": get_int(md, "ToPort"),
        }

    @staticmethod
    def parse_update_security_group_rule_descriptions_egress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "GroupName": get_scalar(md, "GroupName"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "SecurityGroupRuleDescription.N": get_indexed_list(md, "SecurityGroupRuleDescription"),
        }

    @staticmethod
    def parse_update_security_group_rule_descriptions_ingress_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "GroupName": get_scalar(md, "GroupName"),
            "IpPermissions.N": get_indexed_list(md, "IpPermissions"),
            "IpPermissionsRaw": securitygroup_RequestParser._extract_prefixed_params(md, "IpPermissions."),
            "SecurityGroupRuleDescription.N": get_indexed_list(md, "SecurityGroupRuleDescription"),
        }

    @staticmethod
    def parse_associate_security_group_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_describe_security_group_references_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId.N": get_indexed_list(md, "GroupId"),
        }

    @staticmethod
    def parse_describe_security_group_vpc_associations_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_stale_security_groups_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_disassociate_security_group_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "GroupId": get_scalar(md, "GroupId"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_get_security_groups_for_vpc_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "VpcId": get_scalar(md, "VpcId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "AuthorizeSecurityGroupEgress": securitygroup_RequestParser.parse_authorize_security_group_egress_request,
            "AuthorizeSecurityGroupIngress": securitygroup_RequestParser.parse_authorize_security_group_ingress_request,
            "CreateSecurityGroup": securitygroup_RequestParser.parse_create_security_group_request,
            "DeleteSecurityGroup": securitygroup_RequestParser.parse_delete_security_group_request,
            "DescribeSecurityGroupRules": securitygroup_RequestParser.parse_describe_security_group_rules_request,
            "DescribeSecurityGroups": securitygroup_RequestParser.parse_describe_security_groups_request,
            "ModifySecurityGroupRules": securitygroup_RequestParser.parse_modify_security_group_rules_request,
            "RevokeSecurityGroupEgress": securitygroup_RequestParser.parse_revoke_security_group_egress_request,
            "RevokeSecurityGroupIngress": securitygroup_RequestParser.parse_revoke_security_group_ingress_request,
            "UpdateSecurityGroupRuleDescriptionsEgress": securitygroup_RequestParser.parse_update_security_group_rule_descriptions_egress_request,
            "UpdateSecurityGroupRuleDescriptionsIngress": securitygroup_RequestParser.parse_update_security_group_rule_descriptions_ingress_request,
            "AssociateSecurityGroupVpc": securitygroup_RequestParser.parse_associate_security_group_vpc_request,
            "DescribeSecurityGroupReferences": securitygroup_RequestParser.parse_describe_security_group_references_request,
            "DescribeSecurityGroupVpcAssociations": securitygroup_RequestParser.parse_describe_security_group_vpc_associations_request,
            "DescribeStaleSecurityGroups": securitygroup_RequestParser.parse_describe_stale_security_groups_request,
            "DisassociateSecurityGroupVpc": securitygroup_RequestParser.parse_disassociate_security_group_vpc_request,
            "GetSecurityGroupsForVpc": securitygroup_RequestParser.parse_get_security_groups_for_vpc_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class securitygroup_ResponseSerializer:
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
                xml_parts.extend(securitygroup_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(securitygroup_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(securitygroup_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(securitygroup_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_authorize_security_group_egress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AuthorizeSecurityGroupEgressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupRuleSet
        _securityGroupRuleSet_key = None
        if "securityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "securityGroupRuleSet"
        elif "SecurityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "SecurityGroupRuleSet"
        elif "SecurityGroupRules" in data:
            _securityGroupRuleSet_key = "SecurityGroupRules"
        if _securityGroupRuleSet_key:
            param_data = data[_securityGroupRuleSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupRuleSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet/>')
        xml_parts.append(f'</AuthorizeSecurityGroupEgressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_authorize_security_group_ingress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AuthorizeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupRuleSet
        _securityGroupRuleSet_key = None
        if "securityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "securityGroupRuleSet"
        elif "SecurityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "SecurityGroupRuleSet"
        elif "SecurityGroupRules" in data:
            _securityGroupRuleSet_key = "SecurityGroupRules"
        if _securityGroupRuleSet_key:
            param_data = data[_securityGroupRuleSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupRuleSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet/>')
        xml_parts.append(f'</AuthorizeSecurityGroupIngressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_security_group_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize groupId
        _groupId_key = None
        if "groupId" in data:
            _groupId_key = "groupId"
        elif "GroupId" in data:
            _groupId_key = "GroupId"
        if _groupId_key:
            param_data = data[_groupId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<groupId>{esc(str(param_data))}</groupId>')
        # Serialize securityGroupArn
        _securityGroupArn_key = None
        if "securityGroupArn" in data:
            _securityGroupArn_key = "securityGroupArn"
        elif "SecurityGroupArn" in data:
            _securityGroupArn_key = "SecurityGroupArn"
        if _securityGroupArn_key:
            param_data = data[_securityGroupArn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<securityGroupArn>{esc(str(param_data))}</securityGroupArn>')
        # Serialize tagSet
        _tagSet_key = None
        if "tagSet" in data:
            _tagSet_key = "tagSet"
        elif "TagSet" in data:
            _tagSet_key = "TagSet"
        elif "Tags" in data:
            _tagSet_key = "Tags"
        if _tagSet_key:
            param_data = data[_tagSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<tagSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</tagSet>')
            else:
                xml_parts.append(f'{indent_str}<tagSet/>')
        xml_parts.append(f'</CreateSecurityGroupResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_security_group_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize groupId
        _groupId_key = None
        if "groupId" in data:
            _groupId_key = "groupId"
        elif "GroupId" in data:
            _groupId_key = "GroupId"
        if _groupId_key:
            param_data = data[_groupId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<groupId>{esc(str(param_data))}</groupId>')
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
        xml_parts.append(f'</DeleteSecurityGroupResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_security_group_rules_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSecurityGroupRulesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupRuleSet
        _securityGroupRuleSet_key = None
        if "securityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "securityGroupRuleSet"
        elif "SecurityGroupRuleSet" in data:
            _securityGroupRuleSet_key = "SecurityGroupRuleSet"
        elif "SecurityGroupRules" in data:
            _securityGroupRuleSet_key = "SecurityGroupRules"
        if _securityGroupRuleSet_key:
            param_data = data[_securityGroupRuleSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupRuleSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupRuleSet/>')
        xml_parts.append(f'</DescribeSecurityGroupRulesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_security_groups_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupInfo
        _securityGroupInfo_key = None
        if "securityGroupInfo" in data:
            _securityGroupInfo_key = "securityGroupInfo"
        elif "SecurityGroupInfo" in data:
            _securityGroupInfo_key = "SecurityGroupInfo"
        
        if _securityGroupInfo_key:
            param_data = data[_securityGroupInfo_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupInfo>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupInfo>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupInfo/>')

        xml_parts.append(f'</DescribeSecurityGroupsResponse>')
        xml = "\n".join(xml_parts)
        print("[sg-describe-xml]", xml)
        return xml

    @staticmethod
    def serialize_modify_security_group_rules_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifySecurityGroupRulesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ModifySecurityGroupRulesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_revoke_security_group_egress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RevokeSecurityGroupEgressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize revokedSecurityGroupRuleSet
        _revokedSecurityGroupRuleSet_key = None
        if "revokedSecurityGroupRuleSet" in data:
            _revokedSecurityGroupRuleSet_key = "revokedSecurityGroupRuleSet"
        elif "RevokedSecurityGroupRuleSet" in data:
            _revokedSecurityGroupRuleSet_key = "RevokedSecurityGroupRuleSet"
        elif "RevokedSecurityGroupRules" in data:
            _revokedSecurityGroupRuleSet_key = "RevokedSecurityGroupRules"
        if _revokedSecurityGroupRuleSet_key:
            param_data = data[_revokedSecurityGroupRuleSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<revokedSecurityGroupRuleSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</revokedSecurityGroupRuleSet>')
            else:
                xml_parts.append(f'{indent_str}<revokedSecurityGroupRuleSet/>')
        # Serialize unknownIpPermissionSet
        _unknownIpPermissionSet_key = None
        if "unknownIpPermissionSet" in data:
            _unknownIpPermissionSet_key = "unknownIpPermissionSet"
        elif "UnknownIpPermissionSet" in data:
            _unknownIpPermissionSet_key = "UnknownIpPermissionSet"
        elif "UnknownIpPermissions" in data:
            _unknownIpPermissionSet_key = "UnknownIpPermissions"
        if _unknownIpPermissionSet_key:
            param_data = data[_unknownIpPermissionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<unknownIpPermissionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</unknownIpPermissionSet>')
            else:
                xml_parts.append(f'{indent_str}<unknownIpPermissionSet/>')
        xml_parts.append(f'</RevokeSecurityGroupEgressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_revoke_security_group_ingress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize revokedSecurityGroupRuleSet
        _revokedSecurityGroupRuleSet_key = None
        if "revokedSecurityGroupRuleSet" in data:
            _revokedSecurityGroupRuleSet_key = "revokedSecurityGroupRuleSet"
        elif "RevokedSecurityGroupRuleSet" in data:
            _revokedSecurityGroupRuleSet_key = "RevokedSecurityGroupRuleSet"
        elif "RevokedSecurityGroupRules" in data:
            _revokedSecurityGroupRuleSet_key = "RevokedSecurityGroupRules"
        if _revokedSecurityGroupRuleSet_key:
            param_data = data[_revokedSecurityGroupRuleSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<revokedSecurityGroupRuleSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</revokedSecurityGroupRuleSet>')
            else:
                xml_parts.append(f'{indent_str}<revokedSecurityGroupRuleSet/>')
        # Serialize unknownIpPermissionSet
        _unknownIpPermissionSet_key = None
        if "unknownIpPermissionSet" in data:
            _unknownIpPermissionSet_key = "unknownIpPermissionSet"
        elif "UnknownIpPermissionSet" in data:
            _unknownIpPermissionSet_key = "UnknownIpPermissionSet"
        elif "UnknownIpPermissions" in data:
            _unknownIpPermissionSet_key = "UnknownIpPermissions"
        if _unknownIpPermissionSet_key:
            param_data = data[_unknownIpPermissionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<unknownIpPermissionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</unknownIpPermissionSet>')
            else:
                xml_parts.append(f'{indent_str}<unknownIpPermissionSet/>')
        xml_parts.append(f'</RevokeSecurityGroupIngressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_update_security_group_rule_descriptions_egress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<UpdateSecurityGroupRuleDescriptionsEgressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</UpdateSecurityGroupRuleDescriptionsEgressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_update_security_group_rule_descriptions_ingress_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<UpdateSecurityGroupRuleDescriptionsIngressResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</UpdateSecurityGroupRuleDescriptionsIngressResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_associate_security_group_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<AssociateSecurityGroupVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize state
        _state_key = None
        if "state" in data:
            _state_key = "state"
        elif "State" in data:
            _state_key = "State"
        if _state_key:
            param_data = data[_state_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<state>{esc(str(param_data))}</state>')
        xml_parts.append(f'</AssociateSecurityGroupVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_security_group_references_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSecurityGroupReferencesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize securityGroupReferenceSet
        _securityGroupReferenceSet_key = None
        if "securityGroupReferenceSet" in data:
            _securityGroupReferenceSet_key = "securityGroupReferenceSet"
        elif "SecurityGroupReferenceSet" in data:
            _securityGroupReferenceSet_key = "SecurityGroupReferenceSet"
        elif "SecurityGroupReferences" in data:
            _securityGroupReferenceSet_key = "SecurityGroupReferences"
        if _securityGroupReferenceSet_key:
            param_data = data[_securityGroupReferenceSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupReferenceSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupReferenceSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupReferenceSet/>')
        xml_parts.append(f'</DescribeSecurityGroupReferencesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_security_group_vpc_associations_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSecurityGroupVpcAssociationsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupVpcAssociationSet
        _securityGroupVpcAssociationSet_key = None
        if "securityGroupVpcAssociationSet" in data:
            _securityGroupVpcAssociationSet_key = "securityGroupVpcAssociationSet"
        elif "SecurityGroupVpcAssociationSet" in data:
            _securityGroupVpcAssociationSet_key = "SecurityGroupVpcAssociationSet"
        elif "SecurityGroupVpcAssociations" in data:
            _securityGroupVpcAssociationSet_key = "SecurityGroupVpcAssociations"
        if _securityGroupVpcAssociationSet_key:
            param_data = data[_securityGroupVpcAssociationSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupVpcAssociationSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupVpcAssociationSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupVpcAssociationSet/>')
        xml_parts.append(f'</DescribeSecurityGroupVpcAssociationsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_stale_security_groups_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeStaleSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize staleSecurityGroupSet
        _staleSecurityGroupSet_key = None
        if "staleSecurityGroupSet" in data:
            _staleSecurityGroupSet_key = "staleSecurityGroupSet"
        elif "StaleSecurityGroupSet" in data:
            _staleSecurityGroupSet_key = "StaleSecurityGroupSet"
        elif "StaleSecurityGroups" in data:
            _staleSecurityGroupSet_key = "StaleSecurityGroups"
        if _staleSecurityGroupSet_key:
            param_data = data[_staleSecurityGroupSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<staleSecurityGroupSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</staleSecurityGroupSet>')
            else:
                xml_parts.append(f'{indent_str}<staleSecurityGroupSet/>')
        xml_parts.append(f'</DescribeStaleSecurityGroupsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disassociate_security_group_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisassociateSecurityGroupVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize state
        _state_key = None
        if "state" in data:
            _state_key = "state"
        elif "State" in data:
            _state_key = "State"
        if _state_key:
            param_data = data[_state_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<state>{esc(str(param_data))}</state>')
        xml_parts.append(f'</DisassociateSecurityGroupVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_security_groups_for_vpc_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetSecurityGroupsForVpcResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize securityGroupForVpcSet
        _securityGroupForVpcSet_key = None
        if "securityGroupForVpcSet" in data:
            _securityGroupForVpcSet_key = "securityGroupForVpcSet"
        elif "SecurityGroupForVpcSet" in data:
            _securityGroupForVpcSet_key = "SecurityGroupForVpcSet"
        elif "SecurityGroupForVpcs" in data:
            _securityGroupForVpcSet_key = "SecurityGroupForVpcs"
        if _securityGroupForVpcSet_key:
            param_data = data[_securityGroupForVpcSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<securityGroupForVpcSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(securitygroup_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</securityGroupForVpcSet>')
            else:
                xml_parts.append(f'{indent_str}<securityGroupForVpcSet/>')
        xml_parts.append(f'</GetSecurityGroupsForVpcResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "AuthorizeSecurityGroupEgress": securitygroup_ResponseSerializer.serialize_authorize_security_group_egress_response,
            "AuthorizeSecurityGroupIngress": securitygroup_ResponseSerializer.serialize_authorize_security_group_ingress_response,
            "CreateSecurityGroup": securitygroup_ResponseSerializer.serialize_create_security_group_response,
            "DeleteSecurityGroup": securitygroup_ResponseSerializer.serialize_delete_security_group_response,
            "DescribeSecurityGroupRules": securitygroup_ResponseSerializer.serialize_describe_security_group_rules_response,
            "DescribeSecurityGroups": securitygroup_ResponseSerializer.serialize_describe_security_groups_response,
            "ModifySecurityGroupRules": securitygroup_ResponseSerializer.serialize_modify_security_group_rules_response,
            "RevokeSecurityGroupEgress": securitygroup_ResponseSerializer.serialize_revoke_security_group_egress_response,
            "RevokeSecurityGroupIngress": securitygroup_ResponseSerializer.serialize_revoke_security_group_ingress_response,
            "UpdateSecurityGroupRuleDescriptionsEgress": securitygroup_ResponseSerializer.serialize_update_security_group_rule_descriptions_egress_response,
            "UpdateSecurityGroupRuleDescriptionsIngress": securitygroup_ResponseSerializer.serialize_update_security_group_rule_descriptions_ingress_response,
            "AssociateSecurityGroupVpc": securitygroup_ResponseSerializer.serialize_associate_security_group_vpc_response,
            "DescribeSecurityGroupReferences": securitygroup_ResponseSerializer.serialize_describe_security_group_references_response,
            "DescribeSecurityGroupVpcAssociations": securitygroup_ResponseSerializer.serialize_describe_security_group_vpc_associations_response,
            "DescribeStaleSecurityGroups": securitygroup_ResponseSerializer.serialize_describe_stale_security_groups_response,
            "DisassociateSecurityGroupVpc": securitygroup_ResponseSerializer.serialize_disassociate_security_group_vpc_response,
            "GetSecurityGroupsForVpc": securitygroup_ResponseSerializer.serialize_get_security_groups_for_vpc_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)

