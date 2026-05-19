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
class Ami:
    image_id: str = ""
    launch_template: Dict[str, Any] = field(default_factory=dict)
    max_parallel_launches: int = 0
    owner_id: str = ""
    resource_type: str = ""
    snapshot_configuration: Dict[str, Any] = field(default_factory=dict)
    state: str = ""
    state_transition_reason: str = ""
    state_transition_time: str = ""

    # Internal dependency tracking — not in API response
    instance_ids: List[str] = field(default_factory=list)  # tracks Instance children
    vm_export_ids: List[str] = field(default_factory=list)  # tracks VmExport children

    name: str = ""
    description: str = ""
    image_state: str = ""
    image_type: str = ""
    architecture: str = ""
    creation_date: str = ""
    deprecation_time: str = ""
    deregistration_protection: bool = False
    is_public: bool = False
    image_location: str = ""
    image_owner_alias: str = ""
    image_owner_id: str = ""
    platform: str = ""
    platform_details: str = ""
    root_device_name: str = ""
    root_device_type: str = ""
    virtualization_type: str = ""
    ena_support: bool = False
    sriov_net_support: str = ""
    tpm_support: str = ""
    boot_mode: str = ""
    imds_support: str = ""
    kernel_id: str = ""
    ramdisk_id: str = ""
    uefi_data: str = ""
    last_launched_time: str = ""
    usage_operation: str = ""
    source_image_id: str = ""
    source_image_region: str = ""
    source_instance_id: str = ""
    image_allowed: bool = False
    free_tier_eligible: bool = False
    hypervisor: str = ""
    block_device_mappings: List[Dict[str, Any]] = field(default_factory=list)
    product_codes: List[Dict[str, Any]] = field(default_factory=list)
    launch_permissions: List[Dict[str, Any]] = field(default_factory=list)
    tag_set: List[Dict[str, Any]] = field(default_factory=list)
    state_reason: Dict[str, Any] = field(default_factory=dict)
    recycle_bin_enter_time: str = ""
    recycle_bin_exit_time: str = ""
    in_recycle_bin: bool = False


    def to_dict(self) -> Dict[str, Any]:
        return {
            "imageId": self.image_id,
            "launchTemplate": self.launch_template,
            "maxParallelLaunches": self.max_parallel_launches,
            "ownerId": self.owner_id,
            "resourceType": self.resource_type,
            "snapshotConfiguration": self.snapshot_configuration,
            "state": self.state,
            "stateTransitionReason": self.state_transition_reason,
            "stateTransitionTime": self.state_transition_time,
            "architecture": self.architecture,
            "blockDeviceMapping": self.block_device_mappings,
            "bootMode": self.boot_mode,
            "creationDate": self.creation_date,
            "deprecationTime": self.deprecation_time,
            "deregistrationProtection": self.deregistration_protection,
            "description": self.description,
            "enaSupport": self.ena_support,
            "freeTierEligible": self.free_tier_eligible,
            "hypervisor": self.hypervisor,
            "imageAllowed": self.image_allowed,
            "imageLocation": self.image_location,
            "imageOwnerAlias": self.image_owner_alias,
            "imageOwnerId": self.image_owner_id or self.owner_id,
            "imageState": self.image_state,
            "imageType": self.image_type,
            "imdsSupport": self.imds_support,
            "isPublic": self.is_public,
            "kernelId": self.kernel_id,
            "lastLaunchedTime": self.last_launched_time,
            "launchPermission": self.launch_permissions,
            "name": self.name,
            "platform": self.platform,
            "platformDetails": self.platform_details,
            "productCodes": self.product_codes,
            "ramdiskId": self.ramdisk_id,
            "rootDeviceName": self.root_device_name,
            "rootDeviceType": self.root_device_type,
            "sourceImageId": self.source_image_id,
            "sourceImageRegion": self.source_image_region,
            "sourceInstanceId": self.source_instance_id,
            "sriovNetSupport": self.sriov_net_support,
            "stateReason": self.state_reason,
            "tagSet": self.tag_set,
            "tpmSupport": self.tpm_support,
            "uefiData": self.uefi_data,
            "usageOperation": self.usage_operation,
            "virtualizationType": self.virtualization_type,
            "recycleBinEnterTime": self.recycle_bin_enter_time,
            "recycleBinExitTime": self.recycle_bin_exit_time,
            "inRecycleBin": self.in_recycle_bin,

        }

