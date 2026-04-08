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
class Snapshot:
    availability_zone: str = ""
    completion_duration_minutes: int = 0
    completion_time: str = ""
    data_encryption_key_id: str = ""
    description: str = ""
    encrypted: bool = False
    full_snapshot_size_in_bytes: int = 0
    kms_key_id: str = ""
    outpost_arn: str = ""
    owner_alias: str = ""
    owner_id: str = ""
    progress: str = ""
    restore_expiry_time: str = ""
    snapshot_id: str = ""
    sse_type: str = ""
    start_time: str = ""
    status: str = ""
    status_message: str = ""
    storage_tier: str = ""
    tag_set: List[Any] = field(default_factory=list)
    transfer_type: str = ""
    volume_id: str = ""
    volume_size: int = 0

    # Internal dependency tracking — not in API response
    fast_snapshot_restore_ids: List[str] = field(default_factory=list)  # tracks FastSnapshotRestore children
    volume_ids: List[str] = field(default_factory=list)  # tracks Volume children

    create_volume_permissions: List[Dict[str, Any]] = field(default_factory=list)
    product_codes: List[Dict[str, Any]] = field(default_factory=list)
    lock_state: str = ""
    lock_mode: str = ""
    lock_created_on: str = ""
    lock_duration: int = 0
    lock_duration_start_time: str = ""
    lock_expires_on: str = ""
    cool_off_period: int = 0
    cool_off_period_expires_on: str = ""
    archival_complete_time: str = ""
    last_tiering_operation_status: str = ""
    last_tiering_operation_status_detail: str = ""
    last_tiering_progress: str = ""
    last_tiering_start_time: str = ""
    tiering_start_time: str = ""
    restore_start_time: str = ""
    restore_duration: int = 0
    is_permanent_restore: bool = False
    in_recycle_bin: bool = False
    recycle_bin_enter_time: str = ""
    recycle_bin_exit_time: str = ""


    def to_dict(self) -> Dict[str, Any]:
        return {
            "availabilityZone": self.availability_zone,
            "completionDurationMinutes": self.completion_duration_minutes,
            "completionTime": self.completion_time,
            "dataEncryptionKeyId": self.data_encryption_key_id,
            "description": self.description,
            "encrypted": self.encrypted,
            "fullSnapshotSizeInBytes": self.full_snapshot_size_in_bytes,
            "kmsKeyId": self.kms_key_id,
            "outpostArn": self.outpost_arn,
            "ownerAlias": self.owner_alias,
            "ownerId": self.owner_id,
            "progress": self.progress,
            "restoreExpiryTime": self.restore_expiry_time,
            "snapshotId": self.snapshot_id,
            "sseType": self.sse_type,
            "startTime": self.start_time,
            "status": self.status,
            "statusMessage": self.status_message,
            "storageTier": self.storage_tier,
            "tagSet": self.tag_set,
            "transferType": self.transfer_type,
            "volumeId": self.volume_id,
            "volumeSize": self.volume_size,
        }

