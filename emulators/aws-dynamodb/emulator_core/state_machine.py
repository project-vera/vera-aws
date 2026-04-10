"""
DynamoDB table state machine.

Tracks table lifecycle in memory:
  CREATING -> ACTIVE -> UPDATING -> ACTIVE
                     -> DELETING  (terminal)

On startup, existing tables from DynamoDB Local are imported as ACTIVE.
All data lives in DynamoDB Local; vera only tracks table_status.

Persistence strategy:
  - Backup metadata + PITR config + replica metadata → __vera_meta__ table
  - Backup item copies → __vera_bk_{short_id}__ clone tables
  - PITR write log → __vera_pitr_log__ table
  All stored in DynamoDB Local, surviving vera restarts.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("DynamoDBStateMachine")

# Internal table names — hidden from ListTables and user operations
VERA_META_TABLE = "__vera_meta__"
VERA_PITR_LOG_TABLE = "__vera_pitr_log__"
VERA_BK_PREFIX = "__vera_bk_"

def is_vera_internal(table_name: str) -> bool:
    return table_name.startswith("__vera_")


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class BackupRecord:
    backup_arn: str
    backup_name: str
    backup_type: str  # USER | SYSTEM | AWS_BACKUP
    table_name: str
    table_arn: str
    table_id: str
    key_schema: List[Dict[str, Any]]
    attribute_definitions: List[Dict[str, Any]]
    billing_mode: str
    provisioned_throughput: Optional[Dict[str, Any]]
    global_secondary_indexes: List[Dict[str, Any]]
    local_secondary_indexes: List[Dict[str, Any]]
    sse_description: Optional[Dict[str, Any]]
    stream_specification: Optional[Dict[str, Any]]
    backup_table: str  # internal table name holding item copies
    item_count: int
    backup_size_bytes: int
    created_at: str    # ISO-8601
    status: str = "AVAILABLE"  # AVAILABLE | DELETED

    def to_meta_item(self) -> Dict[str, Any]:
        """Serialize to DynamoDB item for __vera_meta__."""
        return {
            "pk": {"S": f"backup#{self.backup_arn}"},
            "sk": {"S": "meta"},
            "backup_arn": {"S": self.backup_arn},
            "backup_name": {"S": self.backup_name},
            "backup_type": {"S": self.backup_type},
            "table_name": {"S": self.table_name},
            "table_arn": {"S": self.table_arn},
            "table_id": {"S": self.table_id},
            "backup_table": {"S": self.backup_table},
            "item_count": {"N": str(self.item_count)},
            "backup_size_bytes": {"N": str(self.backup_size_bytes)},
            "created_at": {"S": self.created_at},
            "status": {"S": self.status},
            "schema_json": {"S": json.dumps({
                "key_schema": self.key_schema,
                "attribute_definitions": self.attribute_definitions,
                "billing_mode": self.billing_mode,
                "provisioned_throughput": self.provisioned_throughput,
                "global_secondary_indexes": self.global_secondary_indexes,
                "local_secondary_indexes": self.local_secondary_indexes,
                "sse_description": self.sse_description,
                "stream_specification": self.stream_specification,
            })},
        }

    @classmethod
    def from_meta_item(cls, item: Dict[str, Any]) -> "BackupRecord":
        schema = json.loads(item["schema_json"]["S"])
        return cls(
            backup_arn=item["backup_arn"]["S"],
            backup_name=item["backup_name"]["S"],
            backup_type=item["backup_type"]["S"],
            table_name=item["table_name"]["S"],
            table_arn=item["table_arn"]["S"],
            table_id=item["table_id"]["S"],
            backup_table=item["backup_table"]["S"],
            item_count=int(item["item_count"]["N"]),
            backup_size_bytes=int(item.get("backup_size_bytes", {}).get("N", "0")),
            created_at=item["created_at"]["S"],
            status=item["status"]["S"],
            key_schema=schema["key_schema"],
            attribute_definitions=schema["attribute_definitions"],
            billing_mode=schema["billing_mode"],
            provisioned_throughput=schema["provisioned_throughput"],
            global_secondary_indexes=schema["global_secondary_indexes"],
            local_secondary_indexes=schema["local_secondary_indexes"],
            sse_description=schema["sse_description"],
            stream_specification=schema["stream_specification"],
        )


@dataclass
class ReplicaRecord:
    region_name: str
    replica_status: str = "ACTIVE"
    kms_master_key_id: Optional[str] = None
    provisioned_throughput_override: Optional[Dict[str, Any]] = None
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = None
    autoscaling_read: Optional[Dict[str, Any]] = None
    autoscaling_write: Optional[Dict[str, Any]] = None


# Valid transitions: current_status -> set of allowed next statuses
_TRANSITIONS = {
    "CREATING":  {"ACTIVE", "DELETING"},
    "ACTIVE":    {"UPDATING", "DELETING"},
    "UPDATING":  {"ACTIVE", "DELETING"},
    "DELETING":  set(),  # terminal
}

# Operations blocked per status
_BLOCKED = {
    "CREATING":  {"DeleteTable", "UpdateTable"},
    "DELETING":  {"DeleteTable", "UpdateTable", "CreateTable"},
    "UPDATING":  {"DeleteTable"},
}


class TableStateMachine:
    """In-memory state tracker + persistent backup/PITR via DynamoDB Local."""

    def __init__(self):
        self._tables: Dict[str, str] = {}
        # Per-table UUIDs (vera-generated, since DDB Local returns empty string)
        self.table_ids: Dict[str, str] = {}
        # Per-table provisioned throughput (rcu, wcu) — used to patch ConsumedCapacity
        self.table_throughput: Dict[str, Dict[str, int]] = {}
        # In-memory caches (populated from __vera_meta__ on startup)
        self.backups: Dict[str, BackupRecord] = {}
        self.replicas: Dict[str, Dict[str, ReplicaRecord]] = {}
        # Per-table PITR enabled flag (table_name -> bool)
        self.pitr_enabled: Dict[str, bool] = {}
        # Contributor Insights: (table_name, index_name|"__table__") -> "ENABLED"|"DISABLED"
        self.contributor_insights: Dict[tuple[str, str], str] = {}
        # Tags: table_name -> {key: value}
        self.tags: Dict[str, Dict[str, str]] = {}
        # DynamoDB Local call function — injected by main.py after init
        self._ddb_call: Optional[Callable] = None

    def set_ddb_caller(self, fn: Callable):
        """Inject the _ddb_local_call function from main.py."""
        self._ddb_call = fn

    def _ddb(self, action: str, payload: dict) -> tuple[int, dict]:
        if not self._ddb_call:
            raise RuntimeError("DDB caller not set — call set_ddb_caller first")
        return self._ddb_call(action, payload)

    # ------------------------------------------------------------------
    # Internal table bootstrap
    # ------------------------------------------------------------------

    def ensure_internal_tables(self) -> None:
        """Create __vera_meta__ and __vera_pitr_log__ if they don't exist."""
        for tbl, schema in [
            (VERA_META_TABLE, [
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ]),
            (VERA_PITR_LOG_TABLE, [
                {"AttributeName": "table_name", "KeyType": "HASH"},
                {"AttributeName": "seq", "KeyType": "RANGE"},
            ]),
        ]:
            attr_defs = [
                {"AttributeName": e["AttributeName"],
                 "AttributeType": "S" if e["AttributeName"] != "seq" else "S"}
                for e in schema
            ]
            status, _ = self._ddb("CreateTable", {
                "TableName": tbl,
                "KeySchema": schema,
                "AttributeDefinitions": attr_defs,
                "BillingMode": "PAY_PER_REQUEST",
            })
            if status == 200:
                logger.info(f"Created internal table: {tbl}")
            # 400 = already exists, that's fine

    # ------------------------------------------------------------------
    # Load persisted state on startup
    # ------------------------------------------------------------------

    def load_persisted_state(self) -> None:
        """Reload backup records, PITR config, and replica metadata from __vera_meta__."""
        items = self._scan_all(VERA_META_TABLE)
        for item in items:
            pk = item.get("pk", {}).get("S", "")
            if pk.startswith("backup#"):
                try:
                    rec = BackupRecord.from_meta_item(item)
                    if rec.status != "DELETED":
                        self.backups[rec.backup_arn] = rec
                except Exception as e:
                    logger.warning(f"Failed to load backup record: {e}")
            elif pk.startswith("pitr#"):
                table_name = pk.split("#", 1)[1]
                enabled = item.get("enabled", {}).get("BOOL", False)
                self.pitr_enabled[table_name] = enabled
            elif pk.startswith("replica#"):
                table_name = pk.split("#", 1)[1]
                sk = item.get("sk", {}).get("S", "")
                if sk.startswith("region#"):
                    region = sk.split("#", 1)[1]
                    data = json.loads(item.get("data_json", {}).get("S", "{}"))
                    self.replicas.setdefault(table_name, {})[region] = ReplicaRecord(
                        region_name=region,
                        replica_status=data.get("replica_status", "ACTIVE"),
                        kms_master_key_id=data.get("kms_master_key_id"),
                        provisioned_throughput_override=data.get("provisioned_throughput_override"),
                        global_secondary_indexes=data.get("global_secondary_indexes"),
                        autoscaling_read=data.get("autoscaling_read"),
                        autoscaling_write=data.get("autoscaling_write"),
                    )
            elif pk.startswith("ci#"):
                # ci#TableName  sk=index#IndexName or sk=index#__table__
                table_name = pk.split("#", 1)[1]
                sk = item.get("sk", {}).get("S", "")
                index_name = sk.split("#", 1)[1] if "#" in sk else "__table__"
                ci_status = item.get("ci_status", {}).get("S", "DISABLED")
                self.contributor_insights[(table_name, index_name)] = ci_status
        logger.info(
            f"Loaded persisted state: {len(self.backups)} backups, "
            f"{sum(len(v) for v in self.replicas.values())} replicas, "
            f"{sum(1 for v in self.pitr_enabled.values() if v)} PITR-enabled tables"
        )

    def _scan_all(self, table_name: str) -> List[Dict[str, Any]]:
        items = []
        last_key = None
        while True:
            payload: dict = {"TableName": table_name}
            if last_key:
                payload["ExclusiveStartKey"] = last_key
            status, body = self._ddb("Scan", payload)
            if status != 200:
                break
            items.extend(body.get("Items", []))
            last_key = body.get("LastEvaluatedKey")
            if not last_key:
                break
        return items

    # ------------------------------------------------------------------
    # Sync from DynamoDB Local on startup
    # ------------------------------------------------------------------

    def import_existing(self, table_names: list[str]) -> None:
        """Register tables already present in DynamoDB Local as ACTIVE."""
        for name in table_names:
            if is_vera_internal(name):
                continue
            if name not in self._tables:
                self._tables[name] = "ACTIVE"
                logger.info(f"Imported existing table: {name} -> ACTIVE")

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_status(self, table_name: str) -> Optional[str]:
        return self._tables.get(table_name)

    def exists(self, table_name: str) -> bool:
        status = self._tables.get(table_name)
        return status is not None and status != "DELETING"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def check_action(self, action: str, table_name: str) -> Optional[str]:
        status = self._tables.get(table_name)
        if action == "CreateTable":
            if status is not None and status != "DELETING":
                return f"Table already exists: {table_name}"
            return None
        if status is None:
            return f"Table not found: {table_name}"
        blocked = _BLOCKED.get(status, set())
        if action in blocked:
            return (
                f"Table {table_name} is in state {status}, "
                f"which does not allow {action}"
            )
        return None

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def transition(self, table_name: str, new_status: str) -> None:
        current = self._tables.get(table_name)
        allowed = _TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition for {table_name}: {current} -> {new_status}"
            )
        self._tables[table_name] = new_status
        logger.info(f"Table {table_name}: {current} -> {new_status}")

    def register(self, table_name: str, status: str = "CREATING") -> None:
        self._tables[table_name] = status
        logger.info(f"Registered table {table_name} as {status}")

    def remove(self, table_name: str) -> None:
        self._tables.pop(table_name, None)
        self.table_ids.pop(table_name, None)
        self.table_throughput.pop(table_name, None)
        self.replicas.pop(table_name, None)
        self.pitr_enabled.pop(table_name, None)
        # Clean up contributor insights records for this table
        ci_keys = [k for k in self.contributor_insights if k[0] == table_name]
        for k in ci_keys:
            del self.contributor_insights[k]
            _, index_name = k
            self._ddb("DeleteItem", {
                "TableName": VERA_META_TABLE,
                "Key": {
                    "pk": {"S": f"ci#{table_name}"},
                    "sk": {"S": f"index#{index_name}"},
                },
            })
        logger.info(f"Removed table {table_name} from state machine")

    def reset(self) -> None:
        """Clear all in-memory vera state (backups, replicas, PITR, CI, tags).
        Used by the eval harness between test runs via /vera/reset-state.
        """
        self._tables.clear()
        self.table_ids.clear()
        self.table_throughput.clear()
        self.backups.clear()
        self.replicas.clear()
        self.pitr_enabled.clear()
        self.contributor_insights.clear()
        self.tags.clear()
        # Clear persisted metadata from __vera_meta__ table
        try:
            items = self._scan_all(VERA_META_TABLE)
            for item in items:
                self._ddb("DeleteItem", {
                    "TableName": VERA_META_TABLE,
                    "Key": {"pk": item["pk"], "sk": item["sk"]},
                })
        except Exception as e:
            logger.warning(f"vera/reset-state: failed to clear meta: {e}")
        logger.info("vera state reset")

    # ------------------------------------------------------------------
    # Backup helpers (persistent)
    # ------------------------------------------------------------------

    @staticmethod
    def _make_backup_arn(table_name: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = uuid.uuid4().hex[:8]
        return (
            f"arn:aws:dynamodb:us-east-1:123456789012:"
            f"table/{table_name}/backup/{ts}-{uid}"
        )

    @staticmethod
    def _make_backup_table_name() -> str:
        return f"{VERA_BK_PREFIX}{uuid.uuid4().hex[:12]}__"

    def create_backup(
        self,
        table_name: str,
        backup_name: str,
        backup_type: str,
        table_description: Dict[str, Any],
    ) -> BackupRecord:
        """Create backup: clone table in DDB Local, store metadata in __vera_meta__."""
        arn = self._make_backup_arn(table_name)
        bk_table = self._make_backup_table_name()

        # Clone the table schema into a backup table
        key_schema = table_description.get("KeySchema", [])
        attr_defs = table_description.get("AttributeDefinitions", [])
        create_payload: dict = {
            "TableName": bk_table,
            "KeySchema": key_schema,
            "AttributeDefinitions": attr_defs,
            "BillingMode": "PAY_PER_REQUEST",
        }
        # Clone GSIs (strip runtime fields)
        gsis = table_description.get("GlobalSecondaryIndexes", [])
        if gsis:
            create_payload["GlobalSecondaryIndexes"] = [
                {
                    "IndexName": g["IndexName"],
                    "KeySchema": g["KeySchema"],
                    "Projection": g["Projection"],
                }
                for g in gsis
            ]
        lsis = table_description.get("LocalSecondaryIndexes", [])
        if lsis:
            create_payload["LocalSecondaryIndexes"] = [
                {
                    "IndexName": l["IndexName"],
                    "KeySchema": l["KeySchema"],
                    "Projection": l["Projection"],
                }
                for l in lsis
            ]

        status, body = self._ddb("CreateTable", create_payload)
        if status != 200:
            raise RuntimeError(f"Failed to create backup table {bk_table}: {body}")

        # Copy all items via scan + batch write
        item_count, size_bytes = self._copy_table_items(table_name, bk_table)

        billing = table_description.get("BillingModeSummary", {}).get(
            "BillingMode",
            table_description.get("BillingMode", "PROVISIONED"),
        )

        rec = BackupRecord(
            backup_arn=arn,
            backup_name=backup_name,
            backup_type=backup_type,
            table_name=table_name,
            table_arn=table_description.get("TableArn", ""),
            table_id=table_description.get("TableId", ""),
            key_schema=key_schema,
            attribute_definitions=attr_defs,
            billing_mode=billing,
            provisioned_throughput=table_description.get("ProvisionedThroughput"),
            global_secondary_indexes=gsis,
            local_secondary_indexes=lsis,
            sse_description=table_description.get("SSEDescription"),
            stream_specification=table_description.get("StreamSpecification"),
            backup_table=bk_table,
            item_count=item_count,
            backup_size_bytes=size_bytes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.backups[arn] = rec

        # Persist metadata to __vera_meta__
        self._ddb("PutItem", {
            "TableName": VERA_META_TABLE,
            "Item": rec.to_meta_item(),
        })
        logger.info(f"Backup created: {arn} ({item_count} items) -> {bk_table}")
        return rec

    @staticmethod
    def _item_size_bytes(item: dict) -> int:
        """Approximate DynamoDB item size in bytes (JSON serialization of the item)."""
        return len(json.dumps(item).encode("utf-8"))

    def _copy_table_items(self, src: str, dst: str) -> tuple[int, int]:
        """Copy all items from src table to dst table. Returns (item_count, size_bytes)."""
        count = 0
        size_bytes = 0
        last_key = None
        while True:
            scan_payload: dict = {"TableName": src}
            if last_key:
                scan_payload["ExclusiveStartKey"] = last_key
            status, body = self._ddb("Scan", scan_payload)
            if status != 200:
                break
            items = body.get("Items", [])
            # Batch write in chunks of 25
            for i in range(0, len(items), 25):
                batch = items[i:i + 25]
                self._ddb("BatchWriteItem", {
                    "RequestItems": {
                        dst: [{"PutRequest": {"Item": item}} for item in batch]
                    }
                })
                count += len(batch)
                size_bytes += sum(self._item_size_bytes(it) for it in batch)
            last_key = body.get("LastEvaluatedKey")
            if not last_key:
                break
        return count, size_bytes

    def get_backup(self, backup_arn: str) -> Optional[BackupRecord]:
        rec = self.backups.get(backup_arn)
        if rec and rec.status == "DELETED":
            return None
        return rec

    def delete_backup(self, backup_arn: str) -> Optional[BackupRecord]:
        rec = self.backups.get(backup_arn)
        if not rec:
            return None
        rec.status = "DELETED"
        # Update metadata in __vera_meta__
        self._ddb("UpdateItem", {
            "TableName": VERA_META_TABLE,
            "Key": {"pk": {"S": f"backup#{backup_arn}"}, "sk": {"S": "meta"}},
            "UpdateExpression": "SET #s = :s",
            "ExpressionAttributeNames": {"#s": "status"},
            "ExpressionAttributeValues": {":s": {"S": "DELETED"}},
        })
        # Delete the backup clone table
        self._ddb("DeleteTable", {"TableName": rec.backup_table})
        logger.info(f"Backup deleted: {backup_arn}")
        return rec

    @staticmethod
    def _to_iso(value) -> str:
        """Convert epoch number or ISO string to ISO-8601 for comparison."""
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        return str(value)

    def list_backups(
        self,
        table_name: Optional[str] = None,
        backup_type: Optional[str] = None,
        time_lower: Optional[str] = None,
        time_upper: Optional[str] = None,
        exclusive_start_arn: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[List[BackupRecord], Optional[str]]:
        records = [r for r in self.backups.values() if r.status != "DELETED"]
        if table_name:
            records = [r for r in records if r.table_name == table_name]
        if backup_type and backup_type != "ALL":
            records = [r for r in records if r.backup_type == backup_type]
        if time_lower:
            lower_iso = self._to_iso(time_lower)
            records = [r for r in records if r.created_at >= lower_iso]
        if time_upper:
            upper_iso = self._to_iso(time_upper)
            records = [r for r in records if r.created_at <= upper_iso]
        records.sort(key=lambda r: r.created_at)
        if exclusive_start_arn:
            idx = next(
                (i for i, r in enumerate(records) if r.backup_arn == exclusive_start_arn),
                -1,
            )
            records = records[idx + 1:]
        page = records[:limit]
        last = page[-1].backup_arn if len(records) > limit else None
        return page, last

    def get_backup_items(self, backup_arn: str) -> List[Dict[str, Any]]:
        """Read all items from a backup's clone table."""
        rec = self.get_backup(backup_arn)
        if not rec:
            return []
        return self._scan_all(rec.backup_table)

    # ------------------------------------------------------------------
    # PITR config (persistent)
    # ------------------------------------------------------------------

    def set_pitr(self, table_name: str, enabled: bool) -> None:
        self.pitr_enabled[table_name] = enabled
        self._ddb("PutItem", {
            "TableName": VERA_META_TABLE,
            "Item": {
                "pk": {"S": f"pitr#{table_name}"},
                "sk": {"S": "config"},
                "enabled": {"BOOL": enabled},
            },
        })
        logger.info(f"PITR {'enabled' if enabled else 'disabled'} for {table_name}")

    def get_pitr(self, table_name: str) -> bool:
        return self.pitr_enabled.get(table_name, False)

    # ------------------------------------------------------------------
    # PITR write log (persistent)
    # ------------------------------------------------------------------

    def log_write_op(self, table_name: str, action: str, request_body: dict) -> None:
        """Log a write operation for PITR replay."""
        if not self.pitr_enabled.get(table_name, False):
            return
        now = datetime.now(timezone.utc)
        seq = now.strftime("%Y%m%dT%H%M%S.%f") + "-" + uuid.uuid4().hex[:6]
        self._ddb("PutItem", {
            "TableName": VERA_PITR_LOG_TABLE,
            "Item": {
                "table_name": {"S": table_name},
                "seq": {"S": seq},
                "action": {"S": action},
                "request_body": {"S": json.dumps(request_body)},
                "timestamp": {"S": now.isoformat()},
            },
        })

    def get_pitr_log(
        self, table_name: str, up_to: str
    ) -> List[Dict[str, Any]]:
        """
        Get all PITR log entries for a table up to the given ISO-8601 timestamp.
        Returns list of {action, request_body, timestamp} dicts, sorted by seq.
        """
        entries = []
        last_key = None
        while True:
            payload: dict = {
                "TableName": VERA_PITR_LOG_TABLE,
                "KeyConditionExpression": "table_name = :tn",
                "ExpressionAttributeValues": {":tn": {"S": table_name}},
            }
            if last_key:
                payload["ExclusiveStartKey"] = last_key
            status, body = self._ddb("Query", payload)
            if status != 200:
                break
            for item in body.get("Items", []):
                ts = item.get("timestamp", {}).get("S", "")
                if ts <= up_to:
                    entries.append({
                        "action": item["action"]["S"],
                        "request_body": json.loads(item["request_body"]["S"]),
                        "timestamp": ts,
                    })
            last_key = body.get("LastEvaluatedKey")
            if not last_key:
                break
        entries.sort(key=lambda e: e["timestamp"])
        return entries

    # ------------------------------------------------------------------
    # Global table replica helpers (persistent)
    # ------------------------------------------------------------------

    def get_replicas(self, table_name: str) -> Dict[str, ReplicaRecord]:
        return self.replicas.get(table_name, {})

    def add_replica(self, table_name: str, replica: ReplicaRecord) -> Optional[str]:
        existing = self.replicas.setdefault(table_name, {})
        if replica.region_name in existing:
            return f"Replica in region '{replica.region_name}' already exists for table '{table_name}'"
        existing[replica.region_name] = replica
        self._persist_replica(table_name, replica)
        logger.info(f"Replica added: {table_name} -> {replica.region_name}")
        return None

    def delete_replica(self, table_name: str, region_name: str) -> Optional[str]:
        existing = self.replicas.get(table_name, {})
        if region_name not in existing:
            return f"Replica in region '{region_name}' does not exist for table '{table_name}'"
        del existing[region_name]
        self._ddb("DeleteItem", {
            "TableName": VERA_META_TABLE,
            "Key": {
                "pk": {"S": f"replica#{table_name}"},
                "sk": {"S": f"region#{region_name}"},
            },
        })
        logger.info(f"Replica removed: {table_name} -> {region_name}")
        return None

    def _persist_replica(self, table_name: str, replica: ReplicaRecord) -> None:
        data = {
            "replica_status": replica.replica_status,
            "kms_master_key_id": replica.kms_master_key_id,
            "provisioned_throughput_override": replica.provisioned_throughput_override,
            "global_secondary_indexes": replica.global_secondary_indexes,
            "autoscaling_read": replica.autoscaling_read,
            "autoscaling_write": replica.autoscaling_write,
        }
        self._ddb("PutItem", {
            "TableName": VERA_META_TABLE,
            "Item": {
                "pk": {"S": f"replica#{table_name}"},
                "sk": {"S": f"region#{replica.region_name}"},
                "data_json": {"S": json.dumps(data)},
            },
        })

    # ------------------------------------------------------------------
    # Contributor Insights (persistent)
    # ------------------------------------------------------------------

    def set_contributor_insights(
        self, table_name: str, index_name: Optional[str], status: str
    ) -> None:
        key = (table_name, index_name or "__table__")
        self.contributor_insights[key] = status
        self._ddb("PutItem", {
            "TableName": VERA_META_TABLE,
            "Item": {
                "pk": {"S": f"ci#{table_name}"},
                "sk": {"S": f"index#{index_name or '__table__'}"},
                "ci_status": {"S": status},
            },
        })

    def get_contributor_insights(
        self, table_name: str, index_name: Optional[str]
    ) -> str:
        key = (table_name, index_name or "__table__")
        return self.contributor_insights.get(key, "DISABLED")

    def list_contributor_insights(
        self, table_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for (tn, idx), status in self.contributor_insights.items():
            if table_name and tn != table_name:
                continue
            # Real AWS only returns ENABLED entries in ListContributorInsights
            if status not in ("ENABLED", "ENABLING"):
                continue
            entry: Dict[str, Any] = {
                "TableName": tn,
                "ContributorInsightsStatus": status,
            }
            if idx != "__table__":
                entry["IndexName"] = idx
            results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def tag_resource(self, table_name: str, tags: List[Dict[str, str]]) -> None:
        if table_name not in self.tags:
            self.tags[table_name] = {}
        for tag in tags:
            self.tags[table_name][tag["Key"]] = tag["Value"]

    def untag_resource(self, table_name: str, tag_keys: List[str]) -> None:
        if table_name in self.tags:
            for key in tag_keys:
                self.tags[table_name].pop(key, None)

    def list_tags(self, table_name: str) -> List[Dict[str, str]]:
        return [
            {"Key": k, "Value": v}
            for k, v in self.tags.get(table_name, {}).items()
        ]
