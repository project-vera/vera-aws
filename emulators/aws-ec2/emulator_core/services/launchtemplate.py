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
class LaunchTemplate:
    created_by: str = ""
    create_time: str = ""
    default_version_number: int = 0
    latest_version_number: int = 0
    launch_template_id: str = ""
    launch_template_name: str = ""
    operator: Dict[str, Any] = field(default_factory=dict)
    tag_set: List[Any] = field(default_factory=list)

    versions: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "createdBy": self.created_by,
            "createTime": self.create_time,
            "defaultVersionNumber": self.default_version_number,
            "latestVersionNumber": self.latest_version_number,
            "launchTemplateId": self.launch_template_id,
            "launchTemplateName": self.launch_template_name,
            "operator": self.operator,
            "tagSet": self.tag_set,
        }

class LaunchTemplate_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.launch_templates  # alias to shared store

    def _find_template_by_name(self, name: str) -> Optional[LaunchTemplate]:
        for template in self.resources.values():
            if template.launch_template_name == name:
                return template
        return None

    def _get_template(self, launch_template_id: Optional[str], launch_template_name: Optional[str], required: bool = False):
        if launch_template_id:
            template = self.resources.get(launch_template_id)
            if not template:
                return None, create_error_response(
                    "InvalidLaunchTemplateId.NotFound",
                    f"Launch template '{launch_template_id}' does not exist.",
                )
            return template, None
        if launch_template_name:
            template = self._find_template_by_name(launch_template_name)
            if not template:
                return None, create_error_response(
                    "InvalidLaunchTemplateName.NotFound",
                    f"Launch template '{launch_template_name}' does not exist.",
                )
            return template, None
        if required:
            return None, create_error_response(
                "MissingParameter",
                "LaunchTemplateId or LaunchTemplateName is required.",
            )
        return None, None

    def _resolve_version_number(self, template: LaunchTemplate, version: Optional[str]) -> Optional[int]:
        if version is None or version == "":
            return None
        if str(version) == "$Latest":
            return template.latest_version_number
        if str(version) == "$Default":
            return template.default_version_number
        try:
            return int(version)
        except (TypeError, ValueError):
            return None

    def CreateLaunchTemplate(self, params: Dict[str, Any]):
        """Creates a launch template. A launch template contains the parameters to launch an instance. When you launch an
            instance usingRunInstances, you can specify a launch template instead
            of providing the launch parameters in the request. For more information, seeStore
             """

        required_params = ["LaunchTemplateData", "LaunchTemplateName"]
        for name in required_params:
            if not params.get(name):
                return create_error_response("MissingParameter", f"Missing required parameter: {name}")

        launch_template_name = params.get("LaunchTemplateName")
        if self._find_template_by_name(launch_template_name):
            return create_error_response(
                "InvalidLaunchTemplateName.AlreadyExists",
                f"Launch template '{launch_template_name}' already exists.",
            )

        operator = params.get("Operator") or {}
        if not isinstance(operator, dict):
            operator = {}
        operator.setdefault("managed", None)
        operator.setdefault("principal", None)

        tag_set = []
        for spec in params.get("TagSpecification.N", []) or []:
            tags = spec.get("Tags") or []
            for tag in tags:
                if isinstance(tag, dict):
                    tag_set.append({"Key": tag.get("Key"), "Value": tag.get("Value")})

        create_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        created_by = operator.get("principal") or ""
        launch_template_id = self._generate_id("lt")
        version_number = 1
        launch_template_data = params.get("LaunchTemplateData") or {}
        version_description = params.get("VersionDescription") or ""

        resource = LaunchTemplate(
            created_by=created_by,
            create_time=create_time,
            default_version_number=version_number,
            latest_version_number=version_number,
            launch_template_id=launch_template_id,
            launch_template_name=launch_template_name,
            operator=operator,
            tag_set=tag_set,
        )
        resource.versions[version_number] = {
            "createdBy": created_by,
            "createTime": create_time,
            "defaultVersion": True,
            "launchTemplateData": launch_template_data,
            "operator": operator,
            "versionDescription": version_description,
            "versionNumber": version_number,
        }
        self.resources[launch_template_id] = resource

        return {
            'launchTemplate': resource.to_dict(),
            'warning': {
                'errorSet': [],
                },
            }

    def CreateLaunchTemplateVersion(self, params: Dict[str, Any]):
        """Creates a new version of a launch template. You must specify an existing launch
            template, either by name or ID. You can determine whether the new version inherits
            parameters from a source version, and add or overwrite parameters as needed. Launch template versions are numbere"""

        if not params.get("LaunchTemplateData"):
            return create_error_response("MissingParameter", "Missing required parameter: LaunchTemplateData")

        template, error = self._get_template(
            params.get("LaunchTemplateId"),
            params.get("LaunchTemplateName"),
            required=True,
        )
        if error:
            return error

        source_version = params.get("SourceVersion")
        resolved_source = self._resolve_version_number(template, source_version)
        if source_version is not None and resolved_source is None:
            return create_error_response(
                "InvalidLaunchTemplateVersion.NotFound",
                f"Launch template version '{source_version}' does not exist.",
            )

        base_data = {}
        if resolved_source is not None:
            source = template.versions.get(resolved_source)
            if not source:
                return create_error_response(
                    "InvalidLaunchTemplateVersion.NotFound",
                    f"Launch template version '{source_version}' does not exist.",
                )
            base_data = source.get("launchTemplateData") or {}

        launch_template_data = params.get("LaunchTemplateData") or {}
        if isinstance(base_data, dict) and isinstance(launch_template_data, dict):
            merged_data = {**base_data, **launch_template_data}
        else:
            merged_data = launch_template_data or base_data

        create_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        version_number = template.latest_version_number + 1
        version_description = params.get("VersionDescription") or ""

        operator = template.operator or {}
        if not isinstance(operator, dict):
            operator = {}
        operator.setdefault("managed", None)
        operator.setdefault("principal", None)

        created_by = template.created_by
        if not created_by:
            created_by = operator.get("principal") or ""

        template.latest_version_number = version_number
        template.versions[version_number] = {
            "createdBy": created_by,
            "createTime": create_time,
            "defaultVersion": version_number == template.default_version_number,
            "launchTemplateData": merged_data,
            "operator": operator,
            "versionDescription": version_description,
            "versionNumber": version_number,
        }

        return {
            'launchTemplateVersion': {
                'createdBy': created_by,
                'createTime': create_time,
                'defaultVersion': version_number == template.default_version_number,
                'launchTemplateData': merged_data,
                'launchTemplateId': template.launch_template_id,
                'launchTemplateName': template.launch_template_name,
                'operator': operator,
                'versionDescription': version_description,
                'versionNumber': version_number,
                },
            'warning': {
                'errorSet': [],
                },
            }

    def DeleteLaunchTemplate(self, params: Dict[str, Any]):
        """Deletes a launch template. Deleting a launch template deletes all of its
            versions."""

        template, error = self._get_template(
            params.get("LaunchTemplateId"),
            params.get("LaunchTemplateName"),
            required=True,
        )
        if error:
            return error

        template_data = template.to_dict()
        self.resources.pop(template.launch_template_id, None)

        return {
            'launchTemplate': template_data,
            }

    def DeleteLaunchTemplateVersions(self, params: Dict[str, Any]):
        """Deletes one or more versions of a launch template. You can't delete the default version of a launch template; you must first assign a
            different version as the default. If the default version is the only version for the
            launch template, you must delete the entire launch templa"""

        if not params.get("LaunchTemplateVersion.N"):
            return create_error_response("MissingParameter", "Missing required parameter: LaunchTemplateVersion.N")

        template, error = self._get_template(
            params.get("LaunchTemplateId"),
            params.get("LaunchTemplateName"),
            required=True,
        )
        if error:
            return error

        requested_versions = params.get("LaunchTemplateVersion.N", []) or []
        success = []
        failure = []

        for version in requested_versions:
            resolved = self._resolve_version_number(template, version)
            if resolved is None or resolved not in template.versions:
                failure.append({
                    "launchTemplateId": template.launch_template_id,
                    "launchTemplateName": template.launch_template_name,
                    "responseError": {
                        "code": "InvalidLaunchTemplateVersion.NotFound",
                        "message": f"Launch template version '{version}' does not exist.",
                    },
                    "versionNumber": version,
                })
                continue

            if resolved == template.default_version_number:
                failure.append({
                    "launchTemplateId": template.launch_template_id,
                    "launchTemplateName": template.launch_template_name,
                    "responseError": {
                        "code": "InvalidLaunchTemplateVersion.NotAllowed",
                        "message": "Cannot delete the default launch template version.",
                    },
                    "versionNumber": resolved,
                })
                continue

            template.versions.pop(resolved, None)
            success.append({
                "launchTemplateId": template.launch_template_id,
                "launchTemplateName": template.launch_template_name,
                "versionNumber": resolved,
            })

        if template.versions:
            template.latest_version_number = max(template.versions.keys())
        else:
            template.latest_version_number = 0

        return {
            'successfullyDeletedLaunchTemplateVersionSet': success,
            'unsuccessfullyDeletedLaunchTemplateVersionSet': failure,
            }

    def DescribeLaunchTemplates(self, params: Dict[str, Any]):
        """Describes one or more launch templates."""

        template_ids = params.get("LaunchTemplateId.N", []) or []
        template_names = params.get("LaunchTemplateName.N", []) or []

        selected = []
        if template_ids:
            for template_id in template_ids:
                template = self.resources.get(template_id)
                if not template:
                    return create_error_response(
                        "InvalidLaunchTemplateId.NotFound",
                        f"The ID '{template_id}' does not exist",
                    )
                selected.append(template)
        elif template_names:
            for template_name in template_names:
                template = self._find_template_by_name(template_name)
                if not template:
                    return create_error_response(
                        "InvalidLaunchTemplateName.NotFound",
                        f"The ID '{template_name}' does not exist",
                    )
                selected.append(template)
        else:
            selected = list(self.resources.values())

        selected_dicts = [template.to_dict() for template in selected]
        filtered = apply_filters(selected_dicts, params.get("Filter.N", []))

        max_results = int(params.get("MaxResults") or 100)
        return {
            'launchTemplates': filtered[:max_results],
            'nextToken': None,
            }

    def DescribeLaunchTemplateVersions(self, params: Dict[str, Any]):
        """Describes one or more versions of a specified launch template. You can describe all
            versions, individual versions, or a range of versions. You can also describe all the
            latest versions or all the default versions of all the launch templates in your
            account."""

        template, error = self._get_template(
            params.get("LaunchTemplateId"),
            params.get("LaunchTemplateName"),
            required=False,
        )
        if error:
            return error

        templates = [template] if template else list(self.resources.values())
        template_specified = template is not None
        requested_versions = params.get("LaunchTemplateVersion.N", []) or []

        def _parse_bound(value: Optional[str], current_template: LaunchTemplate) -> Optional[int]:
            if value is None or value == "":
                return None
            resolved = self._resolve_version_number(current_template, value)
            if resolved is None:
                return None
            return resolved

        version_entries = []
        for tmpl in templates:
            available_versions = tmpl.versions or {}
            if requested_versions:
                version_numbers = []
                for version in requested_versions:
                    resolved = self._resolve_version_number(tmpl, version)
                    if resolved is None:
                        if template_specified:
                            return create_error_response(
                                "InvalidLaunchTemplateVersion.NotFound",
                                f"Launch template version '{version}' does not exist.",
                            )
                        continue
                    if resolved not in available_versions:
                        if template_specified:
                            return create_error_response(
                                "InvalidLaunchTemplateVersion.NotFound",
                                f"Launch template version '{version}' does not exist.",
                            )
                        continue
                    version_numbers.append(resolved)
            else:
                version_numbers = list(available_versions.keys())

            min_version = _parse_bound(params.get("MinVersion"), tmpl)
            max_version = _parse_bound(params.get("MaxVersion"), tmpl)
            if template_specified and params.get("MinVersion") is not None and min_version is None:
                return create_error_response(
                    "InvalidLaunchTemplateVersion.NotFound",
                    f"Launch template version '{params.get('MinVersion')}' does not exist.",
                )
            if template_specified and params.get("MaxVersion") is not None and max_version is None:
                return create_error_response(
                    "InvalidLaunchTemplateVersion.NotFound",
                    f"Launch template version '{params.get('MaxVersion')}' does not exist.",
                )

            filtered_numbers = []
            for number in version_numbers:
                if min_version is not None and number < min_version:
                    continue
                if max_version is not None and number > max_version:
                    continue
                filtered_numbers.append(number)

            for number in sorted(filtered_numbers):
                data = available_versions.get(number, {})
                operator = data.get("operator") or tmpl.operator or {}
                if not isinstance(operator, dict):
                    operator = {}
                operator.setdefault("managed", None)
                operator.setdefault("principal", None)
                version_entries.append({
                    "createdBy": data.get("createdBy", tmpl.created_by),
                    "createTime": data.get("createTime", tmpl.create_time),
                    "defaultVersion": number == tmpl.default_version_number,
                    "launchTemplateData": data.get("launchTemplateData") or {},
                    "launchTemplateId": tmpl.launch_template_id,
                    "launchTemplateName": tmpl.launch_template_name,
                    "operator": operator,
                    "versionDescription": data.get("versionDescription", ""),
                    "versionNumber": number,
                })

        filtered = apply_filters(version_entries, params.get("Filter.N", []))
        max_results = int(params.get("MaxResults") or 100)

        return {
            'launchTemplateVersionSet': filtered[:max_results],
            'nextToken': None,
            }

    def GetLaunchTemplateData(self, params: Dict[str, Any]):
        """Retrieves the configuration data of the specified instance. You can use this data to
            create a launch template. This action calls on other describe actions to get instance information. Depending on
            your instance configuration, you may need to allow the following actions in you"""

        if not params.get("InstanceId"):
            return create_error_response("MissingParameter", "Missing required parameter: InstanceId")

        instance_id = params.get("InstanceId") or ""
        instance = self.state.instances.get(instance_id)
        if not instance:
            return create_error_response("InvalidInstanceID.NotFound", f"The ID '{instance_id}' does not exist")

        operator = instance.operator or {}
        if not isinstance(operator, dict):
            operator = {}
        operator.setdefault("managed", None)
        operator.setdefault("principal", None)

        capacity_spec = instance.capacity_reservation_specification or {}
        if not isinstance(capacity_spec, dict):
            capacity_spec = {}
        capacity_spec.setdefault("capacityReservationPreference", None)
        capacity_target = capacity_spec.get("capacityReservationTarget")
        if not isinstance(capacity_target, dict):
            capacity_target = {}
        capacity_target.setdefault("capacityReservationId", instance.capacity_reservation_id or None)
        capacity_target.setdefault("capacityReservationResourceGroupArn", None)
        capacity_spec["capacityReservationTarget"] = capacity_target

        cpu_options = instance.cpu_options or {}
        if not isinstance(cpu_options, dict):
            cpu_options = {}
        cpu_options.setdefault("amdSevSnp", None)
        cpu_options.setdefault("coreCount", None)
        cpu_options.setdefault("threadsPerCore", None)

        credit_spec = instance.credit_specification or {}
        if not isinstance(credit_spec, dict):
            credit_spec = {}
        credit_spec.setdefault("cpuCredits", None)

        enclave_options = instance.enclave_options or {}
        if not isinstance(enclave_options, dict):
            enclave_options = {}
        enclave_options.setdefault("enabled", None)

        hibernation_options = instance.hibernation_options or {}
        if not isinstance(hibernation_options, dict):
            hibernation_options = {}
        hibernation_options.setdefault("configured", None)

        iam_profile = instance.iam_instance_profile or {}
        if not isinstance(iam_profile, dict):
            iam_profile = {}
        iam_profile.setdefault("arn", None)
        iam_profile.setdefault("name", None)

        instance_market_options = {
            "marketType": instance.instance_lifecycle or None,
            "spotOptions": {
                "blockDurationMinutes": None,
                "instanceInterruptionBehavior": None,
                "maxPrice": None,
                "spotInstanceType": None,
                "validUntil": None,
            },
        }

        instance_requirements = {
            "AcceleratorCount": {"Max": None, "Min": None},
            "AcceleratorManufacturers": None,
            "AcceleratorNames": None,
            "AcceleratorTotalMemoryMiB": {"Max": None, "Min": None},
            "AcceleratorTypes": None,
            "AllowedInstanceTypes": None,
            "BareMetal": None,
            "BaselineEbsBandwidthMbps": {"Max": None, "Min": None},
            "BaselinePerformanceFactors": {"Cpu": {"References": None}},
            "BurstablePerformance": None,
            "CpuManufacturers": None,
            "ExcludedInstanceTypes": None,
            "InstanceGenerations": None,
            "LocalStorage": None,
            "LocalStorageTypes": None,
            "MaxSpotPriceAsPercentageOfOptimalOnDemandPrice": None,
            "MemoryGiBPerVCpu": {"Max": None, "Min": None},
            "MemoryMiB": {"Max": None, "Min": None},
            "NetworkBandwidthGbps": {"Max": None, "Min": None},
            "NetworkInterfaceCount": {"Max": None, "Min": None},
            "OnDemandMaxPricePercentageOverLowestPrice": None,
            "RequireEncryptionInTransit": None,
            "RequireHibernateSupport": None,
            "SpotMaxPricePercentageOverLowestPrice": None,
            "TotalLocalStorageGB": {"Max": None, "Min": None},
            "VCpuCount": {"Max": None, "Min": None},
        }

        maintenance_options = instance.maintenance_options or {}
        if not isinstance(maintenance_options, dict):
            maintenance_options = {}
        maintenance_options.setdefault("autoRecovery", None)

        metadata_options = instance.metadata_options or {}
        if not isinstance(metadata_options, dict):
            metadata_options = {}
        metadata_options.setdefault("httpEndpoint", None)
        metadata_options.setdefault("httpProtocolIpv6", None)
        metadata_options.setdefault("httpPutResponseHopLimit", None)
        metadata_options.setdefault("httpTokens", None)
        metadata_options.setdefault("instanceMetadataTags", None)
        metadata_options.setdefault("state", None)

        monitoring = instance.monitoring or {}
        if not isinstance(monitoring, dict):
            monitoring = {}
        monitoring.setdefault("enabled", None)

        network_performance_options = instance.network_performance_options or {}
        if not isinstance(network_performance_options, dict):
            network_performance_options = {}
        network_performance_options.setdefault("bandwidthWeighting", None)

        placement = instance.placement or {}
        if not isinstance(placement, dict):
            placement = {}
        placement.setdefault("affinity", None)
        placement.setdefault("availabilityZone", None)
        placement.setdefault("availabilityZoneId", None)
        placement.setdefault("groupId", None)
        placement.setdefault("groupName", None)
        placement.setdefault("hostId", None)
        placement.setdefault("hostResourceGroupArn", None)
        placement.setdefault("partitionNumber", None)
        placement.setdefault("spreadDomain", None)
        placement.setdefault("tenancy", None)

        private_dns_options = instance.private_dns_name_options or {}
        if not isinstance(private_dns_options, dict):
            private_dns_options = {}
        private_dns_options.setdefault("enableResourceNameDnsAAAARecord", None)
        private_dns_options.setdefault("enableResourceNameDnsARecord", None)
        private_dns_options.setdefault("hostnameType", None)

        security_group_set = instance.group_set or []
        security_group_id_set = []
        for group in security_group_set:
            if isinstance(group, dict):
                group_id = group.get("groupId") or group.get("GroupId")
                if group_id:
                    security_group_id_set.append(group_id)

        tag_specifications = []
        if instance.tag_set:
            tag_specifications.append({
                "resourceType": "instance",
                "tagSet": instance.tag_set,
            })

        return {
            'launchTemplateData': {
                'blockDeviceMappingSet': instance.block_device_mapping or [],
                'capacityReservationSpecification': capacity_spec,
                'cpuOptions': cpu_options,
                'creditSpecification': credit_spec,
                'disableApiStop': instance.disable_api_stop,
                'disableApiTermination': instance.disable_api_termination,
                'ebsOptimized': instance.ebs_optimized,
                'elasticGpuSpecificationSet': instance.elastic_gpu_association_set or [],
                'elasticInferenceAcceleratorSet': instance.elastic_inference_accelerator_association_set or [],
                'enclaveOptions': enclave_options,
                'hibernationOptions': hibernation_options,
                'iamInstanceProfile': iam_profile,
                'imageId': instance.image_id or None,
                'instanceInitiatedShutdownBehavior': instance.instance_initiated_shutdown_behavior or None,
                'instanceMarketOptions': instance_market_options,
                'instanceRequirements': instance_requirements,
                'instanceType': instance.instance_type or None,
                'kernelId': instance.kernel_id or None,
                'keyName': instance.key_name or None,
                'licenseSet': instance.license_set or [],
                'maintenanceOptions': maintenance_options,
                'metadataOptions': metadata_options,
                'monitoring': monitoring,
                'networkInterfaceSet': instance.network_interface_set or [],
                'networkPerformanceOptions': network_performance_options,
                'operator': operator,
                'placement': placement,
                'privateDnsNameOptions': private_dns_options,
                'ramDiskId': instance.ramdisk_id or None,
                'securityGroupIdSet': security_group_id_set,
                'securityGroupSet': security_group_set,
                'tagSpecificationSet': tag_specifications,
                'userData': instance.user_data or None,
                },
            }

    def ModifyLaunchTemplate(self, params: Dict[str, Any]):
        """Modifies a launch template. You can specify which version of the launch template to
            set as the default version. When launching an instance, the default version applies when
            a launch template version is not specified."""

        template, error = self._get_template(
            params.get("LaunchTemplateId"),
            params.get("LaunchTemplateName"),
            required=True,
        )
        if error:
            return error

        set_default_version = params.get("SetDefaultVersion")
        if set_default_version is not None:
            resolved = self._resolve_version_number(template, set_default_version)
            if resolved is None or resolved not in template.versions:
                return create_error_response(
                    "InvalidLaunchTemplateVersion.NotFound",
                    f"Launch template version '{set_default_version}' does not exist.",
                )
            template.default_version_number = resolved
            for version_number, version_data in template.versions.items():
                if isinstance(version_data, dict):
                    version_data["defaultVersion"] = version_number == resolved

        return {
            'launchTemplate': template.to_dict(),
            }

    def _generate_id(self, prefix: str = 'lt') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, get_nested_dict, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class launchtemplate_RequestParser:
    @staticmethod
    def parse_create_launch_template_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "LaunchTemplateData": get_nested_dict(md, "LaunchTemplateData") or None,
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
            "Operator": get_scalar(md, "Operator"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VersionDescription": get_scalar(md, "VersionDescription"),
        }

    @staticmethod
    def parse_create_launch_template_version_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "LaunchTemplateData": get_nested_dict(md, "LaunchTemplateData") or None,
            "LaunchTemplateId": get_scalar(md, "LaunchTemplateId"),
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
            "ResolveAlias": get_scalar(md, "ResolveAlias"),
            "SourceVersion": get_scalar(md, "SourceVersion"),
            "VersionDescription": get_scalar(md, "VersionDescription"),
        }

    @staticmethod
    def parse_delete_launch_template_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "LaunchTemplateId": get_scalar(md, "LaunchTemplateId"),
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
        }

    @staticmethod
    def parse_delete_launch_template_versions_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "LaunchTemplateId": get_scalar(md, "LaunchTemplateId"),
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
            "LaunchTemplateVersion.N": get_indexed_list(md, "LaunchTemplateVersion"),
        }

    @staticmethod
    def parse_describe_launch_templates_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "LaunchTemplateId.N": get_indexed_list(md, "LaunchTemplateId"),
            "LaunchTemplateName.N": get_indexed_list(md, "LaunchTemplateName"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_launch_template_versions_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "LaunchTemplateId": get_scalar(md, "LaunchTemplateId"),
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
            "LaunchTemplateVersion.N": get_indexed_list(md, "LaunchTemplateVersion"),
            "MaxResults": get_int(md, "MaxResults"),
            "MaxVersion": get_scalar(md, "MaxVersion"),
            "MinVersion": get_scalar(md, "MinVersion"),
            "NextToken": get_scalar(md, "NextToken"),
            "ResolveAlias": get_scalar(md, "ResolveAlias"),
        }

    @staticmethod
    def parse_get_launch_template_data_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InstanceId": get_scalar(md, "InstanceId"),
        }

    @staticmethod
    def parse_modify_launch_template_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "LaunchTemplateId": get_scalar(md, "LaunchTemplateId"),
            "LaunchTemplateName": get_scalar(md, "LaunchTemplateName"),
            "SetDefaultVersion": get_scalar(md, "SetDefaultVersion"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "CreateLaunchTemplate": launchtemplate_RequestParser.parse_create_launch_template_request,
            "CreateLaunchTemplateVersion": launchtemplate_RequestParser.parse_create_launch_template_version_request,
            "DeleteLaunchTemplate": launchtemplate_RequestParser.parse_delete_launch_template_request,
            "DeleteLaunchTemplateVersions": launchtemplate_RequestParser.parse_delete_launch_template_versions_request,
            "DescribeLaunchTemplates": launchtemplate_RequestParser.parse_describe_launch_templates_request,
            "DescribeLaunchTemplateVersions": launchtemplate_RequestParser.parse_describe_launch_template_versions_request,
            "GetLaunchTemplateData": launchtemplate_RequestParser.parse_get_launch_template_data_request,
            "ModifyLaunchTemplate": launchtemplate_RequestParser.parse_modify_launch_template_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class launchtemplate_ResponseSerializer:
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
                xml_parts.extend(launchtemplate_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(launchtemplate_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(launchtemplate_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(launchtemplate_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_create_launch_template_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateLaunchTemplateResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplate
        _launchTemplate_key = None
        if "launchTemplate" in data:
            _launchTemplate_key = "launchTemplate"
        elif "LaunchTemplate" in data:
            _launchTemplate_key = "LaunchTemplate"
        if _launchTemplate_key:
            param_data = data[_launchTemplate_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<launchTemplate>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplate>')
        # Serialize warning
        _warning_key = None
        if "warning" in data:
            _warning_key = "warning"
        elif "Warning" in data:
            _warning_key = "Warning"
        if _warning_key:
            param_data = data[_warning_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<warning>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</warning>')
        xml_parts.append(f'</CreateLaunchTemplateResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_launch_template_version_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateLaunchTemplateVersionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplateVersion
        _launchTemplateVersion_key = None
        if "launchTemplateVersion" in data:
            _launchTemplateVersion_key = "launchTemplateVersion"
        elif "LaunchTemplateVersion" in data:
            _launchTemplateVersion_key = "LaunchTemplateVersion"
        if _launchTemplateVersion_key:
            param_data = data[_launchTemplateVersion_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<launchTemplateVersion>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplateVersion>')
        # Serialize warning
        _warning_key = None
        if "warning" in data:
            _warning_key = "warning"
        elif "Warning" in data:
            _warning_key = "Warning"
        if _warning_key:
            param_data = data[_warning_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<warning>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</warning>')
        xml_parts.append(f'</CreateLaunchTemplateVersionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_launch_template_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteLaunchTemplateResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplate
        _launchTemplate_key = None
        if "launchTemplate" in data:
            _launchTemplate_key = "launchTemplate"
        elif "LaunchTemplate" in data:
            _launchTemplate_key = "LaunchTemplate"
        if _launchTemplate_key:
            param_data = data[_launchTemplate_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<launchTemplate>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplate>')
        xml_parts.append(f'</DeleteLaunchTemplateResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_launch_template_versions_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteLaunchTemplateVersionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize successfullyDeletedLaunchTemplateVersionSet
        _successfullyDeletedLaunchTemplateVersionSet_key = None
        if "successfullyDeletedLaunchTemplateVersionSet" in data:
            _successfullyDeletedLaunchTemplateVersionSet_key = "successfullyDeletedLaunchTemplateVersionSet"
        elif "SuccessfullyDeletedLaunchTemplateVersionSet" in data:
            _successfullyDeletedLaunchTemplateVersionSet_key = "SuccessfullyDeletedLaunchTemplateVersionSet"
        elif "SuccessfullyDeletedLaunchTemplateVersions" in data:
            _successfullyDeletedLaunchTemplateVersionSet_key = "SuccessfullyDeletedLaunchTemplateVersions"
        if _successfullyDeletedLaunchTemplateVersionSet_key:
            param_data = data[_successfullyDeletedLaunchTemplateVersionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<successfullyDeletedLaunchTemplateVersionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</successfullyDeletedLaunchTemplateVersionSet>')
            else:
                xml_parts.append(f'{indent_str}<successfullyDeletedLaunchTemplateVersionSet/>')
        # Serialize unsuccessfullyDeletedLaunchTemplateVersionSet
        _unsuccessfullyDeletedLaunchTemplateVersionSet_key = None
        if "unsuccessfullyDeletedLaunchTemplateVersionSet" in data:
            _unsuccessfullyDeletedLaunchTemplateVersionSet_key = "unsuccessfullyDeletedLaunchTemplateVersionSet"
        elif "UnsuccessfullyDeletedLaunchTemplateVersionSet" in data:
            _unsuccessfullyDeletedLaunchTemplateVersionSet_key = "UnsuccessfullyDeletedLaunchTemplateVersionSet"
        elif "UnsuccessfullyDeletedLaunchTemplateVersions" in data:
            _unsuccessfullyDeletedLaunchTemplateVersionSet_key = "UnsuccessfullyDeletedLaunchTemplateVersions"
        if _unsuccessfullyDeletedLaunchTemplateVersionSet_key:
            param_data = data[_unsuccessfullyDeletedLaunchTemplateVersionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<unsuccessfullyDeletedLaunchTemplateVersionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</unsuccessfullyDeletedLaunchTemplateVersionSet>')
            else:
                xml_parts.append(f'{indent_str}<unsuccessfullyDeletedLaunchTemplateVersionSet/>')
        xml_parts.append(f'</DeleteLaunchTemplateVersionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_launch_templates_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeLaunchTemplatesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplates
        _launchTemplates_key = None
        if "launchTemplates" in data:
            _launchTemplates_key = "launchTemplates"
        elif "LaunchTemplates" in data:
            _launchTemplates_key = "LaunchTemplates"
        if _launchTemplates_key:
            param_data = data[_launchTemplates_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<launchTemplatesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</launchTemplatesSet>')
            else:
                xml_parts.append(f'{indent_str}<launchTemplatesSet/>')
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
        xml_parts.append(f'</DescribeLaunchTemplatesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_launch_template_versions_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeLaunchTemplateVersionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplateVersionSet
        _launchTemplateVersionSet_key = None
        if "launchTemplateVersionSet" in data:
            _launchTemplateVersionSet_key = "launchTemplateVersionSet"
        elif "LaunchTemplateVersionSet" in data:
            _launchTemplateVersionSet_key = "LaunchTemplateVersionSet"
        elif "LaunchTemplateVersions" in data:
            _launchTemplateVersionSet_key = "LaunchTemplateVersions"
        if _launchTemplateVersionSet_key:
            param_data = data[_launchTemplateVersionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<launchTemplateVersionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</launchTemplateVersionSet>')
            else:
                xml_parts.append(f'{indent_str}<launchTemplateVersionSet/>')
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
        xml_parts.append(f'</DescribeLaunchTemplateVersionsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_launch_template_data_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetLaunchTemplateDataResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplateData
        _launchTemplateData_key = None
        if "launchTemplateData" in data:
            _launchTemplateData_key = "launchTemplateData"
        elif "LaunchTemplateData" in data:
            _launchTemplateData_key = "LaunchTemplateData"
        if _launchTemplateData_key:
            param_data = data[_launchTemplateData_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<launchTemplateData>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplateData>')
        xml_parts.append(f'</GetLaunchTemplateDataResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_launch_template_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyLaunchTemplateResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize launchTemplate
        _launchTemplate_key = None
        if "launchTemplate" in data:
            _launchTemplate_key = "launchTemplate"
        elif "LaunchTemplate" in data:
            _launchTemplate_key = "LaunchTemplate"
        if _launchTemplate_key:
            param_data = data[_launchTemplate_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<launchTemplate>')
            xml_parts.extend(launchtemplate_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplate>')
        xml_parts.append(f'</ModifyLaunchTemplateResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "CreateLaunchTemplate": launchtemplate_ResponseSerializer.serialize_create_launch_template_response,
            "CreateLaunchTemplateVersion": launchtemplate_ResponseSerializer.serialize_create_launch_template_version_response,
            "DeleteLaunchTemplate": launchtemplate_ResponseSerializer.serialize_delete_launch_template_response,
            "DeleteLaunchTemplateVersions": launchtemplate_ResponseSerializer.serialize_delete_launch_template_versions_response,
            "DescribeLaunchTemplates": launchtemplate_ResponseSerializer.serialize_describe_launch_templates_response,
            "DescribeLaunchTemplateVersions": launchtemplate_ResponseSerializer.serialize_describe_launch_template_versions_response,
            "GetLaunchTemplateData": launchtemplate_ResponseSerializer.serialize_get_launch_template_data_response,
            "ModifyLaunchTemplate": launchtemplate_ResponseSerializer.serialize_modify_launch_template_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)