class Ami_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.amis  # alias to shared store
        self._ensure_default_images()

    def _ensure_default_images(self) -> None:
        if self.resources:
            return

        amazon_linux_2 = Ami(
            image_id="ami-0f9fc25dd2506cf6d",
            owner_id="137112412989",
            image_owner_id="137112412989",
            image_owner_alias="amazon",
            name="amzn2-ami-hvm-2.0.20240109.0-x86_64-gp2",
            description="Amazon Linux 2 AMI (HVM), SSD Volume Type",
            state="available",
            image_state="available",
            image_type="machine",
            architecture="x86_64",
            creation_date="2024-01-09T00:00:00.000Z",
            is_public=True,
            image_location="amazon/amzn2-ami-hvm-2.0.20240109.0-x86_64-gp2",
            platform_details="Linux/UNIX",
            root_device_name="/dev/xvda",
            root_device_type="ebs",
            virtualization_type="hvm",
            ena_support=True,
            sriov_net_support="simple",
            hypervisor="xen",
            block_device_mappings=[
                {
                    "deviceName": "/dev/xvda",
                    "ebs": {
                        "deleteOnTermination": True,
                        "encrypted": False,
                        "snapshotId": "snap-0f9fc25dd2506cf6d",
                        "volumeSize": 8,
                        "volumeType": "gp2",
                    },
                }
            ],
        )
        self.resources[amazon_linux_2.image_id] = amazon_linux_2

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _require_params(self, params: Dict[str, Any], required: List[str]) -> Optional[Dict[str, Any]]:
        for name in required:
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

    def _get_ami_or_error(self, image_id: str, error_code: str = "InvalidAMIID.NotFound"):
        return self._get_resource_or_error(self.resources, image_id, error_code, f"The ID '{image_id}' does not exist")

    def _extract_tags(self, tag_specs: List[Dict[str, Any]], resource_type: str = "image") -> List[Dict[str, Any]]:
        tags: List[Dict[str, Any]] = []
        for spec in tag_specs or []:
            spec_type = spec.get("ResourceType")
            if spec_type and spec_type != resource_type:
                continue
            for tag in spec.get("Tag") or spec.get("Tags") or []:
                if tag:
                    tags.append(tag)
        return tags

    def _set_fast_launch_state(self, image: Ami, new_state: str, reason: str = "") -> None:
        image.state = new_state
        image.state_transition_reason = reason
        image.state_transition_time = self._utc_now()



    def CancelImageLaunchPermission(self, params: Dict[str, Any]):
        """Removes your AWS account from the launch permissions for the specified AMI.
      For more information, seeCancel having an AMI shared with
        your AWS accountin theAmazon EC2 User Guide."""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.launch_permissions = []

        return {
            'return': True,
            }

    def CopyImage(self, params: Dict[str, Any]):
        """Initiates an AMI copy operation. You must specify the source AMI ID and both the source
      and destination locations. The copy operation must be initiated in the destination
      Region. Region to Region Region to Outpost"""

        error = self._require_params(params, ["Name", "SourceImageId", "SourceRegion"])
        if error:
            return error

        source_image_id = params.get("SourceImageId")
        source_image, error = self._get_ami_or_error(source_image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image_id = self._generate_id("ami")
        now = self._utc_now()
        copy_tags = str2bool(params.get("CopyImageTags"))
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        if copy_tags and not tag_set:
            tag_set = list(source_image.tag_set)

        resource = Ami(
            image_id=image_id,
            name=params.get("Name") or "",
            description=params.get("Description") or source_image.description,
            owner_id=source_image.owner_id,
            image_owner_id=source_image.image_owner_id,
            architecture=source_image.architecture,
            boot_mode=source_image.boot_mode,
            ena_support=source_image.ena_support,
            image_location=source_image.image_location,
            imds_support=source_image.imds_support,
            kernel_id=source_image.kernel_id,
            ramdisk_id=source_image.ramdisk_id,
            root_device_name=source_image.root_device_name,
            root_device_type=source_image.root_device_type,
            sriov_net_support=source_image.sriov_net_support,
            tpm_support=source_image.tpm_support,
            uefi_data=source_image.uefi_data,
            virtualization_type=source_image.virtualization_type,
            image_state="available",
            image_type=source_image.image_type,
            creation_date=now,
            state="available",
            state_transition_reason="copied",
            state_transition_time=now,
            source_image_id=source_image_id,
            source_image_region=params.get("SourceRegion") or "",
            block_device_mappings=list(source_image.block_device_mappings),
            product_codes=list(source_image.product_codes),
            tag_set=tag_set,
        )
        self.resources[image_id] = resource

        return {
            'imageId': image_id,
            }

    def CreateImage(self, params: Dict[str, Any]):
        """Creates an Amazon EBS-backed AMI from an Amazon EBS-backed instance that is either running or
      stopped. If you customized your instance with instance store volumes or Amazon EBS volumes in addition
      to the root device volume, the new AMI contains block device mapping information for those
"""

        error = self._require_params(params, ["InstanceId", "Name"])
        if error:
            return error

        instance_id = params.get("InstanceId")
        instance = self.state.instances.get(instance_id)
        if not instance:
            return create_error_response("InvalidInstanceID.NotFound", f"Instance '{instance_id}' does not exist.")

        image_id = self._generate_id("ami")
        now = self._utc_now()
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        owner_id = getattr(instance, "owner_id", "")
        resource = Ami(
            image_id=image_id,
            owner_id=owner_id,
            image_owner_id=owner_id,
            name=params.get("Name") or "",
            description=params.get("Description") or "",
            image_state="available",
            image_type="machine",
            root_device_type="ebs",
            virtualization_type="hvm",
            creation_date=now,
            state="disabled",
            state_transition_reason="created",
            state_transition_time=now,
            source_instance_id=instance_id,
            block_device_mappings=params.get("BlockDeviceMapping.N", []) or [],
            tag_set=tag_set,
            snapshot_configuration={"snapshotLocation": params.get("SnapshotLocation") or ""} if params.get("SnapshotLocation") else {},
        )
        self.resources[image_id] = resource

        return {
            'imageId': image_id,
            }

    def CreateImageUsageReport(self, params: Dict[str, Any]):
        """Creates a report that shows how your image is used across other AWS accounts. The report
      provides visibility into which accounts are using the specified image, and how many resources
      (EC2 instances or launch templates) are referencing it. For more information, seeView your AMI usagein th"""

        error = self._require_params(params, ["ImageId", "ResourceType.N"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        report_id = self._generate_id("rpt")
        now = self._utc_now()
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        report = {
            "reportId": report_id,
            "imageId": image_id,
            "accountIdSet": params.get("AccountId.N", []) or [],
            "resourceTypeSet": params.get("ResourceType.N", []) or [],
            "creationTime": now,
            "expirationTime": "",
            "state": "available",
            "stateReason": {},
            "tagSet": tag_set,
        }

        if not hasattr(self.state, "image_usage_reports"):
            setattr(self.state, "image_usage_reports", {})
        self.state.image_usage_reports[report_id] = report
        if not hasattr(self.state, "image_usage_report_entries"):
            setattr(self.state, "image_usage_report_entries", {})
        self.state.image_usage_report_entries.setdefault(report_id, [])

        return {
            'reportId': report_id,
            }

    def CreateRestoreImageTask(self, params: Dict[str, Any]):
        """Starts a task that restores an AMI from an Amazon S3 object that was previously created by
      usingCreateStoreImageTask. To use this API, you must have the required permissions. For more information, seePermissions for storing and restoring AMIs using S3in theAmazon EC2 User Guide. For more infor"""

        error = self._require_params(params, ["Bucket", "ObjectKey"])
        if error:
            return error

        image_id = self._generate_id("ami")
        now = self._utc_now()
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        name = params.get("Name") or params.get("ObjectKey") or image_id
        resource = Ami(
            image_id=image_id,
            name=name,
            description="",
            image_state="available",
            image_type="machine",
            root_device_type="ebs",
            virtualization_type="hvm",
            creation_date=now,
            state="available",
            state_transition_reason="restored",
            state_transition_time=now,
            tag_set=tag_set,
            snapshot_configuration={
                "bucket": params.get("Bucket") or "",
                "objectKey": params.get("ObjectKey") or "",
            },
        )
        self.resources[image_id] = resource

        return {
            'imageId': image_id,
            }

    def CreateStoreImageTask(self, params: Dict[str, Any]):
        """Stores an AMI as a single object in an Amazon S3 bucket. To use this API, you must have the required permissions. For more information, seePermissions for storing and restoring AMIs using S3in theAmazon EC2 User Guide. For more information, seeStore and restore an AMI using
        S3in theAmazon EC"""

        error = self._require_params(params, ["Bucket", "ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        object_key = f"{image_id}-{uuid.uuid4().hex[:8]}"
        task = {
            "amiId": image_id,
            "bucket": params.get("Bucket") or "",
            "s3objectKey": object_key,
            "progressPercentage": 100,
            "storeTaskState": "Completed",
            "storeTaskFailureReason": "",
            "taskStartTime": self._utc_now(),
            "s3ObjectTagSet": params.get("S3ObjectTag.N", []) or [],
        }
        if not hasattr(self.state, "store_image_tasks"):
            setattr(self.state, "store_image_tasks", {})
        self.state.store_image_tasks.setdefault(image_id, []).append(task)

        return {
            'objectKey': object_key,
            }

    def DeleteImageUsageReport(self, params: Dict[str, Any]):
        """Deletes the specified image usage report. For more information, seeView your AMI usagein theAmazon EC2 User Guide."""

        error = self._require_params(params, ["ReportId"])
        if error:
            return error

        report_id = params.get("ReportId")
        if not hasattr(self.state, "image_usage_reports") or report_id not in self.state.image_usage_reports:
            return create_error_response("InvalidReportId.NotFound", f"The ID '{report_id}' does not exist")

        del self.state.image_usage_reports[report_id]
        if hasattr(self.state, "image_usage_report_entries"):
            self.state.image_usage_report_entries.pop(report_id, None)

        return {
            'return': True,
            }

    def DeregisterImage(self, params: Dict[str, Any]):
        """Deregisters the specified AMI. A deregistered AMI can't be used to launch new
      instances. If a deregistered EBS-backed AMI matches a Recycle Bin retention rule, it moves to the
      Recycle Bin for the specified retention period. It can be restored before its retention period
      expires, af"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        if getattr(image, "instance_ids", []):
            return create_error_response("DependencyViolation", "Ami has dependent Instance(s) and cannot be deleted.")
        if getattr(image, "vm_export_ids", []):
            return create_error_response("DependencyViolation", "Ami has dependent VmExport(s) and cannot be deleted.")

        delete_snapshots = str2bool(params.get("DeleteAssociatedSnapshots"))
        delete_results = []
        if delete_snapshots:
            for mapping in image.block_device_mappings or []:
                snapshot_id = None
                ebs = mapping.get("Ebs") if isinstance(mapping, dict) else None
                if isinstance(ebs, dict):
                    snapshot_id = ebs.get("SnapshotId")
                if snapshot_id:
                    delete_results.append({"returnCode": "0", "snapshotId": snapshot_id})

        if delete_snapshots:
            del self.resources[image_id]
        else:
            image.image_state = "deregistered"
            image.in_recycle_bin = True
            image.recycle_bin_enter_time = self._utc_now()

        return {
            'deleteSnapshotResultSet': delete_results,
            'return': True,
            }

    def DescribeFastLaunchImages(self, params: Dict[str, Any]):
        """Describe details for Windows AMIs that are configured for Windows fast launch."""

        image_ids = params.get("ImageId.N", []) or []
        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        filtered = apply_filters(resources, params.get("Filter.N", []))
        fast_launch_images = [
            {
                "imageId": image.image_id,
                "launchTemplate": image.launch_template,
                "maxParallelLaunches": image.max_parallel_launches,
                "ownerId": image.owner_id,
                "resourceType": image.resource_type,
                "snapshotConfiguration": image.snapshot_configuration,
                "state": image.state,
                "stateTransitionReason": image.state_transition_reason,
                "stateTransitionTime": image.state_transition_time,
            }
            for image in filtered
        ]

        return {
            'fastLaunchImageSet': fast_launch_images,
            'nextToken': None,
            }

    def DescribeImageAttribute(self, params: Dict[str, Any]):
        """Describes the specified attribute of the specified AMI. You can specify only one attribute
      at a time. The order of the elements in the response, including those within nested structures,
        might vary. Applications should not assume the elements appear in a particular order."""

        error = self._require_params(params, ["Attribute", "ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or ""
        response = {
            'blockDeviceMapping': None,
            'bootMode': {'Value': None},
            'deregistrationProtection': {'Value': None},
            'description': {'Value': None},
            'imageId': image.image_id,
            'imdsSupport': {'Value': None},
            'kernel': {'Value': None},
            'lastLaunchedTime': {'Value': None},
            'launchPermission': None,
            'productCodes': None,
            'ramdisk': {'Value': None},
            'sriovNetSupport': {'Value': None},
            'tpmSupport': {'Value': None},
            'uefiData': {'Value': None},
        }

        if attribute in ("blockDeviceMapping", "block-device-mapping"):
            response['blockDeviceMapping'] = image.block_device_mappings
        elif attribute in ("bootMode", "boot-mode"):
            response['bootMode']['Value'] = image.boot_mode
        elif attribute == "deregistrationProtection":
            response['deregistrationProtection']['Value'] = str(image.deregistration_protection).lower()
        elif attribute == "description":
            response['description']['Value'] = image.description
        elif attribute == "imdsSupport":
            response['imdsSupport']['Value'] = image.imds_support
        elif attribute == "kernel":
            response['kernel']['Value'] = image.kernel_id
        elif attribute == "lastLaunchedTime":
            response['lastLaunchedTime']['Value'] = image.last_launched_time
        elif attribute == "launchPermission":
            response['launchPermission'] = image.launch_permissions
        elif attribute == "productCodes":
            response['productCodes'] = image.product_codes
        elif attribute == "ramdisk":
            response['ramdisk']['Value'] = image.ramdisk_id
        elif attribute == "sriovNetSupport":
            response['sriovNetSupport']['Value'] = image.sriov_net_support
        elif attribute == "tpmSupport":
            response['tpmSupport']['Value'] = image.tpm_support
        elif attribute == "uefiData":
            response['uefiData']['Value'] = image.uefi_data

        return response

    def DescribeImageReferences(self, params: Dict[str, Any]):
        """Describes your AWS resources that are referencing the specified images. For more information, seeIdentify your resources referencing
        specified AMIsin theAmazon EC2 User Guide."""

        error = self._require_params(params, ["ImageId.N"])
        if error:
            return error

        image_ids = params.get("ImageId.N", []) or []
        resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
        if error:
            return error

        resource_types = params.get("ResourceType.N", []) or []
        include_all = str2bool(params.get("IncludeAllResourceTypes"))
        references = []
        for image in resources:
            if include_all or (not resource_types or "instance" in resource_types):
                for instance_id in getattr(image, "instance_ids", []) or []:
                    references.append({
                        "arn": f"arn:aws:ec2:region:account:instance/{instance_id}",
                        "imageId": image.image_id,
                        "resourceType": "instance",
                    })
            if include_all or (not resource_types or "vm-export" in resource_types):
                for export_id in getattr(image, "vm_export_ids", []) or []:
                    references.append({
                        "arn": f"arn:aws:ec2:region:account:vm-export/{export_id}",
                        "imageId": image.image_id,
                        "resourceType": "vm-export",
                    })

        return {
            'imageReferenceSet': references,
            'nextToken': None,
            }

    def DescribeImages(self, params: Dict[str, Any]):
        """Describes the specified images (AMIs, AKIs, and ARIs) available to you or all of the
      images available to you. The images available to you include public images, private images that you own, and
      private images owned by other AWS accounts for which you have explicit launch
      permission"""

        image_ids = params.get("ImageId.N", []) or []
        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        owners = params.get("Owner.N", []) or []
        if owners:
            resources = [
                image
                for image in resources
                if image.owner_id in owners
                or image.image_owner_id in owners
                or image.image_owner_alias in owners
            ]

        include_disabled = str2bool(params.get("IncludeDisabled"))
        include_deprecated = str2bool(params.get("IncludeDeprecated"))
        if not include_disabled:
            resources = [image for image in resources if image.state != "disabled"]
        if not include_deprecated:
            resources = [image for image in resources if not image.deprecation_time]

        filtered = apply_filters(resources, params.get("Filter.N", []))
        images = [image.to_dict() for image in filtered]

        return {
            'imagesSet': images,
            'nextToken': None,
            }

    def DescribeImageUsageReportEntries(self, params: Dict[str, Any]):
        """Describes the entries in image usage reports, showing how your images are used across
      other AWS accounts. For more information, seeView your AMI usagein theAmazon EC2 User Guide."""

        report_ids = params.get("ReportId.N", []) or []
        image_ids = params.get("ImageId.N", []) or []

        if report_ids and hasattr(self.state, "image_usage_reports"):
            for report_id in report_ids:
                if report_id not in self.state.image_usage_reports:
                    return create_error_response("InvalidReportId.NotFound", f"The ID '{report_id}' does not exist")

        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error

        entries = []
        if hasattr(self.state, "image_usage_report_entries"):
            for report_id, report_entries in self.state.image_usage_report_entries.items():
                if report_ids and report_id not in report_ids:
                    continue
                for entry in report_entries:
                    if image_ids and entry.get("imageId") not in image_ids:
                        continue
                    entries.append(entry)

        filtered = apply_filters(entries, params.get("Filter.N", []))

        return {
            'imageUsageReportEntrySet': filtered,
            'nextToken': None,
            }

    def DescribeImageUsageReports(self, params: Dict[str, Any]):
        """Describes the configuration and status of image usage reports, filtered by report IDs or
      image IDs. For more information, seeView your AMI usagein theAmazon EC2 User Guide."""

        report_ids = params.get("ReportId.N", []) or []
        image_ids = params.get("ImageId.N", []) or []

        if report_ids and hasattr(self.state, "image_usage_reports"):
            for report_id in report_ids:
                if report_id not in self.state.image_usage_reports:
                    return create_error_response("InvalidReportId.NotFound", f"The ID '{report_id}' does not exist")

        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error

        reports = []
        if hasattr(self.state, "image_usage_reports"):
            for report in self.state.image_usage_reports.values():
                if report_ids and report.get("reportId") not in report_ids:
                    continue
                if image_ids and report.get("imageId") not in image_ids:
                    continue
                reports.append(report)

        filtered = apply_filters(reports, params.get("Filter.N", []))

        return {
            'imageUsageReportSet': filtered,
            'nextToken': None,
            }

    def DescribeInstanceImageMetadata(self, params: Dict[str, Any]):
        """Describes the AMI that was used to launch an instance, even if the AMI is deprecated,
      deregistered, made private (no longer public or shared with your account), or not
      allowed. If you specify instance IDs, the output includes information for only the specified
      instances. If you spe"""

        instance_ids = params.get("InstanceId.N", []) or []
        if instance_ids:
            instances, error = self._get_resources_by_ids(self.state.instances, instance_ids, "InvalidInstanceID.NotFound")
            if error:
                return error
        else:
            instances = list(self.state.instances.values())

        metadata = []
        for instance in instances:
            image_id = getattr(instance, "image_id", "") or getattr(instance, "imageId", "")
            image = self.resources.get(image_id)
            image_metadata = image.to_dict() if image else {}
            metadata.append({
                "availabilityZone": getattr(instance, "availability_zone", ""),
                "imageMetadata": image_metadata,
                "instanceId": getattr(instance, "instance_id", "") or getattr(instance, "instanceId", ""),
                "instanceOwnerId": getattr(instance, "owner_id", ""),
                "instanceState": getattr(instance, "instance_state", {}),
                "instanceType": getattr(instance, "instance_type", ""),
                "launchTime": getattr(instance, "launch_time", ""),
                "operator": getattr(instance, "operator", ""),
                "tagSet": getattr(instance, "tag_set", []),
                "zoneId": getattr(instance, "zone_id", ""),
            })

        filtered = apply_filters(metadata, params.get("Filter.N", []))

        return {
            'instanceImageMetadataSet': filtered,
            'nextToken': None,
            }

    def DescribeStoreImageTasks(self, params: Dict[str, Any]):
        """Describes the progress of the AMI store tasks. You can describe the store tasks for
      specified AMIs. If you don't specify the AMIs, you get a paginated list of store tasks from
      the last 31 days. For each AMI task, the response indicates if the task isInProgress,Completed, orFailed. For ta"""

        image_ids = params.get("ImageId.N", []) or []
        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error

        tasks = []
        if hasattr(self.state, "store_image_tasks"):
            if image_ids:
                for image_id in image_ids:
                    tasks.extend(self.state.store_image_tasks.get(image_id, []))
            else:
                for task_list in self.state.store_image_tasks.values():
                    tasks.extend(task_list)

        filtered = apply_filters(tasks, params.get("Filter.N", []))

        return {
            'nextToken': None,
            'storeImageTaskResultSet': filtered,
            }

    def DisableAllowedImagesSettings(self, params: Dict[str, Any]):
        """Disables Allowed AMIs for your account in the specified AWS Region. When set todisabled, the image criteria in your Allowed AMIs settings do not apply, and no
      restrictions are placed on AMI discoverability or usage. Users in your account can launch
      instances using any public AMI or AMI s"""

        if not hasattr(self.state, "allowed_images_settings"):
            setattr(self.state, "allowed_images_settings", {
                "state": "disabled",
                "managedBy": "account",
                "imageCriterionSet": [],
            })
        else:
            self.state.allowed_images_settings["state"] = "disabled"

        return {
            'allowedImagesSettingsState': self.state.allowed_images_settings.get("state"),
            }

    def DisableFastLaunch(self, params: Dict[str, Any]):
        """Discontinue Windows fast launch for a Windows AMI, and clean up existing pre-provisioned
      snapshots. After you disable Windows fast launch, the AMI uses the standard launch process for
      each new instance. Amazon EC2 must remove all pre-provisioned snapshots before you can enable
      Wind"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        self._set_fast_launch_state(image, "disabled", "fast-launch disabled")

        return {
            'imageId': image.image_id,
            'launchTemplate': image.launch_template or {
                'launchTemplateId': None,
                'launchTemplateName': None,
                'version': None,
            },
            'maxParallelLaunches': image.max_parallel_launches,
            'ownerId': image.owner_id,
            'resourceType': image.resource_type,
            'snapshotConfiguration': image.snapshot_configuration or {
                'targetResourceCount': None,
            },
            'state': image.state,
            'stateTransitionReason': image.state_transition_reason,
            'stateTransitionTime': image.state_transition_time,
            }

    def DisableImage(self, params: Dict[str, Any]):
        """Sets the AMI state todisabledand removes all launch permissions from the
      AMI. A disabled AMI can't be used for instance launches. A disabled AMI can't be shared. If an AMI was public or previously shared, it is made
      private. If an AMI was shared with an AWS account, organization, or Orga"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.state = "disabled"
        image.launch_permissions = []
        image.is_public = False

        return {
            'return': True,
            }

    def DisableImageBlockPublicAccess(self, params: Dict[str, Any]):
        """Disablesblock public access for AMIsat the account level in the
      specified AWS Region. This removes theblock public accessrestriction
      from your account. With the restriction removed, you can publicly share your AMIs in the
      specified AWS Region. For more information, seeBlock
      p"""

        if not hasattr(self.state, "image_block_public_access"):
            setattr(self.state, "image_block_public_access", {
                "state": "unblocked",
                "managedBy": "account",
            })
        else:
            self.state.image_block_public_access["state"] = "unblocked"

        return {
            'imageBlockPublicAccessState': self.state.image_block_public_access.get("state"),
            }

    def DisableImageDeprecation(self, params: Dict[str, Any]):
        """Cancels the deprecation of the specified AMI. For more information, seeDeprecate an Amazon EC2 AMIin theAmazon EC2 User Guide."""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.deprecation_time = ""

        return {
            'return': True,
            }

    def DisableImageDeregistrationProtection(self, params: Dict[str, Any]):
        """Disables deregistration protection for an AMI. When deregistration protection is disabled,
      the AMI can be deregistered. If you chose to include a 24-hour cooldown period when you enabled deregistration
      protection for the AMI, then, when you disable deregistration protection, you wonât
"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.deregistration_protection = False

        return {
            'return': True,
            }

    def EnableAllowedImagesSettings(self, params: Dict[str, Any]):
        """Enables Allowed AMIs for your account in the specified AWS Region. Two values are
      accepted: enabled: The image criteria in your Allowed AMIs settings are applied. As
          a result, only AMIs matching these criteria are discoverable and can be used by your
          account to launch insta"""

        error = self._require_params(params, ["AllowedImagesSettingsState"])
        if error:
            return error

        if not hasattr(self.state, "allowed_images_settings"):
            setattr(self.state, "allowed_images_settings", {
                "state": params.get("AllowedImagesSettingsState"),
                "managedBy": "account",
                "imageCriterionSet": [],
            })
        else:
            self.state.allowed_images_settings["state"] = params.get("AllowedImagesSettingsState")

        return {
            'allowedImagesSettingsState': self.state.allowed_images_settings.get("state"),
            }

    def EnableFastLaunch(self, params: Dict[str, Any]):
        """When you enable Windows fast launch for a Windows AMI, images are pre-provisioned, using
      snapshots to launch instances up to 65% faster. To create the optimized Windows image, Amazon EC2
      launches an instance and runs through Sysprep steps, rebooting as required. Then it creates a
      s"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        if params.get("LaunchTemplate"):
            image.launch_template = params.get("LaunchTemplate")
        if params.get("MaxParallelLaunches") is not None:
            image.max_parallel_launches = int(params.get("MaxParallelLaunches") or 0)
        if params.get("ResourceType"):
            image.resource_type = params.get("ResourceType")
        if params.get("SnapshotConfiguration"):
            image.snapshot_configuration = params.get("SnapshotConfiguration")

        self._set_fast_launch_state(image, "enabled", "fast-launch enabled")

        return {
            'imageId': image.image_id,
            'launchTemplate': image.launch_template or {
                'launchTemplateId': None,
                'launchTemplateName': None,
                'version': None,
            },
            'maxParallelLaunches': image.max_parallel_launches,
            'ownerId': image.owner_id,
            'resourceType': image.resource_type,
            'snapshotConfiguration': image.snapshot_configuration or {
                'targetResourceCount': None,
            },
            'state': image.state,
            'stateTransitionReason': image.state_transition_reason,
            'stateTransitionTime': image.state_transition_time,
            }

    def EnableImage(self, params: Dict[str, Any]):
        """Re-enables a disabled AMI. The re-enabled AMI is marked asavailableand can
      be used for instance launches, appears in describe operations, and can be shared. AWS
      accounts, organizations, and Organizational Units that lost access to the AMI when it was
      disabled do not regain access a"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.state = "available"

        return {
            'return': True,
            }

    def EnableImageBlockPublicAccess(self, params: Dict[str, Any]):
        """Enablesblock public access for AMIsat the account level in the
      specified AWS Region. This prevents the public sharing of your AMIs. However, if you already
      have public AMIs, they will remain publicly available. The API can take up to 10 minutes to configure this setting. During this time"""

        error = self._require_params(params, ["ImageBlockPublicAccessState"])
        if error:
            return error

        state_value = params.get("ImageBlockPublicAccessState")
        if not hasattr(self.state, "image_block_public_access"):
            setattr(self.state, "image_block_public_access", {
                "state": state_value,
                "managedBy": "account",
            })
        else:
            self.state.image_block_public_access["state"] = state_value

        return {
            'imageBlockPublicAccessState': self.state.image_block_public_access.get("state"),
            }

    def EnableImageDeprecation(self, params: Dict[str, Any]):
        """Enables deprecation of the specified AMI at the specified date and time. For more information, seeDeprecate an AMIin theAmazon EC2 User Guide."""

        error = self._require_params(params, ["DeprecateAt", "ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.deprecation_time = params.get("DeprecateAt") or ""

        return {
            'return': True,
            }

    def EnableImageDeregistrationProtection(self, params: Dict[str, Any]):
        """Enables deregistration protection for an AMI. When deregistration protection is enabled,
      the AMI can't be deregistered. To allow the AMI to be deregistered, you must first disable deregistration protection. For more information, seeProtect an
      Amazon EC2 AMI from deregistrationin theAmazo"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        image.deregistration_protection = True

        return {
            'return': True,
            }

    def GetAllowedImagesSettings(self, params: Dict[str, Any]):
        """Gets the current state of the Allowed AMIs setting and the list of Allowed AMIs criteria
      at the account level in the specified Region. The Allowed AMIs feature does not restrict the AMIs owned by your account. Regardless of
        the criteria you set, the AMIs created by your account will al"""

        if not hasattr(self.state, "allowed_images_settings"):
            setattr(self.state, "allowed_images_settings", {
                "state": "disabled",
                "managedBy": "account",
                "imageCriterionSet": [],
            })

        settings = self.state.allowed_images_settings

        return {
            'imageCriterionSet': settings.get("imageCriterionSet", []),
            'managedBy': settings.get("managedBy"),
            'state': settings.get("state"),
            }

    def GetImageAncestry(self, params: Dict[str, Any]):
        """Retrieves the ancestry chain of the specified AMI, tracing its lineage back to the root
      AMI. For more information, seeAMI ancestryinAmazon EC2 User Guide."""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        ancestry = []
        current = image
        while current:
            ancestry.append({
                "creationDate": current.creation_date,
                "imageId": current.image_id,
                "imageOwnerAlias": current.image_owner_alias,
                "sourceImageId": current.source_image_id,
                "sourceImageRegion": current.source_image_region,
            })
            if not current.source_image_id:
                break
            current = self.resources.get(current.source_image_id)

        return {
            'imageAncestryEntrySet': ancestry,
            }

    def GetImageBlockPublicAccessState(self, params: Dict[str, Any]):
        """Gets the current state ofblock public access for AMIsat the account
      level in the specified AWS Region. For more information, seeBlock
      public access to your AMIsin theAmazon EC2 User Guide."""

        if not hasattr(self.state, "image_block_public_access"):
            setattr(self.state, "image_block_public_access", {
                "state": "unblocked",
                "managedBy": "account",
            })

        settings = self.state.image_block_public_access

        return {
            'imageBlockPublicAccessState': settings.get("state"),
            'managedBy': settings.get("managedBy"),
            }

    def ModifyImageAttribute(self, params: Dict[str, Any]):
        """Modifies the specified attribute of the specified AMI. You can specify only one attribute
      at a time. To specify the attribute, you can use theAttributeparameter, or one of the
      following parameters:Description,ImdsSupport, orLaunchPermission. Images with an AWS Marketplace product code ca"""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or ""
        value = params.get("Value")
        operation = params.get("OperationType") or ""

        if params.get("Description") is not None or attribute == "description":
            description = params.get("Description")
            image.description = description.get("Value") if isinstance(description, dict) else (description or value or "")
        elif params.get("ImdsSupport") is not None or attribute == "imdsSupport":
            imds_support = params.get("ImdsSupport")
            image.imds_support = imds_support.get("Value") if isinstance(imds_support, dict) else (imds_support or value or "")
        elif params.get("LaunchPermission") is not None or attribute == "launchPermission":
            if operation.lower() == "add":
                image.launch_permissions.extend(params.get("LaunchPermission") or [])
                image.launch_permissions.extend([{"UserId": uid} for uid in params.get("UserId.N", [])])
            elif operation.lower() == "remove":
                to_remove = {perm.get("UserId") for perm in (params.get("LaunchPermission") or [])}
                to_remove.update(params.get("UserId.N", []) or [])
                image.launch_permissions = [perm for perm in image.launch_permissions if perm.get("UserId") not in to_remove]
            else:
                image.launch_permissions = params.get("LaunchPermission") or image.launch_permissions
        elif attribute == "productCodes":
            product_codes = params.get("ProductCode.N", []) or []
            if operation.lower() == "add":
                image.product_codes.extend(product_codes)
            elif operation.lower() == "remove":
                image.product_codes = [code for code in image.product_codes if code not in product_codes]
            else:
                image.product_codes = product_codes
        elif attribute == "bootMode":
            image.boot_mode = value or image.boot_mode
        elif attribute == "sriovNetSupport":
            image.sriov_net_support = value or image.sriov_net_support
        elif attribute == "tpmSupport":
            image.tpm_support = value or image.tpm_support
        elif attribute == "uefiData":
            image.uefi_data = value or image.uefi_data
        elif attribute == "kernel":
            image.kernel_id = value or image.kernel_id
        elif attribute == "ramdisk":
            image.ramdisk_id = value or image.ramdisk_id

        return {
            'return': True,
            }

    def RegisterImage(self, params: Dict[str, Any]):
        """Registers an AMI. When you're creating an instance-store backed AMI, registering the AMI
      is the final step in the creation process. For more information about creating AMIs, seeCreate an AMI from a snapshotandCreate an instance-store
        backed AMIin theAmazon EC2 User Guide. For Amazon EB"""

        error = self._require_params(params, ["Name"])
        if error:
            return error

        image_id = self._generate_id("ami")
        now = self._utc_now()
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        resource = Ami(
            image_id=image_id,
            name=params.get("Name") or "",
            description=params.get("Description") or "",
            architecture=params.get("Architecture") or "",
            boot_mode=params.get("BootMode") or "",
            ena_support=str2bool(params.get("EnaSupport")),
            image_location=params.get("ImageLocation") or "",
            imds_support=params.get("ImdsSupport") or "",
            kernel_id=params.get("KernelId") or "",
            ramdisk_id=params.get("RamdiskId") or "",
            root_device_name=params.get("RootDeviceName") or "",
            sriov_net_support=params.get("SriovNetSupport") or "",
            tpm_support=params.get("TpmSupport") or "",
            uefi_data=params.get("UefiData") or "",
            virtualization_type=params.get("VirtualizationType") or "",
            image_state="available",
            image_type="machine",
            root_device_type="ebs",
            creation_date=now,
            state="available",
            state_transition_reason="registered",
            state_transition_time=now,
            block_device_mappings=params.get("BlockDeviceMapping.N", []) or [],
            product_codes=params.get("BillingProduct.N", []) or [],
            tag_set=tag_set,
        )
        self.resources[image_id] = resource

        return {
            'imageId': image_id,
            }

    def ReplaceImageCriteriaInAllowedImagesSettings(self, params: Dict[str, Any]):
        """Sets or replaces the criteria for Allowed AMIs. The Allowed AMIs feature does not restrict the AMIs owned by your account. Regardless of
        the criteria you set, the AMIs created by your account will always be discoverable and
        usable by users in your account. For more information, seeCo"""

        if not hasattr(self.state, "allowed_images_settings"):
            setattr(self.state, "allowed_images_settings", {
                "state": "disabled",
                "managedBy": "account",
                "imageCriterionSet": [],
            })

        self.state.allowed_images_settings["imageCriterionSet"] = params.get("ImageCriterion.N", []) or []

        return {
            'return': True,
            }

    def ResetImageAttribute(self, params: Dict[str, Any]):
        """Resets an attribute of an AMI to its default value."""

        error = self._require_params(params, ["Attribute", "ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or ""
        if attribute in ("launchPermission", "launch-permission"):
            image.launch_permissions = []
        elif attribute == "productCodes":
            image.product_codes = []
        elif attribute == "description":
            image.description = ""
        elif attribute == "imdsSupport":
            image.imds_support = ""
        elif attribute == "bootMode":
            image.boot_mode = ""
        elif attribute == "tpmSupport":
            image.tpm_support = ""
        elif attribute == "sriovNetSupport":
            image.sriov_net_support = ""
        elif attribute == "uefiData":
            image.uefi_data = ""

        return {
            'return': True,
            }

    def ListImagesInRecycleBin(self, params: Dict[str, Any]):
        """Lists one or more AMIs that are currently in the Recycle Bin. For more information, seeRecycle
        Binin theAmazon EC2 User Guide."""

        image_ids = params.get("ImageId.N", []) or []
        if image_ids:
            resources, error = self._get_resources_by_ids(self.resources, image_ids, "InvalidAMIID.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        images = []
        for image in resources:
            if not image.in_recycle_bin:
                continue
            images.append({
                "description": image.description,
                "imageId": image.image_id,
                "name": image.name,
                "recycleBinEnterTime": image.recycle_bin_enter_time,
                "recycleBinExitTime": image.recycle_bin_exit_time,
            })

        return {
            'imageSet': images,
            'nextToken': None,
            }

    def RestoreImageFromRecycleBin(self, params: Dict[str, Any]):
        """Restores an AMI from the Recycle Bin. For more information, seeRecover deleted Amazon EBS
        snapshots and EBS-back AMIs with Recycle Binin theAmazon EC2 User Guide."""

        error = self._require_params(params, ["ImageId"])
        if error:
            return error

        image_id = params.get("ImageId")
        image, error = self._get_ami_or_error(image_id, "InvalidAMIID.NotFound")
        if error:
            return error

        if not image.in_recycle_bin:
            return create_error_response("InvalidAMIID.NotFound", f"The ID '{image_id}' does not exist")

        image.in_recycle_bin = False
        image.recycle_bin_exit_time = self._utc_now()
        image.image_state = "available"

        return {
            'return': True,
            }

    def _generate_id(self, prefix: str = 'ami') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class ami_RequestParser:
    @staticmethod
    def parse_cancel_image_launch_permission_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_copy_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ClientToken": get_scalar(md, "ClientToken"),
            "CopyImageTags": get_scalar(md, "CopyImageTags"),
            "Description": get_scalar(md, "Description"),
            "DestinationAvailabilityZone": get_scalar(md, "DestinationAvailabilityZone"),
            "DestinationAvailabilityZoneId": get_scalar(md, "DestinationAvailabilityZoneId"),
            "DestinationOutpostArn": get_scalar(md, "DestinationOutpostArn"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Encrypted": get_scalar(md, "Encrypted"),
            "KmsKeyId": get_scalar(md, "KmsKeyId"),
            "Name": get_scalar(md, "Name"),
            "SnapshotCopyCompletionDurationMinutes": get_int(md, "SnapshotCopyCompletionDurationMinutes"),
            "SourceImageId": get_scalar(md, "SourceImageId"),
            "SourceRegion": get_scalar(md, "SourceRegion"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "BlockDeviceMapping.N": get_indexed_list(md, "BlockDeviceMapping"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InstanceId": get_scalar(md, "InstanceId"),
            "Name": get_scalar(md, "Name"),
            "NoReboot": get_scalar(md, "NoReboot"),
            "SnapshotLocation": get_scalar(md, "SnapshotLocation"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_image_usage_report_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AccountId.N": get_indexed_list(md, "AccountId"),
            "ClientToken": get_scalar(md, "ClientToken"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
            "ResourceType.N": get_indexed_list(md, "ResourceType"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_restore_image_task_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Bucket": get_scalar(md, "Bucket"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Name": get_scalar(md, "Name"),
            "ObjectKey": get_scalar(md, "ObjectKey"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_store_image_task_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Bucket": get_scalar(md, "Bucket"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
            "S3ObjectTag.N": get_indexed_list(md, "S3ObjectTag"),
        }

    @staticmethod
    def parse_delete_image_usage_report_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ReportId": get_scalar(md, "ReportId"),
        }

    @staticmethod
    def parse_deregister_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DeleteAssociatedSnapshots": get_scalar(md, "DeleteAssociatedSnapshots"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_describe_fast_launch_images_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_image_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_describe_image_references_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "IncludeAllResourceTypes": get_scalar(md, "IncludeAllResourceTypes"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "ResourceType.N": get_indexed_list(md, "ResourceType"),
        }

    @staticmethod
    def parse_describe_images_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ExecutableBy.N": get_indexed_list(md, "ExecutableBy"),
            "Filter.N": parse_filters(md, "Filter"),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "IncludeDeprecated": get_scalar(md, "IncludeDeprecated"),
            "IncludeDisabled": get_scalar(md, "IncludeDisabled"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "Owner.N": get_indexed_list(md, "Owner"),
        }

    @staticmethod
    def parse_describe_image_usage_report_entries_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "ReportId.N": get_indexed_list(md, "ReportId"),
        }

    @staticmethod
    def parse_describe_image_usage_reports_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "ReportId.N": get_indexed_list(md, "ReportId"),
        }

    @staticmethod
    def parse_describe_instance_image_metadata_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "InstanceId.N": get_indexed_list(md, "InstanceId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_describe_store_image_tasks_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_disable_allowed_images_settings_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_disable_fast_launch_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Force": get_scalar(md, "Force"),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_disable_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_disable_image_block_public_access_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_disable_image_deprecation_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_disable_image_deregistration_protection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_enable_allowed_images_settings_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "AllowedImagesSettingsState": get_scalar(md, "AllowedImagesSettingsState"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_enable_fast_launch_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
            "LaunchTemplate": get_scalar(md, "LaunchTemplate"),
            "MaxParallelLaunches": get_int(md, "MaxParallelLaunches"),
            "ResourceType": get_scalar(md, "ResourceType"),
            "SnapshotConfiguration": get_scalar(md, "SnapshotConfiguration"),
        }

    @staticmethod
    def parse_enable_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_enable_image_block_public_access_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageBlockPublicAccessState": get_scalar(md, "ImageBlockPublicAccessState"),
        }

    @staticmethod
    def parse_enable_image_deprecation_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DeprecateAt": get_scalar(md, "DeprecateAt"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_enable_image_deregistration_protection_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
            "WithCooldown": get_scalar(md, "WithCooldown"),
        }

    @staticmethod
    def parse_get_allowed_images_settings_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_get_image_ancestry_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_get_image_block_public_access_state_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_modify_image_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
            "ImdsSupport": get_scalar(md, "ImdsSupport"),
            "LaunchPermission": get_scalar(md, "LaunchPermission"),
            "OperationType": get_scalar(md, "OperationType"),
            "OrganizationalUnitArn.N": get_indexed_list(md, "OrganizationalUnitArn"),
            "OrganizationArn.N": get_indexed_list(md, "OrganizationArn"),
            "ProductCode.N": get_indexed_list(md, "ProductCode"),
            "UserGroup.N": get_indexed_list(md, "UserGroup"),
            "UserId.N": get_indexed_list(md, "UserId"),
            "Value": get_scalar(md, "Value"),
        }

    @staticmethod
    def parse_register_image_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Architecture": get_scalar(md, "Architecture"),
            "BillingProduct.N": get_indexed_list(md, "BillingProduct"),
            "BlockDeviceMapping.N": get_indexed_list(md, "BlockDeviceMapping"),
            "BootMode": get_scalar(md, "BootMode"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "EnaSupport": get_scalar(md, "EnaSupport"),
            "ImageLocation": get_scalar(md, "ImageLocation"),
            "ImdsSupport": get_scalar(md, "ImdsSupport"),
            "KernelId": get_scalar(md, "KernelId"),
            "Name": get_scalar(md, "Name"),
            "RamdiskId": get_scalar(md, "RamdiskId"),
            "RootDeviceName": get_scalar(md, "RootDeviceName"),
            "SriovNetSupport": get_scalar(md, "SriovNetSupport"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "TpmSupport": get_scalar(md, "TpmSupport"),
            "UefiData": get_scalar(md, "UefiData"),
            "VirtualizationType": get_scalar(md, "VirtualizationType"),
        }

    @staticmethod
    def parse_replace_image_criteria_in_allowed_images_settings_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageCriterion.N": get_indexed_list(md, "ImageCriterion"),
        }

    @staticmethod
    def parse_reset_image_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_list_images_in_recycle_bin_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId.N": get_indexed_list(md, "ImageId"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_restore_image_from_recycle_bin_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ImageId": get_scalar(md, "ImageId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "CancelImageLaunchPermission": ami_RequestParser.parse_cancel_image_launch_permission_request,
            "CopyImage": ami_RequestParser.parse_copy_image_request,
            "CreateImage": ami_RequestParser.parse_create_image_request,
            "CreateImageUsageReport": ami_RequestParser.parse_create_image_usage_report_request,
            "CreateRestoreImageTask": ami_RequestParser.parse_create_restore_image_task_request,
            "CreateStoreImageTask": ami_RequestParser.parse_create_store_image_task_request,
            "DeleteImageUsageReport": ami_RequestParser.parse_delete_image_usage_report_request,
            "DeregisterImage": ami_RequestParser.parse_deregister_image_request,
            "DescribeFastLaunchImages": ami_RequestParser.parse_describe_fast_launch_images_request,
            "DescribeImageAttribute": ami_RequestParser.parse_describe_image_attribute_request,
            "DescribeImageReferences": ami_RequestParser.parse_describe_image_references_request,
            "DescribeImages": ami_RequestParser.parse_describe_images_request,
            "DescribeImageUsageReportEntries": ami_RequestParser.parse_describe_image_usage_report_entries_request,
            "DescribeImageUsageReports": ami_RequestParser.parse_describe_image_usage_reports_request,
            "DescribeInstanceImageMetadata": ami_RequestParser.parse_describe_instance_image_metadata_request,
            "DescribeStoreImageTasks": ami_RequestParser.parse_describe_store_image_tasks_request,
            "DisableAllowedImagesSettings": ami_RequestParser.parse_disable_allowed_images_settings_request,
            "DisableFastLaunch": ami_RequestParser.parse_disable_fast_launch_request,
            "DisableImage": ami_RequestParser.parse_disable_image_request,
            "DisableImageBlockPublicAccess": ami_RequestParser.parse_disable_image_block_public_access_request,
            "DisableImageDeprecation": ami_RequestParser.parse_disable_image_deprecation_request,
            "DisableImageDeregistrationProtection": ami_RequestParser.parse_disable_image_deregistration_protection_request,
            "EnableAllowedImagesSettings": ami_RequestParser.parse_enable_allowed_images_settings_request,
            "EnableFastLaunch": ami_RequestParser.parse_enable_fast_launch_request,
            "EnableImage": ami_RequestParser.parse_enable_image_request,
            "EnableImageBlockPublicAccess": ami_RequestParser.parse_enable_image_block_public_access_request,
            "EnableImageDeprecation": ami_RequestParser.parse_enable_image_deprecation_request,
            "EnableImageDeregistrationProtection": ami_RequestParser.parse_enable_image_deregistration_protection_request,
            "GetAllowedImagesSettings": ami_RequestParser.parse_get_allowed_images_settings_request,
            "GetImageAncestry": ami_RequestParser.parse_get_image_ancestry_request,
            "GetImageBlockPublicAccessState": ami_RequestParser.parse_get_image_block_public_access_state_request,
            "ModifyImageAttribute": ami_RequestParser.parse_modify_image_attribute_request,
            "RegisterImage": ami_RequestParser.parse_register_image_request,
            "ReplaceImageCriteriaInAllowedImagesSettings": ami_RequestParser.parse_replace_image_criteria_in_allowed_images_settings_request,
            "ResetImageAttribute": ami_RequestParser.parse_reset_image_attribute_request,
            "ListImagesInRecycleBin": ami_RequestParser.parse_list_images_in_recycle_bin_request,
            "RestoreImageFromRecycleBin": ami_RequestParser.parse_restore_image_from_recycle_bin_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class ami_ResponseSerializer:
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
                xml_parts.extend(ami_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(ami_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(ami_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(ami_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_cancel_image_launch_permission_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CancelImageLaunchPermissionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</CancelImageLaunchPermissionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_copy_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CopyImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
        xml_parts.append(f'</CopyImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
        xml_parts.append(f'</CreateImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_image_usage_report_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateImageUsageReportResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize reportId
        _reportId_key = None
        if "reportId" in data:
            _reportId_key = "reportId"
        elif "ReportId" in data:
            _reportId_key = "ReportId"
        if _reportId_key:
            param_data = data[_reportId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<reportId>{esc(str(param_data))}</reportId>')
        xml_parts.append(f'</CreateImageUsageReportResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_restore_image_task_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateRestoreImageTaskResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
        xml_parts.append(f'</CreateRestoreImageTaskResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_store_image_task_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateStoreImageTaskResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize objectKey
        _objectKey_key = None
        if "objectKey" in data:
            _objectKey_key = "objectKey"
        elif "ObjectKey" in data:
            _objectKey_key = "ObjectKey"
        if _objectKey_key:
            param_data = data[_objectKey_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<objectKey>{esc(str(param_data))}</objectKey>')
        xml_parts.append(f'</CreateStoreImageTaskResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_image_usage_report_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteImageUsageReportResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteImageUsageReportResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_deregister_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize deleteSnapshotResultSet
        _deleteSnapshotResultSet_key = None
        if "deleteSnapshotResultSet" in data:
            _deleteSnapshotResultSet_key = "deleteSnapshotResultSet"
        elif "DeleteSnapshotResultSet" in data:
            _deleteSnapshotResultSet_key = "DeleteSnapshotResultSet"
        elif "DeleteSnapshotResults" in data:
            _deleteSnapshotResultSet_key = "DeleteSnapshotResults"
        if _deleteSnapshotResultSet_key:
            param_data = data[_deleteSnapshotResultSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<deleteSnapshotResultSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</deleteSnapshotResultSet>')
            else:
                xml_parts.append(f'{indent_str}<deleteSnapshotResultSet/>')
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
        xml_parts.append(f'</DeregisterImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_fast_launch_images_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeFastLaunchImagesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize fastLaunchImageSet
        _fastLaunchImageSet_key = None
        if "fastLaunchImageSet" in data:
            _fastLaunchImageSet_key = "fastLaunchImageSet"
        elif "FastLaunchImageSet" in data:
            _fastLaunchImageSet_key = "FastLaunchImageSet"
        elif "FastLaunchImages" in data:
            _fastLaunchImageSet_key = "FastLaunchImages"
        if _fastLaunchImageSet_key:
            param_data = data[_fastLaunchImageSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<fastLaunchImageSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</fastLaunchImageSet>')
            else:
                xml_parts.append(f'{indent_str}<fastLaunchImageSet/>')
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
        xml_parts.append(f'</DescribeFastLaunchImagesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_image_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize blockDeviceMapping
        _blockDeviceMapping_key = None
        if "blockDeviceMapping" in data:
            _blockDeviceMapping_key = "blockDeviceMapping"
        elif "BlockDeviceMapping" in data:
            _blockDeviceMapping_key = "BlockDeviceMapping"
        if _blockDeviceMapping_key:
            param_data = data[_blockDeviceMapping_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<blockDeviceMappingSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</blockDeviceMappingSet>')
            else:
                xml_parts.append(f'{indent_str}<blockDeviceMappingSet/>')
        # Serialize bootMode
        _bootMode_key = None
        if "bootMode" in data:
            _bootMode_key = "bootMode"
        elif "BootMode" in data:
            _bootMode_key = "BootMode"
        if _bootMode_key:
            param_data = data[_bootMode_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<bootMode>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</bootMode>')
        # Serialize deregistrationProtection
        _deregistrationProtection_key = None
        if "deregistrationProtection" in data:
            _deregistrationProtection_key = "deregistrationProtection"
        elif "DeregistrationProtection" in data:
            _deregistrationProtection_key = "DeregistrationProtection"
        if _deregistrationProtection_key:
            param_data = data[_deregistrationProtection_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<deregistrationProtection>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</deregistrationProtection>')
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
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</description>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
        # Serialize imdsSupport
        _imdsSupport_key = None
        if "imdsSupport" in data:
            _imdsSupport_key = "imdsSupport"
        elif "ImdsSupport" in data:
            _imdsSupport_key = "ImdsSupport"
        if _imdsSupport_key:
            param_data = data[_imdsSupport_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imdsSupport>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</imdsSupport>')
        # Serialize kernel
        _kernel_key = None
        if "kernel" in data:
            _kernel_key = "kernel"
        elif "Kernel" in data:
            _kernel_key = "Kernel"
        if _kernel_key:
            param_data = data[_kernel_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<kernel>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</kernel>')
        # Serialize lastLaunchedTime
        _lastLaunchedTime_key = None
        if "lastLaunchedTime" in data:
            _lastLaunchedTime_key = "lastLaunchedTime"
        elif "LastLaunchedTime" in data:
            _lastLaunchedTime_key = "LastLaunchedTime"
        if _lastLaunchedTime_key:
            param_data = data[_lastLaunchedTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lastLaunchedTime>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</lastLaunchedTime>')
        # Serialize launchPermission
        _launchPermission_key = None
        if "launchPermission" in data:
            _launchPermission_key = "launchPermission"
        elif "LaunchPermission" in data:
            _launchPermission_key = "LaunchPermission"
        if _launchPermission_key:
            param_data = data[_launchPermission_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<launchPermissionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</launchPermissionSet>')
            else:
                xml_parts.append(f'{indent_str}<launchPermissionSet/>')
        # Serialize productCodes
        _productCodes_key = None
        if "productCodes" in data:
            _productCodes_key = "productCodes"
        elif "ProductCodes" in data:
            _productCodes_key = "ProductCodes"
        if _productCodes_key:
            param_data = data[_productCodes_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<productCodesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</productCodesSet>')
            else:
                xml_parts.append(f'{indent_str}<productCodesSet/>')
        # Serialize ramdisk
        _ramdisk_key = None
        if "ramdisk" in data:
            _ramdisk_key = "ramdisk"
        elif "Ramdisk" in data:
            _ramdisk_key = "Ramdisk"
        if _ramdisk_key:
            param_data = data[_ramdisk_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<ramdisk>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</ramdisk>')
        # Serialize sriovNetSupport
        _sriovNetSupport_key = None
        if "sriovNetSupport" in data:
            _sriovNetSupport_key = "sriovNetSupport"
        elif "SriovNetSupport" in data:
            _sriovNetSupport_key = "SriovNetSupport"
        if _sriovNetSupport_key:
            param_data = data[_sriovNetSupport_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<sriovNetSupport>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</sriovNetSupport>')
        # Serialize tpmSupport
        _tpmSupport_key = None
        if "tpmSupport" in data:
            _tpmSupport_key = "tpmSupport"
        elif "TpmSupport" in data:
            _tpmSupport_key = "TpmSupport"
        if _tpmSupport_key:
            param_data = data[_tpmSupport_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<tpmSupport>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</tpmSupport>')
        # Serialize uefiData
        _uefiData_key = None
        if "uefiData" in data:
            _uefiData_key = "uefiData"
        elif "UefiData" in data:
            _uefiData_key = "UefiData"
        if _uefiData_key:
            param_data = data[_uefiData_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<uefiData>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</uefiData>')
        xml_parts.append(f'</DescribeImageAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_image_references_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeImageReferencesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageReferenceSet
        _imageReferenceSet_key = None
        if "imageReferenceSet" in data:
            _imageReferenceSet_key = "imageReferenceSet"
        elif "ImageReferenceSet" in data:
            _imageReferenceSet_key = "ImageReferenceSet"
        elif "ImageReferences" in data:
            _imageReferenceSet_key = "ImageReferences"
        if _imageReferenceSet_key:
            param_data = data[_imageReferenceSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageReferenceSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageReferenceSet>')
            else:
                xml_parts.append(f'{indent_str}<imageReferenceSet/>')
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
        xml_parts.append(f'</DescribeImageReferencesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_images_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imagesSet
        _imagesSet_key = None
        if "imagesSet" in data:
            _imagesSet_key = "imagesSet"
        elif "ImagesSet" in data:
            _imagesSet_key = "ImagesSet"
        elif "Imagess" in data:
            _imagesSet_key = "Imagess"
        if _imagesSet_key:
            param_data = data[_imagesSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imagesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imagesSet>')
            else:
                xml_parts.append(f'{indent_str}<imagesSet/>')
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
        xml_parts.append(f'</DescribeImagesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_image_usage_report_entries_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeImageUsageReportEntriesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageUsageReportEntrySet
        _imageUsageReportEntrySet_key = None
        if "imageUsageReportEntrySet" in data:
            _imageUsageReportEntrySet_key = "imageUsageReportEntrySet"
        elif "ImageUsageReportEntrySet" in data:
            _imageUsageReportEntrySet_key = "ImageUsageReportEntrySet"
        elif "ImageUsageReportEntrys" in data:
            _imageUsageReportEntrySet_key = "ImageUsageReportEntrys"
        if _imageUsageReportEntrySet_key:
            param_data = data[_imageUsageReportEntrySet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageUsageReportEntrySet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageUsageReportEntrySet>')
            else:
                xml_parts.append(f'{indent_str}<imageUsageReportEntrySet/>')
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
        xml_parts.append(f'</DescribeImageUsageReportEntriesResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_image_usage_reports_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeImageUsageReportsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageUsageReportSet
        _imageUsageReportSet_key = None
        if "imageUsageReportSet" in data:
            _imageUsageReportSet_key = "imageUsageReportSet"
        elif "ImageUsageReportSet" in data:
            _imageUsageReportSet_key = "ImageUsageReportSet"
        elif "ImageUsageReports" in data:
            _imageUsageReportSet_key = "ImageUsageReports"
        if _imageUsageReportSet_key:
            param_data = data[_imageUsageReportSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageUsageReportSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageUsageReportSet>')
            else:
                xml_parts.append(f'{indent_str}<imageUsageReportSet/>')
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
        xml_parts.append(f'</DescribeImageUsageReportsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_instance_image_metadata_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeInstanceImageMetadataResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize instanceImageMetadataSet
        _instanceImageMetadataSet_key = None
        if "instanceImageMetadataSet" in data:
            _instanceImageMetadataSet_key = "instanceImageMetadataSet"
        elif "InstanceImageMetadataSet" in data:
            _instanceImageMetadataSet_key = "InstanceImageMetadataSet"
        elif "InstanceImageMetadatas" in data:
            _instanceImageMetadataSet_key = "InstanceImageMetadatas"
        if _instanceImageMetadataSet_key:
            param_data = data[_instanceImageMetadataSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<instanceImageMetadataSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</instanceImageMetadataSet>')
            else:
                xml_parts.append(f'{indent_str}<instanceImageMetadataSet/>')
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
        xml_parts.append(f'</DescribeInstanceImageMetadataResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_store_image_tasks_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeStoreImageTasksResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize storeImageTaskResultSet
        _storeImageTaskResultSet_key = None
        if "storeImageTaskResultSet" in data:
            _storeImageTaskResultSet_key = "storeImageTaskResultSet"
        elif "StoreImageTaskResultSet" in data:
            _storeImageTaskResultSet_key = "StoreImageTaskResultSet"
        elif "StoreImageTaskResults" in data:
            _storeImageTaskResultSet_key = "StoreImageTaskResults"
        if _storeImageTaskResultSet_key:
            param_data = data[_storeImageTaskResultSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<storeImageTaskResultSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</storeImageTaskResultSet>')
            else:
                xml_parts.append(f'{indent_str}<storeImageTaskResultSet/>')
        xml_parts.append(f'</DescribeStoreImageTasksResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_allowed_images_settings_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableAllowedImagesSettingsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize allowedImagesSettingsState
        _allowedImagesSettingsState_key = None
        if "allowedImagesSettingsState" in data:
            _allowedImagesSettingsState_key = "allowedImagesSettingsState"
        elif "AllowedImagesSettingsState" in data:
            _allowedImagesSettingsState_key = "AllowedImagesSettingsState"
        if _allowedImagesSettingsState_key:
            param_data = data[_allowedImagesSettingsState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<allowedImagesSettingsState>{esc(str(param_data))}</allowedImagesSettingsState>')
        xml_parts.append(f'</DisableAllowedImagesSettingsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_fast_launch_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableFastLaunchResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
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
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplate>')
        # Serialize maxParallelLaunches
        _maxParallelLaunches_key = None
        if "maxParallelLaunches" in data:
            _maxParallelLaunches_key = "maxParallelLaunches"
        elif "MaxParallelLaunches" in data:
            _maxParallelLaunches_key = "MaxParallelLaunches"
        if _maxParallelLaunches_key:
            param_data = data[_maxParallelLaunches_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<maxParallelLaunchesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</maxParallelLaunchesSet>')
            else:
                xml_parts.append(f'{indent_str}<maxParallelLaunchesSet/>')
        # Serialize ownerId
        _ownerId_key = None
        if "ownerId" in data:
            _ownerId_key = "ownerId"
        elif "OwnerId" in data:
            _ownerId_key = "OwnerId"
        if _ownerId_key:
            param_data = data[_ownerId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<ownerId>{esc(str(param_data))}</ownerId>')
        # Serialize resourceType
        _resourceType_key = None
        if "resourceType" in data:
            _resourceType_key = "resourceType"
        elif "ResourceType" in data:
            _resourceType_key = "ResourceType"
        if _resourceType_key:
            param_data = data[_resourceType_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<resourceType>{esc(str(param_data))}</resourceType>')
        # Serialize snapshotConfiguration
        _snapshotConfiguration_key = None
        if "snapshotConfiguration" in data:
            _snapshotConfiguration_key = "snapshotConfiguration"
        elif "SnapshotConfiguration" in data:
            _snapshotConfiguration_key = "SnapshotConfiguration"
        if _snapshotConfiguration_key:
            param_data = data[_snapshotConfiguration_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotConfiguration>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</snapshotConfiguration>')
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
        # Serialize stateTransitionReason
        _stateTransitionReason_key = None
        if "stateTransitionReason" in data:
            _stateTransitionReason_key = "stateTransitionReason"
        elif "StateTransitionReason" in data:
            _stateTransitionReason_key = "StateTransitionReason"
        if _stateTransitionReason_key:
            param_data = data[_stateTransitionReason_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<stateTransitionReason>{esc(str(param_data))}</stateTransitionReason>')
        # Serialize stateTransitionTime
        _stateTransitionTime_key = None
        if "stateTransitionTime" in data:
            _stateTransitionTime_key = "stateTransitionTime"
        elif "StateTransitionTime" in data:
            _stateTransitionTime_key = "StateTransitionTime"
        if _stateTransitionTime_key:
            param_data = data[_stateTransitionTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<stateTransitionTime>{esc(str(param_data))}</stateTransitionTime>')
        xml_parts.append(f'</DisableFastLaunchResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DisableImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_image_block_public_access_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableImageBlockPublicAccessResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageBlockPublicAccessState
        _imageBlockPublicAccessState_key = None
        if "imageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "imageBlockPublicAccessState"
        elif "ImageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "ImageBlockPublicAccessState"
        if _imageBlockPublicAccessState_key:
            param_data = data[_imageBlockPublicAccessState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageBlockPublicAccessState>{esc(str(param_data))}</imageBlockPublicAccessState>')
        xml_parts.append(f'</DisableImageBlockPublicAccessResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_image_deprecation_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableImageDeprecationResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DisableImageDeprecationResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_image_deregistration_protection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableImageDeregistrationProtectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DisableImageDeregistrationProtectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_allowed_images_settings_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableAllowedImagesSettingsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize allowedImagesSettingsState
        _allowedImagesSettingsState_key = None
        if "allowedImagesSettingsState" in data:
            _allowedImagesSettingsState_key = "allowedImagesSettingsState"
        elif "AllowedImagesSettingsState" in data:
            _allowedImagesSettingsState_key = "AllowedImagesSettingsState"
        if _allowedImagesSettingsState_key:
            param_data = data[_allowedImagesSettingsState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<allowedImagesSettingsState>{esc(str(param_data))}</allowedImagesSettingsState>')
        xml_parts.append(f'</EnableAllowedImagesSettingsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_fast_launch_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableFastLaunchResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
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
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</launchTemplate>')
        # Serialize maxParallelLaunches
        _maxParallelLaunches_key = None
        if "maxParallelLaunches" in data:
            _maxParallelLaunches_key = "maxParallelLaunches"
        elif "MaxParallelLaunches" in data:
            _maxParallelLaunches_key = "MaxParallelLaunches"
        if _maxParallelLaunches_key:
            param_data = data[_maxParallelLaunches_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<maxParallelLaunchesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</maxParallelLaunchesSet>')
            else:
                xml_parts.append(f'{indent_str}<maxParallelLaunchesSet/>')
        # Serialize ownerId
        _ownerId_key = None
        if "ownerId" in data:
            _ownerId_key = "ownerId"
        elif "OwnerId" in data:
            _ownerId_key = "OwnerId"
        if _ownerId_key:
            param_data = data[_ownerId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<ownerId>{esc(str(param_data))}</ownerId>')
        # Serialize resourceType
        _resourceType_key = None
        if "resourceType" in data:
            _resourceType_key = "resourceType"
        elif "ResourceType" in data:
            _resourceType_key = "ResourceType"
        if _resourceType_key:
            param_data = data[_resourceType_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<resourceType>{esc(str(param_data))}</resourceType>')
        # Serialize snapshotConfiguration
        _snapshotConfiguration_key = None
        if "snapshotConfiguration" in data:
            _snapshotConfiguration_key = "snapshotConfiguration"
        elif "SnapshotConfiguration" in data:
            _snapshotConfiguration_key = "SnapshotConfiguration"
        if _snapshotConfiguration_key:
            param_data = data[_snapshotConfiguration_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotConfiguration>')
            xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(param_data, 2))
            xml_parts.append(f'{indent_str}</snapshotConfiguration>')
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
        # Serialize stateTransitionReason
        _stateTransitionReason_key = None
        if "stateTransitionReason" in data:
            _stateTransitionReason_key = "stateTransitionReason"
        elif "StateTransitionReason" in data:
            _stateTransitionReason_key = "StateTransitionReason"
        if _stateTransitionReason_key:
            param_data = data[_stateTransitionReason_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<stateTransitionReason>{esc(str(param_data))}</stateTransitionReason>')
        # Serialize stateTransitionTime
        _stateTransitionTime_key = None
        if "stateTransitionTime" in data:
            _stateTransitionTime_key = "stateTransitionTime"
        elif "StateTransitionTime" in data:
            _stateTransitionTime_key = "StateTransitionTime"
        if _stateTransitionTime_key:
            param_data = data[_stateTransitionTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<stateTransitionTime>{esc(str(param_data))}</stateTransitionTime>')
        xml_parts.append(f'</EnableFastLaunchResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</EnableImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_image_block_public_access_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableImageBlockPublicAccessResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageBlockPublicAccessState
        _imageBlockPublicAccessState_key = None
        if "imageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "imageBlockPublicAccessState"
        elif "ImageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "ImageBlockPublicAccessState"
        if _imageBlockPublicAccessState_key:
            param_data = data[_imageBlockPublicAccessState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageBlockPublicAccessState>{esc(str(param_data))}</imageBlockPublicAccessState>')
        xml_parts.append(f'</EnableImageBlockPublicAccessResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_image_deprecation_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableImageDeprecationResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</EnableImageDeprecationResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_image_deregistration_protection_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableImageDeregistrationProtectionResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</EnableImageDeregistrationProtectionResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_allowed_images_settings_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetAllowedImagesSettingsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageCriterionSet
        _imageCriterionSet_key = None
        if "imageCriterionSet" in data:
            _imageCriterionSet_key = "imageCriterionSet"
        elif "ImageCriterionSet" in data:
            _imageCriterionSet_key = "ImageCriterionSet"
        elif "ImageCriterions" in data:
            _imageCriterionSet_key = "ImageCriterions"
        if _imageCriterionSet_key:
            param_data = data[_imageCriterionSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageCriterionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageCriterionSet>')
            else:
                xml_parts.append(f'{indent_str}<imageCriterionSet/>')
        # Serialize managedBy
        _managedBy_key = None
        if "managedBy" in data:
            _managedBy_key = "managedBy"
        elif "ManagedBy" in data:
            _managedBy_key = "ManagedBy"
        if _managedBy_key:
            param_data = data[_managedBy_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<managedBy>{esc(str(param_data))}</managedBy>')
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
        xml_parts.append(f'</GetAllowedImagesSettingsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_image_ancestry_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetImageAncestryResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageAncestryEntrySet
        _imageAncestryEntrySet_key = None
        if "imageAncestryEntrySet" in data:
            _imageAncestryEntrySet_key = "imageAncestryEntrySet"
        elif "ImageAncestryEntrySet" in data:
            _imageAncestryEntrySet_key = "ImageAncestryEntrySet"
        elif "ImageAncestryEntrys" in data:
            _imageAncestryEntrySet_key = "ImageAncestryEntrys"
        if _imageAncestryEntrySet_key:
            param_data = data[_imageAncestryEntrySet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageAncestryEntrySet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageAncestryEntrySet>')
            else:
                xml_parts.append(f'{indent_str}<imageAncestryEntrySet/>')
        xml_parts.append(f'</GetImageAncestryResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_image_block_public_access_state_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetImageBlockPublicAccessStateResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageBlockPublicAccessState
        _imageBlockPublicAccessState_key = None
        if "imageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "imageBlockPublicAccessState"
        elif "ImageBlockPublicAccessState" in data:
            _imageBlockPublicAccessState_key = "ImageBlockPublicAccessState"
        if _imageBlockPublicAccessState_key:
            param_data = data[_imageBlockPublicAccessState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageBlockPublicAccessState>{esc(str(param_data))}</imageBlockPublicAccessState>')
        # Serialize managedBy
        _managedBy_key = None
        if "managedBy" in data:
            _managedBy_key = "managedBy"
        elif "ManagedBy" in data:
            _managedBy_key = "ManagedBy"
        if _managedBy_key:
            param_data = data[_managedBy_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<managedBy>{esc(str(param_data))}</managedBy>')
        xml_parts.append(f'</GetImageBlockPublicAccessStateResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_image_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifyImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ModifyImageAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_register_image_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RegisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageId
        _imageId_key = None
        if "imageId" in data:
            _imageId_key = "imageId"
        elif "ImageId" in data:
            _imageId_key = "ImageId"
        if _imageId_key:
            param_data = data[_imageId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<imageId>{esc(str(param_data))}</imageId>')
        xml_parts.append(f'</RegisterImageResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_replace_image_criteria_in_allowed_images_settings_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ReplaceImageCriteriaInAllowedImagesSettingsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ReplaceImageCriteriaInAllowedImagesSettingsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_reset_image_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ResetImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ResetImageAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_list_images_in_recycle_bin_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ListImagesInRecycleBinResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize imageSet
        _imageSet_key = None
        if "imageSet" in data:
            _imageSet_key = "imageSet"
        elif "ImageSet" in data:
            _imageSet_key = "ImageSet"
        elif "Images" in data:
            _imageSet_key = "Images"
        if _imageSet_key:
            param_data = data[_imageSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<imageSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(ami_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</imageSet>')
            else:
                xml_parts.append(f'{indent_str}<imageSet/>')
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
        xml_parts.append(f'</ListImagesInRecycleBinResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_restore_image_from_recycle_bin_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RestoreImageFromRecycleBinResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</RestoreImageFromRecycleBinResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "CancelImageLaunchPermission": ami_ResponseSerializer.serialize_cancel_image_launch_permission_response,
            "CopyImage": ami_ResponseSerializer.serialize_copy_image_response,
            "CreateImage": ami_ResponseSerializer.serialize_create_image_response,
            "CreateImageUsageReport": ami_ResponseSerializer.serialize_create_image_usage_report_response,
            "CreateRestoreImageTask": ami_ResponseSerializer.serialize_create_restore_image_task_response,
            "CreateStoreImageTask": ami_ResponseSerializer.serialize_create_store_image_task_response,
            "DeleteImageUsageReport": ami_ResponseSerializer.serialize_delete_image_usage_report_response,
            "DeregisterImage": ami_ResponseSerializer.serialize_deregister_image_response,
            "DescribeFastLaunchImages": ami_ResponseSerializer.serialize_describe_fast_launch_images_response,
            "DescribeImageAttribute": ami_ResponseSerializer.serialize_describe_image_attribute_response,
            "DescribeImageReferences": ami_ResponseSerializer.serialize_describe_image_references_response,
            "DescribeImages": ami_ResponseSerializer.serialize_describe_images_response,
            "DescribeImageUsageReportEntries": ami_ResponseSerializer.serialize_describe_image_usage_report_entries_response,
            "DescribeImageUsageReports": ami_ResponseSerializer.serialize_describe_image_usage_reports_response,
            "DescribeInstanceImageMetadata": ami_ResponseSerializer.serialize_describe_instance_image_metadata_response,
            "DescribeStoreImageTasks": ami_ResponseSerializer.serialize_describe_store_image_tasks_response,
            "DisableAllowedImagesSettings": ami_ResponseSerializer.serialize_disable_allowed_images_settings_response,
            "DisableFastLaunch": ami_ResponseSerializer.serialize_disable_fast_launch_response,
            "DisableImage": ami_ResponseSerializer.serialize_disable_image_response,
            "DisableImageBlockPublicAccess": ami_ResponseSerializer.serialize_disable_image_block_public_access_response,
            "DisableImageDeprecation": ami_ResponseSerializer.serialize_disable_image_deprecation_response,
            "DisableImageDeregistrationProtection": ami_ResponseSerializer.serialize_disable_image_deregistration_protection_response,
            "EnableAllowedImagesSettings": ami_ResponseSerializer.serialize_enable_allowed_images_settings_response,
            "EnableFastLaunch": ami_ResponseSerializer.serialize_enable_fast_launch_response,
            "EnableImage": ami_ResponseSerializer.serialize_enable_image_response,
            "EnableImageBlockPublicAccess": ami_ResponseSerializer.serialize_enable_image_block_public_access_response,
            "EnableImageDeprecation": ami_ResponseSerializer.serialize_enable_image_deprecation_response,
            "EnableImageDeregistrationProtection": ami_ResponseSerializer.serialize_enable_image_deregistration_protection_response,
            "GetAllowedImagesSettings": ami_ResponseSerializer.serialize_get_allowed_images_settings_response,
            "GetImageAncestry": ami_ResponseSerializer.serialize_get_image_ancestry_response,
            "GetImageBlockPublicAccessState": ami_ResponseSerializer.serialize_get_image_block_public_access_state_response,
            "ModifyImageAttribute": ami_ResponseSerializer.serialize_modify_image_attribute_response,
            "RegisterImage": ami_ResponseSerializer.serialize_register_image_response,
            "ReplaceImageCriteriaInAllowedImagesSettings": ami_ResponseSerializer.serialize_replace_image_criteria_in_allowed_images_settings_response,
            "ResetImageAttribute": ami_ResponseSerializer.serialize_reset_image_attribute_response,
            "ListImagesInRecycleBin": ami_ResponseSerializer.serialize_list_images_in_recycle_bin_response,
            "RestoreImageFromRecycleBin": ami_ResponseSerializer.serialize_restore_image_from_recycle_bin_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)