class Snapshot_Backend:
    def __init__(self):
        self.state = EC2State.get()
        self.resources = self.state.snapshots  # alias to shared store

    # Cross-resource parent registration (do this in Create/Delete methods):
    #   Create: self.state.volumes.get(params['volume_id']).snapshot_ids.append(new_id)
    #   Delete: self.state.volumes.get(resource.volume_id).snapshot_ids.remove(resource_id)

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

    def _get_snapshot_or_error(self, snapshot_id: str, error_code: str = "InvalidSnapshot.NotFound"):
        return self._get_resource_or_error(self.resources, snapshot_id, error_code, f"The ID '{snapshot_id}' does not exist")

    def _extract_tags(self, tag_specs: List[Dict[str, Any]], resource_type: str = "snapshot") -> List[Dict[str, Any]]:
        tags: List[Dict[str, Any]] = []
        for spec in tag_specs or []:
            spec_type = spec.get("ResourceType")
            if spec_type and spec_type != resource_type:
                continue
            for tag in spec.get("Tag") or spec.get("Tags") or []:
                if tag:
                    tags.append(tag)
        return tags

    def _get_snapshot_block_public_access_settings(self) -> Dict[str, Any]:
        if not hasattr(self.state, "snapshot_block_public_access"):
            setattr(self.state, "snapshot_block_public_access", {
                "state": "unblocked",
                "managedBy": "account",
            })
        settings = self.state.snapshot_block_public_access
        if "state" not in settings:
            settings["state"] = "unblocked"
        if "managedBy" not in settings:
            settings["managedBy"] = "account"
        return settings



    def CopySnapshot(self, params: Dict[str, Any]):
        """Creates an exact copy of an Amazon EBS snapshot. The location of the source snapshot determines whether you can copy it or not, 
      and the allowed destinations for the snapshot copy. If the source snapshot is in a Region, you can copy it within that Region, 
          to another Region, to an Ou"""

        error = self._require_params(params, ["SourceRegion", "SourceSnapshotId"])
        if error:
            return error

        source_snapshot_id = params.get("SourceSnapshotId")
        source_snapshot, error = self._get_snapshot_or_error(source_snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        snapshot_id = self._generate_id("snap")
        now = self._utc_now()
        tag_set = self._extract_tags(params.get("TagSpecification.N", []))
        if not tag_set:
            tag_set = list(source_snapshot.tag_set)

        encrypted = str2bool(params.get("Encrypted"))
        if params.get("Encrypted") is None:
            encrypted = source_snapshot.encrypted

        kms_key_id = params.get("KmsKeyId") or source_snapshot.kms_key_id
        outpost_arn = params.get("DestinationOutpostArn") or source_snapshot.outpost_arn
        availability_zone = params.get("DestinationAvailabilityZone") or source_snapshot.availability_zone

        snapshot = Snapshot(
            availability_zone=availability_zone,
            completion_duration_minutes=params.get("CompletionDurationMinutes") or source_snapshot.completion_duration_minutes,
            completion_time=now,
            data_encryption_key_id=source_snapshot.data_encryption_key_id,
            description=params.get("Description") or source_snapshot.description,
            encrypted=encrypted,
            full_snapshot_size_in_bytes=source_snapshot.full_snapshot_size_in_bytes,
            kms_key_id=kms_key_id,
            outpost_arn=outpost_arn,
            owner_alias=source_snapshot.owner_alias,
            owner_id=source_snapshot.owner_id,
            progress="100%",
            restore_expiry_time=source_snapshot.restore_expiry_time,
            snapshot_id=snapshot_id,
            sse_type=source_snapshot.sse_type,
            start_time=now,
            status="completed",
            status_message="",
            storage_tier=source_snapshot.storage_tier,
            tag_set=tag_set,
            transfer_type=source_snapshot.transfer_type,
            volume_id=source_snapshot.volume_id,
            volume_size=source_snapshot.volume_size,
        )

        self.resources[snapshot_id] = snapshot
        parent = self.state.volumes.get(snapshot.volume_id)
        if parent and hasattr(parent, "snapshot_ids"):
            parent.snapshot_ids.append(snapshot_id)

        return {
            "snapshotId": snapshot.snapshot_id,
            "tagSet": snapshot.tag_set,
        }

    def CreateSnapshot(self, params: Dict[str, Any]):
        """Creates a snapshot of an EBS volume and stores it in Amazon S3. You can use snapshots for
  	backups, to make copies of EBS volumes, and to save data before shutting down an
  	instance. The location of the source EBS volume determines where you can create the snapshot. If the source volume is in a """

        error = self._require_params(params, ["VolumeId"])
        if error:
            return error

        volume_id = params.get("VolumeId")
        volume, error = self._get_resource_or_error(
            self.state.volumes,
            volume_id,
            "InvalidVolume.NotFound",
            f"The ID '{volume_id}' does not exist",
        )
        if error:
            return error

        now = self._utc_now()
        snapshot_id = self._generate_id("snap")
        volume_size = (
            getattr(volume, "size", None)
            or getattr(volume, "volume_size", None)
            or getattr(volume, "volumeSize", None)
            or 0
        )
        availability_zone = (
            getattr(volume, "availability_zone", None)
            or getattr(volume, "availabilityZone", None)
            or ""
        )
        encrypted = bool(getattr(volume, "encrypted", False))
        kms_key_id = getattr(volume, "kms_key_id", None) or getattr(volume, "kmsKeyId", None) or ""
        sse_type = getattr(volume, "sse_type", None) or getattr(volume, "sseType", None) or ""
        owner_id = getattr(volume, "owner_id", None) or getattr(volume, "ownerId", None) or ""
        owner_alias = getattr(volume, "owner_alias", None) or getattr(volume, "ownerAlias", None) or ""
        outpost_arn = params.get("OutpostArn") or getattr(volume, "outpost_arn", None) or getattr(volume, "outpostArn", None) or ""

        snapshot = Snapshot(
            availability_zone=availability_zone,
            completion_duration_minutes=0,
            completion_time=now,
            data_encryption_key_id="",
            description=params.get("Description") or "",
            encrypted=encrypted,
            full_snapshot_size_in_bytes=int(volume_size) * 1024 * 1024 * 1024 if volume_size else 0,
            kms_key_id=kms_key_id,
            outpost_arn=outpost_arn,
            owner_alias=owner_alias,
            owner_id=owner_id,
            progress="100%",
            restore_expiry_time="",
            snapshot_id=snapshot_id,
            sse_type=sse_type,
            start_time=now,
            status="completed",
            status_message="",
            storage_tier="standard",
            tag_set=self._extract_tags(params.get("TagSpecification.N", [])),
            transfer_type="",
            volume_id=volume_id,
            volume_size=int(volume_size) if volume_size else 0,
        )

        self.resources[snapshot_id] = snapshot
        if volume and hasattr(volume, "snapshot_ids"):
            volume.snapshot_ids.append(snapshot_id)

        return snapshot.to_dict()

    def CreateSnapshots(self, params: Dict[str, Any]):
        """Creates crash-consistent snapshots of multiple EBS volumes attached to an Amazon EC2 instance.
    Volumes are chosen by specifying an instance. Each volume attached to the specified instance 
    will produce one snapshot that is crash-consistent across the instance. You can include all of 
    the"""

        error = self._require_params(params, ["InstanceSpecification"])
        if error:
            return error

        instance_spec = params.get("InstanceSpecification")
        instance_id = None
        if isinstance(instance_spec, dict):
            instance_id = instance_spec.get("InstanceId") or instance_spec.get("instanceId")
        elif isinstance(instance_spec, str):
            instance_id = instance_spec

        if not instance_id:
            return create_error_response("MissingParameter", "Missing required parameter: InstanceSpecification")

        instance = self.state.instances.get(instance_id)
        if not instance:
            return create_error_response("InvalidInstanceID.NotFound", f"The ID '{instance_id}' does not exist")

        volume_ids: List[str] = []
        volume_ids.extend(getattr(instance, "volume_ids", []) or [])
        for mapping in instance.block_device_mapping or []:
            if not isinstance(mapping, dict):
                continue
            ebs_mapping = mapping.get("Ebs") or mapping.get("EBS") or {}
            volume_id = mapping.get("VolumeId") or mapping.get("volumeId") or ebs_mapping.get("VolumeId") or ebs_mapping.get("volumeId")
            if volume_id:
                volume_ids.append(volume_id)

        seen = set()
        unique_volume_ids = []
        for volume_id in volume_ids:
            if volume_id in seen:
                continue
            seen.add(volume_id)
            unique_volume_ids.append(volume_id)

        tag_specs = params.get("TagSpecification.N", [])
        base_tags = self._extract_tags(tag_specs)
        copy_tags_from_source = str(params.get("CopyTagsFromSource") or "").lower()
        now = self._utc_now()
        snapshot_set: List[Dict[str, Any]] = []

        for volume_id in unique_volume_ids:
            volume = self.state.volumes.get(volume_id)
            if not volume:
                return create_error_response("InvalidVolume.NotFound", f"The ID '{volume_id}' does not exist")

            volume_size = (
                getattr(volume, "size", None)
                or getattr(volume, "volume_size", None)
                or getattr(volume, "volumeSize", None)
                or 0
            )
            availability_zone = (
                getattr(volume, "availability_zone", None)
                or getattr(volume, "availabilityZone", None)
                or ""
            )
            encrypted = bool(getattr(volume, "encrypted", False))
            kms_key_id = getattr(volume, "kms_key_id", None) or getattr(volume, "kmsKeyId", None) or ""
            sse_type = getattr(volume, "sse_type", None) or getattr(volume, "sseType", None) or ""
            owner_id = getattr(volume, "owner_id", None) or getattr(volume, "ownerId", None) or ""
            owner_alias = getattr(volume, "owner_alias", None) or getattr(volume, "ownerAlias", None) or ""
            outpost_arn = params.get("OutpostArn") or getattr(volume, "outpost_arn", None) or getattr(volume, "outpostArn", None) or ""

            tags = list(base_tags)
            if copy_tags_from_source == "volume":
                tags.extend(getattr(volume, "tag_set", []) or [])

            snapshot_id = self._generate_id("snap")
            snapshot = Snapshot(
                availability_zone=availability_zone,
                completion_duration_minutes=0,
                completion_time=now,
                data_encryption_key_id="",
                description=params.get("Description") or "",
                encrypted=encrypted,
                full_snapshot_size_in_bytes=int(volume_size) * 1024 * 1024 * 1024 if volume_size else 0,
                kms_key_id=kms_key_id,
                outpost_arn=outpost_arn,
                owner_alias=owner_alias,
                owner_id=owner_id,
                progress="100%",
                restore_expiry_time="",
                snapshot_id=snapshot_id,
                sse_type=sse_type,
                start_time=now,
                status="completed",
                status_message="",
                storage_tier="standard",
                tag_set=tags,
                transfer_type="",
                volume_id=volume_id,
                volume_size=int(volume_size) if volume_size else 0,
            )

            self.resources[snapshot_id] = snapshot
            if volume and hasattr(volume, "snapshot_ids"):
                volume.snapshot_ids.append(snapshot_id)

            snapshot_set.append({
                "availabilityZone": snapshot.availability_zone,
                "description": snapshot.description,
                "encrypted": snapshot.encrypted,
                "outpostArn": snapshot.outpost_arn,
                "ownerId": snapshot.owner_id,
                "progress": snapshot.progress,
                "snapshotId": snapshot.snapshot_id,
                "sseType": snapshot.sse_type,
                "startTime": snapshot.start_time,
                "state": snapshot.status,
                "tagSet": snapshot.tag_set,
                "volumeId": snapshot.volume_id,
                "volumeSize": snapshot.volume_size,
            })

        return {
            "snapshotSet": snapshot_set,
        }

    def DescribeLockedSnapshots(self, params: Dict[str, Any]):
        """Describes the lock status for a snapshot."""

        snapshot_ids = params.get("SnapshotId.N", [])
        if snapshot_ids:
            resources, error = self._get_resources_by_ids(self.resources, snapshot_ids, "InvalidSnapshot.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        filters = params.get("Filter.N", [])
        resources = apply_filters(resources, filters)

        max_results = int(params.get("MaxResults") or 100)
        next_token = params.get("NextToken")
        start_index = 0
        if next_token:
            try:
                start_index = int(next_token)
            except (TypeError, ValueError):
                start_index = 0

        page = resources[start_index:start_index + max_results]
        new_next_token = None
        if start_index + max_results < len(resources):
            new_next_token = str(start_index + max_results)

        snapshot_set = []
        for snapshot in page:
            snapshot_set.append({
                "coolOffPeriod": snapshot.cool_off_period,
                "coolOffPeriodExpiresOn": snapshot.cool_off_period_expires_on,
                "lockCreatedOn": snapshot.lock_created_on,
                "lockDuration": snapshot.lock_duration,
                "lockDurationStartTime": snapshot.lock_duration_start_time,
                "lockExpiresOn": snapshot.lock_expires_on,
                "lockState": snapshot.lock_state,
                "ownerId": snapshot.owner_id,
                "snapshotId": snapshot.snapshot_id,
            })

        return {
            "nextToken": new_next_token,
            "snapshotSet": snapshot_set,
        }

    def DeleteSnapshot(self, params: Dict[str, Any]):
        """Deletes the specified snapshot. When you make periodic snapshots of a volume, the snapshots are incremental, and only the
      blocks on the device that have changed since your last snapshot are saved in the new snapshot.
      When you delete a snapshot, only the data not needed for any other snap"""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        if getattr(snapshot, "fast_snapshot_restore_ids", []):
            return create_error_response(
                "DependencyViolation",
                "Snapshot has dependent FastSnapshotRestore(s) and cannot be deleted.",
            )
        if getattr(snapshot, "volume_ids", []):
            return create_error_response(
                "DependencyViolation",
                "Snapshot has dependent Volume(s) and cannot be deleted.",
            )

        parent = self.state.volumes.get(snapshot.volume_id)
        if parent and hasattr(parent, "snapshot_ids") and snapshot_id in parent.snapshot_ids:
            parent.snapshot_ids.remove(snapshot_id)

        self.resources.pop(snapshot_id, None)

        return {
            "return": True,
        }

    def DescribeSnapshotAttribute(self, params: Dict[str, Any]):
        """Describes the specified attribute of the specified snapshot. You can specify only one
      attribute at a time. For more information about EBS snapshots, seeAmazon EBS snapshotsin theAmazon EBS User Guide."""

        error = self._require_params(params, ["Attribute", "SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or ""
        if attribute not in ("createVolumePermission", "productCodes"):
            return create_error_response("InvalidParameterValue", f"Invalid attribute '{attribute}'")

        create_volume_permission = []
        product_codes = []
        if attribute == "createVolumePermission":
            create_volume_permission = snapshot.create_volume_permissions
        elif attribute == "productCodes":
            product_codes = snapshot.product_codes

        return {
            "createVolumePermission": create_volume_permission,
            "productCodes": product_codes,
            "snapshotId": snapshot.snapshot_id,
        }

    def DescribeSnapshots(self, params: Dict[str, Any]):
        """Describes the specified EBS snapshots available to you or all of the EBS snapshots
      available to you. The snapshots available to you include public snapshots, private snapshots that you own,
      and private snapshots owned by other AWS accounts for which you have explicit create volume
      """

        snapshot_ids = params.get("SnapshotId.N", [])
        if snapshot_ids:
            resources, error = self._get_resources_by_ids(self.resources, snapshot_ids, "InvalidSnapshot.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        owners = params.get("Owner.N", [])
        if owners:
            resources = [resource for resource in resources if resource.owner_id in owners]

        restorable_by = params.get("RestorableBy.N", [])
        if restorable_by:
            restorable_set = set(restorable_by)
            filtered = []
            for resource in resources:
                if resource.owner_id in restorable_set:
                    filtered.append(resource)
                    continue
                for permission in resource.create_volume_permissions or []:
                    user_id = permission.get("UserId")
                    group = permission.get("Group")
                    if user_id and user_id in restorable_set:
                        filtered.append(resource)
                        break
                    if group and group in restorable_set:
                        filtered.append(resource)
                        break
            resources = filtered

        filters = params.get("Filter.N", [])
        resources = apply_filters(resources, filters)

        max_results = int(params.get("MaxResults") or 100)
        next_token = params.get("NextToken")
        start_index = 0
        if next_token:
            try:
                start_index = int(next_token)
            except (TypeError, ValueError):
                start_index = 0

        page = resources[start_index:start_index + max_results]
        new_next_token = None
        if start_index + max_results < len(resources):
            new_next_token = str(start_index + max_results)

        return {
            "nextToken": new_next_token,
            "snapshotSet": [resource.to_dict() for resource in page],
        }

    def DescribeSnapshotTierStatus(self, params: Dict[str, Any]):
        """Describes the storage tier status of one or more Amazon EBS snapshots."""

        resources = list(self.resources.values())
        filters = params.get("Filter.N", [])
        resources = apply_filters(resources, filters)

        max_results = int(params.get("MaxResults") or 100)
        next_token = params.get("NextToken")
        start_index = 0
        if next_token:
            try:
                start_index = int(next_token)
            except (TypeError, ValueError):
                start_index = 0

        page = resources[start_index:start_index + max_results]
        new_next_token = None
        if start_index + max_results < len(resources):
            new_next_token = str(start_index + max_results)

        snapshot_tier_status_set = []
        for snapshot in page:
            snapshot_tier_status_set.append({
                "archivalCompleteTime": snapshot.archival_complete_time,
                "lastTieringOperationStatus": snapshot.last_tiering_operation_status,
                "lastTieringOperationStatusDetail": snapshot.last_tiering_operation_status_detail,
                "lastTieringProgress": snapshot.last_tiering_progress,
                "lastTieringStartTime": snapshot.last_tiering_start_time,
                "ownerId": snapshot.owner_id,
                "restoreExpiryTime": snapshot.restore_expiry_time,
                "snapshotId": snapshot.snapshot_id,
                "status": snapshot.status,
                "storageTier": snapshot.storage_tier,
                "tagSet": snapshot.tag_set,
                "volumeId": snapshot.volume_id,
            })

        return {
            "nextToken": new_next_token,
            "snapshotTierStatusSet": snapshot_tier_status_set,
        }

    def DisableSnapshotBlockPublicAccess(self, params: Dict[str, Any]):
        """Disables theblock public access for snapshotssetting at 
      the account level for the specified AWS Region. After you disable block public 
      access for snapshots in a Region, users can publicly share snapshots in that Region. Enabling block public access for snapshots inblock-all-sharingmode"""

        settings = self._get_snapshot_block_public_access_settings()
        settings["state"] = "unblocked"

        return {
            "state": settings.get("state"),
        }

    def EnableSnapshotBlockPublicAccess(self, params: Dict[str, Any]):
        """Enables or modifies theblock public access for snapshotssetting at the account level for the specified AWS Region. After you enable block 
      public access for snapshots in a Region, users can no longer request public sharing 
      for snapshots in that Region. Snapshots that are already publicl"""

        error = self._require_params(params, ["State"])
        if error:
            return error

        state_value = params.get("State")
        settings = self._get_snapshot_block_public_access_settings()
        settings["state"] = state_value

        return {
            "state": settings.get("state"),
        }

    def GetSnapshotBlockPublicAccessState(self, params: Dict[str, Any]):
        """Gets the current state ofblock public access for snapshotssetting 
      for the account and Region. For more information, seeBlock public access for snapshotsin theAmazon EBS User Guide."""

        settings = self._get_snapshot_block_public_access_settings()

        return {
            "managedBy": settings.get("managedBy"),
            "state": settings.get("state"),
        }

    def LockSnapshot(self, params: Dict[str, Any]):
        """Locks an Amazon EBS snapshot in eithergovernanceorcompliancemode to protect it against accidental or malicious deletions for a specific duration. A locked snapshot 
      can't be deleted. You can also use this action to modify the lock settings for a snapshot that is already locked. The 
      allo"""

        error = self._require_params(params, ["LockMode", "SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        lock_mode = params.get("LockMode")
        if lock_mode not in ("governance", "compliance"):
            return create_error_response("InvalidParameterValue", f"Invalid lock mode '{lock_mode}'")

        now = self._utc_now()
        lock_duration = int(params.get("LockDuration") or 0)
        cool_off_period = int(params.get("CoolOffPeriod") or 0)
        lock_expires_on = params.get("ExpirationDate") or ""

        snapshot.lock_mode = lock_mode
        snapshot.lock_state = "locked"
        snapshot.lock_created_on = now
        snapshot.lock_duration = lock_duration
        snapshot.lock_duration_start_time = now
        snapshot.cool_off_period = cool_off_period
        snapshot.cool_off_period_expires_on = ""
        snapshot.lock_expires_on = lock_expires_on

        return {
            "coolOffPeriod": snapshot.cool_off_period,
            "coolOffPeriodExpiresOn": snapshot.cool_off_period_expires_on,
            "lockCreatedOn": snapshot.lock_created_on,
            "lockDuration": snapshot.lock_duration,
            "lockDurationStartTime": snapshot.lock_duration_start_time,
            "lockExpiresOn": snapshot.lock_expires_on,
            "lockState": snapshot.lock_state,
            "snapshotId": snapshot.snapshot_id,
        }

    def ModifySnapshotAttribute(self, params: Dict[str, Any]):
        """Adds or removes permission settings for the specified snapshot. You may add or remove
      specified AWS account IDs from a snapshot's list of create volume permissions, but you cannot
      do both in a single operation. If you need to both add and remove account IDs for a snapshot,
      you must"""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or "createVolumePermission"
        if attribute not in ("createVolumePermission", "productCodes"):
            return create_error_response("InvalidParameterValue", f"Invalid attribute '{attribute}'")

        operation_type = params.get("OperationType") or ""
        if operation_type and operation_type not in ("add", "remove"):
            return create_error_response("InvalidParameterValue", f"Invalid operation type '{operation_type}'")

        user_groups = params.get("UserGroup.N", [])
        user_ids = params.get("UserId.N", [])
        permissions_payload = params.get("CreateVolumePermission") or {}
        if isinstance(permissions_payload, dict):
            user_groups = permissions_payload.get("Group", user_groups) or user_groups
            user_ids = permissions_payload.get("UserId", user_ids) or user_ids
            if not operation_type:
                operation_type = permissions_payload.get("OperationType") or operation_type

        changes = []
        for group in user_groups or []:
            changes.append({"Group": group})
        for user_id in user_ids or []:
            changes.append({"UserId": user_id})

        if attribute == "createVolumePermission":
            if operation_type == "add":
                for item in changes:
                    if item not in snapshot.create_volume_permissions:
                        snapshot.create_volume_permissions.append(item)
            elif operation_type == "remove":
                snapshot.create_volume_permissions = [
                    item for item in snapshot.create_volume_permissions if item not in changes
                ]
            elif changes:
                snapshot.create_volume_permissions = list(changes)
        else:
            if operation_type == "add":
                for item in changes:
                    if item not in snapshot.product_codes:
                        snapshot.product_codes.append(item)
            elif operation_type == "remove":
                snapshot.product_codes = [
                    item for item in snapshot.product_codes if item not in changes
                ]
            elif changes:
                snapshot.product_codes = list(changes)

        return {
            "return": True,
        }

    def ModifySnapshotTier(self, params: Dict[str, Any]):
        """Archives an Amazon EBS snapshot. When you archive a snapshot, it is converted to a full 
      snapshot that includes all of the blocks of data that were written to the volume at the 
      time the snapshot was created, and moved from the standard tier to the archive 
      tier. For more informati"""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        storage_tier = params.get("StorageTier") or "archive"
        now = self._utc_now()
        snapshot.storage_tier = storage_tier
        snapshot.tiering_start_time = now
        snapshot.archival_complete_time = now
        snapshot.last_tiering_operation_status = "completed"
        snapshot.last_tiering_operation_status_detail = ""
        snapshot.last_tiering_progress = "100%"
        snapshot.last_tiering_start_time = now

        return {
            "snapshotId": snapshot.snapshot_id,
            "tieringStartTime": snapshot.tiering_start_time,
        }

    def ResetSnapshotAttribute(self, params: Dict[str, Any]):
        """Resets permission settings for the specified snapshot. For more information about modifying snapshot permissions, seeShare a snapshotin theAmazon EBS User Guide."""

        error = self._require_params(params, ["Attribute", "SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        attribute = params.get("Attribute") or ""
        if attribute not in ("createVolumePermission", "productCodes"):
            return create_error_response("InvalidParameterValue", f"Invalid attribute '{attribute}'")

        if attribute == "createVolumePermission":
            snapshot.create_volume_permissions = []
        else:
            snapshot.product_codes = []

        return {
            "return": True,
        }

    def RestoreSnapshotTier(self, params: Dict[str, Any]):
        """Restores an archived Amazon EBS snapshot for use temporarily or permanently, or modifies the restore 
      period or restore type for a snapshot that was previously temporarily restored. For more information seeRestore an archived snapshotandmodify the restore period or restore type for a temporari"""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        is_permanent = str2bool(params.get("PermanentRestore"))
        restore_days = params.get("TemporaryRestoreDays")
        if is_permanent:
            snapshot.is_permanent_restore = True
            snapshot.restore_duration = 0
        else:
            snapshot.is_permanent_restore = False
            snapshot.restore_duration = int(restore_days or 0)

        snapshot.restore_start_time = self._utc_now()
        snapshot.restore_expiry_time = ""
        if snapshot.restore_duration:
            snapshot.restore_expiry_time = snapshot.restore_start_time

        return {
            "isPermanentRestore": snapshot.is_permanent_restore,
            "restoreDuration": snapshot.restore_duration,
            "restoreStartTime": snapshot.restore_start_time,
            "snapshotId": snapshot.snapshot_id,
        }

    def UnlockSnapshot(self, params: Dict[str, Any]):
        """Unlocks a snapshot that is locked in governance mode or that is locked in compliance mode 
      but still in the cooling-off period. You can't unlock a snapshot that is locked in compliance 
      mode after the cooling-off period has expired."""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        snapshot.lock_state = ""
        snapshot.lock_mode = ""
        snapshot.lock_created_on = ""
        snapshot.lock_duration = 0
        snapshot.lock_duration_start_time = ""
        snapshot.lock_expires_on = ""
        snapshot.cool_off_period = 0
        snapshot.cool_off_period_expires_on = ""

        return {
            "snapshotId": snapshot.snapshot_id,
        }

    def ListSnapshotsInRecycleBin(self, params: Dict[str, Any]):
        """Lists one or more snapshots that are currently in the Recycle Bin."""

        snapshot_ids = params.get("SnapshotId.N", [])
        if snapshot_ids:
            resources, error = self._get_resources_by_ids(self.resources, snapshot_ids, "InvalidSnapshot.NotFound")
            if error:
                return error
        else:
            resources = list(self.resources.values())

        resources = [resource for resource in resources if resource.in_recycle_bin]

        max_results = int(params.get("MaxResults") or 100)
        next_token = params.get("NextToken")
        start_index = 0
        if next_token:
            try:
                start_index = int(next_token)
            except (TypeError, ValueError):
                start_index = 0

        page = resources[start_index:start_index + max_results]
        new_next_token = None
        if start_index + max_results < len(resources):
            new_next_token = str(start_index + max_results)

        snapshot_set = []
        for snapshot in page:
            snapshot_set.append({
                "description": snapshot.description,
                "recycleBinEnterTime": snapshot.recycle_bin_enter_time,
                "recycleBinExitTime": snapshot.recycle_bin_exit_time,
                "snapshotId": snapshot.snapshot_id,
                "volumeId": snapshot.volume_id,
            })

        return {
            "nextToken": new_next_token,
            "snapshotSet": snapshot_set,
        }

    def RestoreSnapshotFromRecycleBin(self, params: Dict[str, Any]):
        """Restores a snapshot from the Recycle Bin. For more information, seeRestore 
      snapshots from the Recycle Binin theAmazon EBS User Guide."""

        error = self._require_params(params, ["SnapshotId"])
        if error:
            return error

        snapshot_id = params.get("SnapshotId")
        snapshot, error = self._get_snapshot_or_error(snapshot_id, "InvalidSnapshot.NotFound")
        if error:
            return error

        snapshot.in_recycle_bin = False
        snapshot.recycle_bin_enter_time = ""
        snapshot.recycle_bin_exit_time = ""

        return {
            "description": snapshot.description,
            "encrypted": snapshot.encrypted,
            "outpostArn": snapshot.outpost_arn,
            "ownerId": snapshot.owner_id,
            "progress": snapshot.progress,
            "snapshotId": snapshot.snapshot_id,
            "sseType": snapshot.sse_type,
            "startTime": snapshot.start_time,
            "status": snapshot.status,
            "volumeId": snapshot.volume_id,
            "volumeSize": snapshot.volume_size,
        }

    def _generate_id(self, prefix: str = 'snap') -> str:
        return f'{prefix}-{uuid.uuid4().hex[:17]}'

from typing import Dict, List, Any, Optional
from ..utils import get_scalar, get_int, get_indexed_list, parse_filters, parse_tags, str2bool, esc
from ..utils import is_error_response, serialize_error_response

class snapshot_RequestParser:
    @staticmethod
    def parse_copy_snapshot_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CompletionDurationMinutes": get_int(md, "CompletionDurationMinutes"),
            "Description": get_scalar(md, "Description"),
            "DestinationAvailabilityZone": get_scalar(md, "DestinationAvailabilityZone"),
            "DestinationOutpostArn": get_scalar(md, "DestinationOutpostArn"),
            "DestinationRegion": get_scalar(md, "DestinationRegion"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Encrypted": get_scalar(md, "Encrypted"),
            "KmsKeyId": get_scalar(md, "KmsKeyId"),
            "PresignedUrl": get_scalar(md, "PresignedUrl"),
            "SourceRegion": get_scalar(md, "SourceRegion"),
            "SourceSnapshotId": get_scalar(md, "SourceSnapshotId"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_create_snapshot_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Location": get_scalar(md, "Location"),
            "OutpostArn": get_scalar(md, "OutpostArn"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
            "VolumeId": get_scalar(md, "VolumeId"),
        }

    @staticmethod
    def parse_create_snapshots_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CopyTagsFromSource": get_scalar(md, "CopyTagsFromSource"),
            "Description": get_scalar(md, "Description"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "InstanceSpecification": get_scalar(md, "InstanceSpecification"),
            "Location": get_scalar(md, "Location"),
            "OutpostArn": get_scalar(md, "OutpostArn"),
            "TagSpecification.N": parse_tags(md, "TagSpecification"),
        }

    @staticmethod
    def parse_describe_locked_snapshots_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "SnapshotId.N": get_indexed_list(md, "SnapshotId"),
        }

    @staticmethod
    def parse_delete_snapshot_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_describe_snapshot_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_describe_snapshots_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "Owner.N": get_indexed_list(md, "Owner"),
            "RestorableBy.N": get_indexed_list(md, "RestorableBy"),
            "SnapshotId.N": get_indexed_list(md, "SnapshotId"),
        }

    @staticmethod
    def parse_describe_snapshot_tier_status_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "Filter.N": parse_filters(md, "Filter"),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
        }

    @staticmethod
    def parse_disable_snapshot_block_public_access_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_enable_snapshot_block_public_access_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "State": get_scalar(md, "State"),
        }

    @staticmethod
    def parse_get_snapshot_block_public_access_state_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
        }

    @staticmethod
    def parse_lock_snapshot_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CoolOffPeriod": get_int(md, "CoolOffPeriod"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "ExpirationDate": get_scalar(md, "ExpirationDate"),
            "LockDuration": get_int(md, "LockDuration"),
            "LockMode": get_scalar(md, "LockMode"),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_modify_snapshot_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "CreateVolumePermission": get_scalar(md, "CreateVolumePermission"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "OperationType": get_scalar(md, "OperationType"),
            "SnapshotId": get_scalar(md, "SnapshotId"),
            "UserGroup.N": get_indexed_list(md, "UserGroup"),
            "UserId.N": get_indexed_list(md, "UserId"),
        }

    @staticmethod
    def parse_modify_snapshot_tier_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
            "StorageTier": get_scalar(md, "StorageTier"),
        }

    @staticmethod
    def parse_reset_snapshot_attribute_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Attribute": get_scalar(md, "Attribute"),
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_restore_snapshot_tier_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "PermanentRestore": get_scalar(md, "PermanentRestore"),
            "SnapshotId": get_scalar(md, "SnapshotId"),
            "TemporaryRestoreDays": get_int(md, "TemporaryRestoreDays"),
        }

    @staticmethod
    def parse_unlock_snapshot_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_list_snapshots_in_recycle_bin_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "MaxResults": get_int(md, "MaxResults"),
            "NextToken": get_scalar(md, "NextToken"),
            "SnapshotId.N": get_indexed_list(md, "SnapshotId"),
        }

    @staticmethod
    def parse_restore_snapshot_from_recycle_bin_request(md: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "DryRun": str2bool(get_scalar(md, "DryRun")),
            "SnapshotId": get_scalar(md, "SnapshotId"),
        }

    @staticmethod
    def parse_request(action: str, md: Dict[str, Any]) -> Dict[str, Any]:
        parsers = {
            "CopySnapshot": snapshot_RequestParser.parse_copy_snapshot_request,
            "CreateSnapshot": snapshot_RequestParser.parse_create_snapshot_request,
            "CreateSnapshots": snapshot_RequestParser.parse_create_snapshots_request,
            "DescribeLockedSnapshots": snapshot_RequestParser.parse_describe_locked_snapshots_request,
            "DeleteSnapshot": snapshot_RequestParser.parse_delete_snapshot_request,
            "DescribeSnapshotAttribute": snapshot_RequestParser.parse_describe_snapshot_attribute_request,
            "DescribeSnapshots": snapshot_RequestParser.parse_describe_snapshots_request,
            "DescribeSnapshotTierStatus": snapshot_RequestParser.parse_describe_snapshot_tier_status_request,
            "DisableSnapshotBlockPublicAccess": snapshot_RequestParser.parse_disable_snapshot_block_public_access_request,
            "EnableSnapshotBlockPublicAccess": snapshot_RequestParser.parse_enable_snapshot_block_public_access_request,
            "GetSnapshotBlockPublicAccessState": snapshot_RequestParser.parse_get_snapshot_block_public_access_state_request,
            "LockSnapshot": snapshot_RequestParser.parse_lock_snapshot_request,
            "ModifySnapshotAttribute": snapshot_RequestParser.parse_modify_snapshot_attribute_request,
            "ModifySnapshotTier": snapshot_RequestParser.parse_modify_snapshot_tier_request,
            "ResetSnapshotAttribute": snapshot_RequestParser.parse_reset_snapshot_attribute_request,
            "RestoreSnapshotTier": snapshot_RequestParser.parse_restore_snapshot_tier_request,
            "UnlockSnapshot": snapshot_RequestParser.parse_unlock_snapshot_request,
            "ListSnapshotsInRecycleBin": snapshot_RequestParser.parse_list_snapshots_in_recycle_bin_request,
            "RestoreSnapshotFromRecycleBin": snapshot_RequestParser.parse_restore_snapshot_from_recycle_bin_request,
        }
        if action not in parsers:
            raise ValueError(f"Unknown action: {action}")
        return parsers[action](md)

class snapshot_ResponseSerializer:
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
                xml_parts.extend(snapshot_ResponseSerializer._serialize_dict_to_xml(value, key, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.extend(snapshot_ResponseSerializer._serialize_list_to_xml(value, key, indent_level))
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
                xml_parts.extend(snapshot_ResponseSerializer._serialize_dict_to_xml(item, 'item', indent_level + 2))
                xml_parts.append(f'{indent}    </item>')
            elif isinstance(item, list):
                xml_parts.extend(snapshot_ResponseSerializer._serialize_list_to_xml(item, tag_name, indent_level + 1))
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
                xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(value, indent_level + 1))
                xml_parts.append(f'{indent}</{key}>')
            elif isinstance(value, list):
                xml_parts.append(f'{indent}<{key}>')
                for item in value:
                    if isinstance(item, dict):
                        xml_parts.append(f'{indent}    <item>')
                        xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, indent_level + 2))
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
    def serialize_copy_snapshot_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CopySnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
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
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</tagSet>')
            else:
                xml_parts.append(f'{indent_str}<tagSet/>')
        xml_parts.append(f'</CopySnapshotResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_snapshot_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize availabilityZone
        _availabilityZone_key = None
        if "availabilityZone" in data:
            _availabilityZone_key = "availabilityZone"
        elif "AvailabilityZone" in data:
            _availabilityZone_key = "AvailabilityZone"
        if _availabilityZone_key:
            param_data = data[_availabilityZone_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<availabilityZone>{esc(str(param_data))}</availabilityZone>')
        # Serialize completionDurationMinutes
        _completionDurationMinutes_key = None
        if "completionDurationMinutes" in data:
            _completionDurationMinutes_key = "completionDurationMinutes"
        elif "CompletionDurationMinutes" in data:
            _completionDurationMinutes_key = "CompletionDurationMinutes"
        if _completionDurationMinutes_key:
            param_data = data[_completionDurationMinutes_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<completionDurationMinutesSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</completionDurationMinutesSet>')
            else:
                xml_parts.append(f'{indent_str}<completionDurationMinutesSet/>')
        # Serialize completionTime
        _completionTime_key = None
        if "completionTime" in data:
            _completionTime_key = "completionTime"
        elif "CompletionTime" in data:
            _completionTime_key = "CompletionTime"
        if _completionTime_key:
            param_data = data[_completionTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<completionTime>{esc(str(param_data))}</completionTime>')
        # Serialize dataEncryptionKeyId
        _dataEncryptionKeyId_key = None
        if "dataEncryptionKeyId" in data:
            _dataEncryptionKeyId_key = "dataEncryptionKeyId"
        elif "DataEncryptionKeyId" in data:
            _dataEncryptionKeyId_key = "DataEncryptionKeyId"
        if _dataEncryptionKeyId_key:
            param_data = data[_dataEncryptionKeyId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<dataEncryptionKeyId>{esc(str(param_data))}</dataEncryptionKeyId>')
        # Serialize description
        _description_key = None
        if "description" in data:
            _description_key = "description"
        elif "Description" in data:
            _description_key = "Description"
        if _description_key:
            param_data = data[_description_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<description>{esc(str(param_data))}</description>')
        # Serialize encrypted
        _encrypted_key = None
        if "encrypted" in data:
            _encrypted_key = "encrypted"
        elif "Encrypted" in data:
            _encrypted_key = "Encrypted"
        if _encrypted_key:
            param_data = data[_encrypted_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<encrypted>{esc(str(param_data))}</encrypted>')
        # Serialize fullSnapshotSizeInBytes
        _fullSnapshotSizeInBytes_key = None
        if "fullSnapshotSizeInBytes" in data:
            _fullSnapshotSizeInBytes_key = "fullSnapshotSizeInBytes"
        elif "FullSnapshotSizeInBytes" in data:
            _fullSnapshotSizeInBytes_key = "FullSnapshotSizeInBytes"
        if _fullSnapshotSizeInBytes_key:
            param_data = data[_fullSnapshotSizeInBytes_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<fullSnapshotSizeInBytes>{esc(str(param_data))}</fullSnapshotSizeInBytes>')
        # Serialize kmsKeyId
        _kmsKeyId_key = None
        if "kmsKeyId" in data:
            _kmsKeyId_key = "kmsKeyId"
        elif "KmsKeyId" in data:
            _kmsKeyId_key = "KmsKeyId"
        if _kmsKeyId_key:
            param_data = data[_kmsKeyId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<kmsKeyId>{esc(str(param_data))}</kmsKeyId>')
        # Serialize outpostArn
        _outpostArn_key = None
        if "outpostArn" in data:
            _outpostArn_key = "outpostArn"
        elif "OutpostArn" in data:
            _outpostArn_key = "OutpostArn"
        if _outpostArn_key:
            param_data = data[_outpostArn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<outpostArn>{esc(str(param_data))}</outpostArn>')
        # Serialize ownerAlias
        _ownerAlias_key = None
        if "ownerAlias" in data:
            _ownerAlias_key = "ownerAlias"
        elif "OwnerAlias" in data:
            _ownerAlias_key = "OwnerAlias"
        if _ownerAlias_key:
            param_data = data[_ownerAlias_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<ownerAliasSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</ownerAliasSet>')
            else:
                xml_parts.append(f'{indent_str}<ownerAliasSet/>')
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
        # Serialize progress
        _progress_key = None
        if "progress" in data:
            _progress_key = "progress"
        elif "Progress" in data:
            _progress_key = "Progress"
        if _progress_key:
            param_data = data[_progress_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<progress>{esc(str(param_data))}</progress>')
        # Serialize restoreExpiryTime
        _restoreExpiryTime_key = None
        if "restoreExpiryTime" in data:
            _restoreExpiryTime_key = "restoreExpiryTime"
        elif "RestoreExpiryTime" in data:
            _restoreExpiryTime_key = "RestoreExpiryTime"
        if _restoreExpiryTime_key:
            param_data = data[_restoreExpiryTime_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<restoreExpiryTime>{esc(str(param_data))}</restoreExpiryTime>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        # Serialize sseType
        _sseType_key = None
        if "sseType" in data:
            _sseType_key = "sseType"
        elif "SseType" in data:
            _sseType_key = "SseType"
        if _sseType_key:
            param_data = data[_sseType_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<sseType>{esc(str(param_data))}</sseType>')
        # Serialize startTime
        _startTime_key = None
        if "startTime" in data:
            _startTime_key = "startTime"
        elif "StartTime" in data:
            _startTime_key = "StartTime"
        if _startTime_key:
            param_data = data[_startTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<startTime>{esc(str(param_data))}</startTime>')
        # Serialize status
        _status_key = None
        if "status" in data:
            _status_key = "status"
        elif "Status" in data:
            _status_key = "Status"
        if _status_key:
            param_data = data[_status_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<statusSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</statusSet>')
            else:
                xml_parts.append(f'{indent_str}<statusSet/>')
        # Serialize statusMessage
        _statusMessage_key = None
        if "statusMessage" in data:
            _statusMessage_key = "statusMessage"
        elif "StatusMessage" in data:
            _statusMessage_key = "StatusMessage"
        if _statusMessage_key:
            param_data = data[_statusMessage_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<statusMessage>{esc(str(param_data))}</statusMessage>')
        # Serialize storageTier
        _storageTier_key = None
        if "storageTier" in data:
            _storageTier_key = "storageTier"
        elif "StorageTier" in data:
            _storageTier_key = "StorageTier"
        if _storageTier_key:
            param_data = data[_storageTier_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<storageTier>{esc(str(param_data))}</storageTier>')
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
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</tagSet>')
            else:
                xml_parts.append(f'{indent_str}<tagSet/>')
        # Serialize transferType
        _transferType_key = None
        if "transferType" in data:
            _transferType_key = "transferType"
        elif "TransferType" in data:
            _transferType_key = "TransferType"
        if _transferType_key:
            param_data = data[_transferType_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<transferType>{esc(str(param_data))}</transferType>')
        # Serialize volumeId
        _volumeId_key = None
        if "volumeId" in data:
            _volumeId_key = "volumeId"
        elif "VolumeId" in data:
            _volumeId_key = "VolumeId"
        if _volumeId_key:
            param_data = data[_volumeId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<volumeId>{esc(str(param_data))}</volumeId>')
        # Serialize volumeSize
        _volumeSize_key = None
        if "volumeSize" in data:
            _volumeSize_key = "volumeSize"
        elif "VolumeSize" in data:
            _volumeSize_key = "VolumeSize"
        if _volumeSize_key:
            param_data = data[_volumeSize_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<volumeSize>{esc(str(param_data))}</volumeSize>')
        xml_parts.append(f'</CreateSnapshotResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_create_snapshots_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<CreateSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize snapshotSet
        _snapshotSet_key = None
        if "snapshotSet" in data:
            _snapshotSet_key = "snapshotSet"
        elif "SnapshotSet" in data:
            _snapshotSet_key = "SnapshotSet"
        elif "Snapshots" in data:
            _snapshotSet_key = "Snapshots"
        if _snapshotSet_key:
            param_data = data[_snapshotSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<snapshotSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</snapshotSet>')
            else:
                xml_parts.append(f'{indent_str}<snapshotSet/>')
        xml_parts.append(f'</CreateSnapshotsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_locked_snapshots_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeLockedSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize snapshotSet
        _snapshotSet_key = None
        if "snapshotSet" in data:
            _snapshotSet_key = "snapshotSet"
        elif "SnapshotSet" in data:
            _snapshotSet_key = "SnapshotSet"
        elif "Snapshots" in data:
            _snapshotSet_key = "Snapshots"
        if _snapshotSet_key:
            param_data = data[_snapshotSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<snapshotSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</snapshotSet>')
            else:
                xml_parts.append(f'{indent_str}<snapshotSet/>')
        xml_parts.append(f'</DescribeLockedSnapshotsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_delete_snapshot_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DeleteSnapshotResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_snapshot_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize createVolumePermission
        _createVolumePermission_key = None
        if "createVolumePermission" in data:
            _createVolumePermission_key = "createVolumePermission"
        elif "CreateVolumePermission" in data:
            _createVolumePermission_key = "CreateVolumePermission"
        if _createVolumePermission_key:
            param_data = data[_createVolumePermission_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<createVolumePermissionSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</createVolumePermissionSet>')
            else:
                xml_parts.append(f'{indent_str}<createVolumePermissionSet/>')
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
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</productCodesSet>')
            else:
                xml_parts.append(f'{indent_str}<productCodesSet/>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        xml_parts.append(f'</DescribeSnapshotAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_snapshots_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize snapshotSet
        _snapshotSet_key = None
        if "snapshotSet" in data:
            _snapshotSet_key = "snapshotSet"
        elif "SnapshotSet" in data:
            _snapshotSet_key = "SnapshotSet"
        elif "Snapshots" in data:
            _snapshotSet_key = "Snapshots"
        if _snapshotSet_key:
            param_data = data[_snapshotSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<snapshotSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</snapshotSet>')
            else:
                xml_parts.append(f'{indent_str}<snapshotSet/>')
        xml_parts.append(f'</DescribeSnapshotsResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_describe_snapshot_tier_status_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DescribeSnapshotTierStatusResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize snapshotTierStatusSet
        _snapshotTierStatusSet_key = None
        if "snapshotTierStatusSet" in data:
            _snapshotTierStatusSet_key = "snapshotTierStatusSet"
        elif "SnapshotTierStatusSet" in data:
            _snapshotTierStatusSet_key = "SnapshotTierStatusSet"
        elif "SnapshotTierStatuss" in data:
            _snapshotTierStatusSet_key = "SnapshotTierStatuss"
        if _snapshotTierStatusSet_key:
            param_data = data[_snapshotTierStatusSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<snapshotTierStatusSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</snapshotTierStatusSet>')
            else:
                xml_parts.append(f'{indent_str}<snapshotTierStatusSet/>')
        xml_parts.append(f'</DescribeSnapshotTierStatusResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_disable_snapshot_block_public_access_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<DisableSnapshotBlockPublicAccessResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</DisableSnapshotBlockPublicAccessResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_enable_snapshot_block_public_access_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<EnableSnapshotBlockPublicAccessResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</EnableSnapshotBlockPublicAccessResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_get_snapshot_block_public_access_state_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<GetSnapshotBlockPublicAccessStateResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
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
        xml_parts.append(f'</GetSnapshotBlockPublicAccessStateResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_lock_snapshot_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<LockSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize coolOffPeriod
        _coolOffPeriod_key = None
        if "coolOffPeriod" in data:
            _coolOffPeriod_key = "coolOffPeriod"
        elif "CoolOffPeriod" in data:
            _coolOffPeriod_key = "CoolOffPeriod"
        if _coolOffPeriod_key:
            param_data = data[_coolOffPeriod_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<coolOffPeriod>{esc(str(param_data))}</coolOffPeriod>')
        # Serialize coolOffPeriodExpiresOn
        _coolOffPeriodExpiresOn_key = None
        if "coolOffPeriodExpiresOn" in data:
            _coolOffPeriodExpiresOn_key = "coolOffPeriodExpiresOn"
        elif "CoolOffPeriodExpiresOn" in data:
            _coolOffPeriodExpiresOn_key = "CoolOffPeriodExpiresOn"
        if _coolOffPeriodExpiresOn_key:
            param_data = data[_coolOffPeriodExpiresOn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<coolOffPeriodExpiresOn>{esc(str(param_data))}</coolOffPeriodExpiresOn>')
        # Serialize lockCreatedOn
        _lockCreatedOn_key = None
        if "lockCreatedOn" in data:
            _lockCreatedOn_key = "lockCreatedOn"
        elif "LockCreatedOn" in data:
            _lockCreatedOn_key = "LockCreatedOn"
        if _lockCreatedOn_key:
            param_data = data[_lockCreatedOn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lockCreatedOn>{esc(str(param_data))}</lockCreatedOn>')
        # Serialize lockDuration
        _lockDuration_key = None
        if "lockDuration" in data:
            _lockDuration_key = "lockDuration"
        elif "LockDuration" in data:
            _lockDuration_key = "LockDuration"
        if _lockDuration_key:
            param_data = data[_lockDuration_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lockDuration>{esc(str(param_data))}</lockDuration>')
        # Serialize lockDurationStartTime
        _lockDurationStartTime_key = None
        if "lockDurationStartTime" in data:
            _lockDurationStartTime_key = "lockDurationStartTime"
        elif "LockDurationStartTime" in data:
            _lockDurationStartTime_key = "LockDurationStartTime"
        if _lockDurationStartTime_key:
            param_data = data[_lockDurationStartTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lockDurationStartTime>{esc(str(param_data))}</lockDurationStartTime>')
        # Serialize lockExpiresOn
        _lockExpiresOn_key = None
        if "lockExpiresOn" in data:
            _lockExpiresOn_key = "lockExpiresOn"
        elif "LockExpiresOn" in data:
            _lockExpiresOn_key = "LockExpiresOn"
        if _lockExpiresOn_key:
            param_data = data[_lockExpiresOn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lockExpiresOn>{esc(str(param_data))}</lockExpiresOn>')
        # Serialize lockState
        _lockState_key = None
        if "lockState" in data:
            _lockState_key = "lockState"
        elif "LockState" in data:
            _lockState_key = "LockState"
        if _lockState_key:
            param_data = data[_lockState_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<lockState>{esc(str(param_data))}</lockState>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        xml_parts.append(f'</LockSnapshotResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_snapshot_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifySnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ModifySnapshotAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_modify_snapshot_tier_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ModifySnapshotTierResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        # Serialize tieringStartTime
        _tieringStartTime_key = None
        if "tieringStartTime" in data:
            _tieringStartTime_key = "tieringStartTime"
        elif "TieringStartTime" in data:
            _tieringStartTime_key = "TieringStartTime"
        if _tieringStartTime_key:
            param_data = data[_tieringStartTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<tieringStartTime>{esc(str(param_data))}</tieringStartTime>')
        xml_parts.append(f'</ModifySnapshotTierResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_reset_snapshot_attribute_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ResetSnapshotAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        xml_parts.append(f'</ResetSnapshotAttributeResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_restore_snapshot_tier_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RestoreSnapshotTierResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize isPermanentRestore
        _isPermanentRestore_key = None
        if "isPermanentRestore" in data:
            _isPermanentRestore_key = "isPermanentRestore"
        elif "IsPermanentRestore" in data:
            _isPermanentRestore_key = "IsPermanentRestore"
        if _isPermanentRestore_key:
            param_data = data[_isPermanentRestore_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<isPermanentRestore>{esc(str(param_data))}</isPermanentRestore>')
        # Serialize restoreDuration
        _restoreDuration_key = None
        if "restoreDuration" in data:
            _restoreDuration_key = "restoreDuration"
        elif "RestoreDuration" in data:
            _restoreDuration_key = "RestoreDuration"
        if _restoreDuration_key:
            param_data = data[_restoreDuration_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<restoreDuration>{esc(str(param_data))}</restoreDuration>')
        # Serialize restoreStartTime
        _restoreStartTime_key = None
        if "restoreStartTime" in data:
            _restoreStartTime_key = "restoreStartTime"
        elif "RestoreStartTime" in data:
            _restoreStartTime_key = "RestoreStartTime"
        if _restoreStartTime_key:
            param_data = data[_restoreStartTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<restoreStartTime>{esc(str(param_data))}</restoreStartTime>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        xml_parts.append(f'</RestoreSnapshotTierResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_unlock_snapshot_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<UnlockSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        xml_parts.append(f'</UnlockSnapshotResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_list_snapshots_in_recycle_bin_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<ListSnapshotsInRecycleBinResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
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
        # Serialize snapshotSet
        _snapshotSet_key = None
        if "snapshotSet" in data:
            _snapshotSet_key = "snapshotSet"
        elif "SnapshotSet" in data:
            _snapshotSet_key = "SnapshotSet"
        elif "Snapshots" in data:
            _snapshotSet_key = "Snapshots"
        if _snapshotSet_key:
            param_data = data[_snapshotSet_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<snapshotSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>')
                    xml_parts.extend(snapshot_ResponseSerializer._serialize_nested_fields(item, 2))
                    xml_parts.append(f'{indent_str}    </item>')
                xml_parts.append(f'{indent_str}</snapshotSet>')
            else:
                xml_parts.append(f'{indent_str}<snapshotSet/>')
        xml_parts.append(f'</ListSnapshotsInRecycleBinResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize_restore_snapshot_from_recycle_bin_response(data: Dict[str, Any], request_id: str) -> str:
        xml_parts = []
        xml_parts.append(f'<RestoreSnapshotFromRecycleBinResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">')
        xml_parts.append(f'    <requestId>{esc(request_id)}</requestId>')
        # Serialize description
        _description_key = None
        if "description" in data:
            _description_key = "description"
        elif "Description" in data:
            _description_key = "Description"
        if _description_key:
            param_data = data[_description_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<description>{esc(str(param_data))}</description>')
        # Serialize encrypted
        _encrypted_key = None
        if "encrypted" in data:
            _encrypted_key = "encrypted"
        elif "Encrypted" in data:
            _encrypted_key = "Encrypted"
        if _encrypted_key:
            param_data = data[_encrypted_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<encrypted>{esc(str(param_data))}</encrypted>')
        # Serialize outpostArn
        _outpostArn_key = None
        if "outpostArn" in data:
            _outpostArn_key = "outpostArn"
        elif "OutpostArn" in data:
            _outpostArn_key = "OutpostArn"
        if _outpostArn_key:
            param_data = data[_outpostArn_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<outpostArn>{esc(str(param_data))}</outpostArn>')
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
        # Serialize progress
        _progress_key = None
        if "progress" in data:
            _progress_key = "progress"
        elif "Progress" in data:
            _progress_key = "Progress"
        if _progress_key:
            param_data = data[_progress_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<progressSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</progressSet>')
            else:
                xml_parts.append(f'{indent_str}<progressSet/>')
        # Serialize snapshotId
        _snapshotId_key = None
        if "snapshotId" in data:
            _snapshotId_key = "snapshotId"
        elif "SnapshotId" in data:
            _snapshotId_key = "SnapshotId"
        if _snapshotId_key:
            param_data = data[_snapshotId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<snapshotId>{esc(str(param_data))}</snapshotId>')
        # Serialize sseType
        _sseType_key = None
        if "sseType" in data:
            _sseType_key = "sseType"
        elif "SseType" in data:
            _sseType_key = "SseType"
        if _sseType_key:
            param_data = data[_sseType_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<sseType>{esc(str(param_data))}</sseType>')
        # Serialize startTime
        _startTime_key = None
        if "startTime" in data:
            _startTime_key = "startTime"
        elif "StartTime" in data:
            _startTime_key = "StartTime"
        if _startTime_key:
            param_data = data[_startTime_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<startTime>{esc(str(param_data))}</startTime>')
        # Serialize status
        _status_key = None
        if "status" in data:
            _status_key = "status"
        elif "Status" in data:
            _status_key = "Status"
        if _status_key:
            param_data = data[_status_key]
            indent_str = "    " * 1
            if param_data:
                xml_parts.append(f'{indent_str}<statusSet>')
                for item in param_data:
                    xml_parts.append(f'{indent_str}    <item>{esc(str(item))}</item>')
                xml_parts.append(f'{indent_str}</statusSet>')
            else:
                xml_parts.append(f'{indent_str}<statusSet/>')
        # Serialize volumeId
        _volumeId_key = None
        if "volumeId" in data:
            _volumeId_key = "volumeId"
        elif "VolumeId" in data:
            _volumeId_key = "VolumeId"
        if _volumeId_key:
            param_data = data[_volumeId_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<volumeId>{esc(str(param_data))}</volumeId>')
        # Serialize volumeSize
        _volumeSize_key = None
        if "volumeSize" in data:
            _volumeSize_key = "volumeSize"
        elif "VolumeSize" in data:
            _volumeSize_key = "VolumeSize"
        if _volumeSize_key:
            param_data = data[_volumeSize_key]
            indent_str = "    " * 1
            xml_parts.append(f'{indent_str}<volumeSize>{esc(str(param_data))}</volumeSize>')
        xml_parts.append(f'</RestoreSnapshotFromRecycleBinResponse>')
        return "\n".join(xml_parts)

    @staticmethod
    def serialize(action: str, data: Dict[str, Any], request_id: str) -> str:
        # Check for error response from backend
        if is_error_response(data):
            return serialize_error_response(data, request_id)
        
        serializers = {
            "CopySnapshot": snapshot_ResponseSerializer.serialize_copy_snapshot_response,
            "CreateSnapshot": snapshot_ResponseSerializer.serialize_create_snapshot_response,
            "CreateSnapshots": snapshot_ResponseSerializer.serialize_create_snapshots_response,
            "DescribeLockedSnapshots": snapshot_ResponseSerializer.serialize_describe_locked_snapshots_response,
            "DeleteSnapshot": snapshot_ResponseSerializer.serialize_delete_snapshot_response,
            "DescribeSnapshotAttribute": snapshot_ResponseSerializer.serialize_describe_snapshot_attribute_response,
            "DescribeSnapshots": snapshot_ResponseSerializer.serialize_describe_snapshots_response,
            "DescribeSnapshotTierStatus": snapshot_ResponseSerializer.serialize_describe_snapshot_tier_status_response,
            "DisableSnapshotBlockPublicAccess": snapshot_ResponseSerializer.serialize_disable_snapshot_block_public_access_response,
            "EnableSnapshotBlockPublicAccess": snapshot_ResponseSerializer.serialize_enable_snapshot_block_public_access_response,
            "GetSnapshotBlockPublicAccessState": snapshot_ResponseSerializer.serialize_get_snapshot_block_public_access_state_response,
            "LockSnapshot": snapshot_ResponseSerializer.serialize_lock_snapshot_response,
            "ModifySnapshotAttribute": snapshot_ResponseSerializer.serialize_modify_snapshot_attribute_response,
            "ModifySnapshotTier": snapshot_ResponseSerializer.serialize_modify_snapshot_tier_response,
            "ResetSnapshotAttribute": snapshot_ResponseSerializer.serialize_reset_snapshot_attribute_response,
            "RestoreSnapshotTier": snapshot_ResponseSerializer.serialize_restore_snapshot_tier_response,
            "UnlockSnapshot": snapshot_ResponseSerializer.serialize_unlock_snapshot_response,
            "ListSnapshotsInRecycleBin": snapshot_ResponseSerializer.serialize_list_snapshots_in_recycle_bin_response,
            "RestoreSnapshotFromRecycleBin": snapshot_ResponseSerializer.serialize_restore_snapshot_from_recycle_bin_response,
        }
        if action not in serializers:
            raise ValueError(f"Unknown action: {action}")
        return serializers[action](data, request_id)

