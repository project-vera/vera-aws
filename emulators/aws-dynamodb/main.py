"""
vera-dynamodb: DynamoDB proxy with state machine enforcement.

Architecture:
  Client -> vera-dynamodb (this server, port 5005)
               |
               +--> [State Machine] for table lifecycle, backup, replica, PITR
               |
               +--> [DynamoDB Local] for all data ops (port 8000)

Protocol: POST / with X-Amz-Target header + JSON body (application/x-amz-json-1.0)

What vera handles natively (never forwarded to DynamoDB Local):
  Backup:       CreateBackup, DeleteBackup, DescribeBackup, ListBackups,
                RestoreTableFromBackup, RestoreTableToPointInTime
  PITR:         DescribeContinuousBackups, UpdateContinuousBackups
  Global table: CreateGlobalTable, DescribeGlobalTable, ListGlobalTables,
                UpdateGlobalTable (v1 legacy API)
  Augmented:    UpdateTable (intercepts ReplicaUpdates for v2 global tables)
                DescribeTable (injects Replicas field)
                DeleteTable (patches TableStatus -> DELETING in response)
                ListTables (hides __vera_*__ internal tables)

PITR write logging:
  PutItem, UpdateItem, DeleteItem, BatchWriteItem, TransactWriteItems
  are proxied to DynamoDB Local and then logged to __vera_pitr_log__
  when the target table has PITR enabled.
"""

import json
import logging
import os
import socket
import subprocess
import time
from typing import Optional

import requests
from flask import Flask, request, Response

from emulator_core.state_machine import (
    ReplicaRecord, TableStateMachine, is_vera_internal,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera-dynamodb")

app = Flask(__name__)

DYNAMODB_LOCAL_URL = os.environ.get("DYNAMODB_LOCAL_URL", "http://localhost:8000")

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_JAR = os.path.join(_HERE, "dynamodb-local", "DynamoDBLocal.jar")
_DEFAULT_LIB = os.path.join(_HERE, "dynamodb-local", "DynamoDBLocal_lib")

sm = TableStateMachine()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _table_name_from_arn(arn: str) -> Optional[str]:
    """Extract table name from a DynamoDB table ARN (any region/account)."""
    if not arn.startswith("arn:"):
        return None
    parts = arn.split(":table/")
    if len(parts) != 2:
        return None
    return parts[1].split("/")[0] or None


def _fix_ddblocal_arns(content: bytes) -> bytes:
    """Replace DynamoDB Local's fake ARN components with standard values."""
    return (
        content
        .replace(b":ddblocal:", b":us-east-1:")
        .replace(b":000000000000:", b":123456789012:")
    )


def json_error(code: str, message: str, http_status: int = 400) -> Response:
    body = json.dumps({"__type": code, "message": message})
    return Response(body, status=http_status, mimetype="application/x-amz-json-1.0")


def json_ok(data: dict) -> Response:
    return Response(json.dumps(data), status=200, mimetype="application/x-amz-json-1.0")


def proxy(raw_body: bytes) -> Response:
    """Forward the request as-is to DynamoDB Local and return its response."""
    headers = {k: v for k, v in request.headers if k != "Host"}
    try:
        resp = requests.post(
            DYNAMODB_LOCAL_URL,
            data=raw_body,
            headers=headers,
            timeout=10,
        )
        content = _fix_ddblocal_arns(resp.content)
        return Response(content, status=resp.status_code, mimetype="application/x-amz-json-1.0")
    except requests.exceptions.ConnectionError:
        return json_error(
            "ServiceUnavailableException",
            f"DynamoDB Local not reachable at {DYNAMODB_LOCAL_URL}",
            503,
        )


def _ddb_local_call(action: str, payload: dict) -> tuple[int, dict]:
    """Make a direct call to DynamoDB Local. Returns (status_code, body_dict)."""
    headers = {
        "X-Amz-Target": f"DynamoDB_20120810.{action}",
        "Content-Type": "application/x-amz-json-1.0",
        "Authorization": (
            "AWS4-HMAC-SHA256 Credential=fake/20000101/us-east-1/dynamodb/aws4_request,"
            " SignedHeaders=host, Signature=fake"
        ),
    }
    try:
        resp = requests.post(
            DYNAMODB_LOCAL_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        return resp.status_code, resp.json() if resp.content else {}
    except requests.exceptions.ConnectionError:
        return 503, {"__type": "ServiceUnavailableException",
                     "message": f"DynamoDB Local not reachable at {DYNAMODB_LOCAL_URL}"}


def _describe_table_from_local(table_name: str) -> tuple[int, dict]:
    status, body = _ddb_local_call("DescribeTable", {"TableName": table_name})
    if status != 200:
        return status, body
    table_desc = body.get("Table", {})
    # Inject vera-generated TableId if DDB Local returned empty string
    if not table_desc.get("TableId") and table_name in sm.table_ids:
        table_desc["TableId"] = sm.table_ids[table_name]
    # Inject BillingModeSummary if DDB Local omitted it
    if "BillingModeSummary" not in table_desc:
        billing = table_desc.get("BillingMode", "PROVISIONED")
        table_desc["BillingModeSummary"] = {"BillingMode": billing}
    # Normalize ProvisionedThroughput fields
    if "ProvisionedThroughput" in table_desc:
        _normalize_provisioned_throughput(table_desc["ProvisionedThroughput"])
    for gsi in table_desc.get("GlobalSecondaryIndexes", []):
        if "ProvisionedThroughput" in gsi:
            _normalize_provisioned_throughput(gsi["ProvisionedThroughput"])
        gsi.setdefault("IndexSizeBytes", 0)
        gsi.setdefault("ItemCount", 0)
    for lsi in table_desc.get("LocalSecondaryIndexes", []):
        if "ProvisionedThroughput" in lsi:
            _normalize_provisioned_throughput(lsi["ProvisionedThroughput"])
    return 200, table_desc


# ------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------

def start_embedded_dynamodb_local() -> None:
    jar = os.environ.get("DYNAMODB_LOCAL_JAR", _DEFAULT_JAR)
    lib = os.environ.get("DYNAMODB_LOCAL_LIB", _DEFAULT_LIB)
    if not os.path.exists(jar):
        logger.warning(f"DynamoDB Local JAR not found at {jar}. Run install.sh first.")
        return

    port = int(DYNAMODB_LOCAL_URL.rsplit(":", 1)[-1])
    cmd = [
        "java",
        f"-Djava.library.path={lib}",
        "-jar", jar,
        "-inMemory",
        "-sharedDb",
        "-port", str(port),
    ]
    logger.info(f"Starting embedded DynamoDB Local: {' '.join(cmd)}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(30):
        try:
            s = socket.create_connection(("localhost", port), timeout=0.5)
            s.close()
            logger.info("Embedded DynamoDB Local is ready")
            return
        except OSError:
            time.sleep(0.5)

    logger.error("Embedded DynamoDB Local did not become ready in time")


def sync_from_dynamodb_local() -> None:
    try:
        status, body = _ddb_local_call("ListTables", {})
        if status == 200:
            table_names = body.get("TableNames", [])
            sm.import_existing(table_names)
            # Cache provisioned throughput for existing tables
            for name in table_names:
                if is_vera_internal(name):
                    continue
                _, td = _describe_table_from_local(name)
                pt = td.get("ProvisionedThroughput", {})
                sm.table_throughput[name] = {
                    "ReadCapacityUnits": pt.get("ReadCapacityUnits", 5),
                    "WriteCapacityUnits": pt.get("WriteCapacityUnits", 5),
                }
            logger.info(f"Synced {len([n for n in table_names if not is_vera_internal(n)])} tables from DynamoDB Local")
        else:
            logger.warning(f"ListTables sync failed: {status}")
    except Exception as e:
        logger.warning(f"Could not sync from DynamoDB Local: {e}")


# ------------------------------------------------------------------
# Table lifecycle handlers
# ------------------------------------------------------------------

def _normalize_provisioned_throughput(pt: dict) -> dict:
    """Ensure ProvisionedThroughput includes NumberOfDecreasesToday (DDB Local may omit it)."""
    if pt and "NumberOfDecreasesToday" not in pt:
        pt["NumberOfDecreasesToday"] = 0
    return pt


def _patch_consumed_capacity(resp_body: dict) -> None:
    """Inject ReadCapacityUnits/WriteCapacityUnits into ConsumedCapacity entries that lack them.

    DDB Local returns ConsumedCapacity.CapacityUnits but omits the per-type breakdown.
    We fill in from the stored provisioned throughput for the table.
    """
    for entry in resp_body.get("ConsumedCapacity", []):
        table_name = entry.get("TableName", "")
        pt = sm.table_throughput.get(table_name)
        if pt is None:
            # Try to fetch from DDB Local if not cached
            _, td = _describe_table_from_local(table_name)
            pt = td.get("ProvisionedThroughput", {})
        if pt:
            entry.setdefault("ReadCapacityUnits", pt.get("ReadCapacityUnits", 5))
            entry.setdefault("WriteCapacityUnits", pt.get("WriteCapacityUnits", 5))


def _maybe_patch_consumed_capacity(resp: Response) -> Response:
    """If the response has ConsumedCapacity, patch in RCU/WCU from stored throughput."""
    if resp.status_code != 200:
        return resp
    try:
        resp_body = json.loads(resp.get_data())
        if "ConsumedCapacity" not in resp_body:
            return resp
        _patch_consumed_capacity(resp_body)
        return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
    except Exception:
        return resp


def _augment_create_table_response(resp_body: dict, request_body: dict) -> dict:
    import uuid as _uuid
    desc = resp_body.get("TableDescription", {})

    # Inject a real UUID for TableId (DDB Local returns empty string)
    table_name = desc.get("TableName", request_body.get("TableName", ""))
    if not desc.get("TableId"):
        table_id = sm.table_ids.get(table_name)
        if not table_id:
            table_id = str(_uuid.uuid4())
            sm.table_ids[table_name] = table_id
        desc["TableId"] = table_id

    # Inject BillingModeSummary if missing
    if "BillingModeSummary" not in desc:
        billing = request_body.get("BillingMode", "PROVISIONED")
        desc["BillingModeSummary"] = {"BillingMode": billing}

    # Store provisioned throughput for ConsumedCapacity patching
    pt = desc.get("ProvisionedThroughput") or request_body.get("ProvisionedThroughput") or {}
    sm.table_throughput[table_name] = {
        "ReadCapacityUnits": pt.get("ReadCapacityUnits", 5),
        "WriteCapacityUnits": pt.get("WriteCapacityUnits", 5),
    }

    # Normalize ProvisionedThroughput (add NumberOfDecreasesToday if missing)
    if "ProvisionedThroughput" in desc:
        _normalize_provisioned_throughput(desc["ProvisionedThroughput"])
    for gsi in desc.get("GlobalSecondaryIndexes", []):
        if "ProvisionedThroughput" in gsi:
            _normalize_provisioned_throughput(gsi["ProvisionedThroughput"])
        gsi.setdefault("IndexSizeBytes", 0)
        gsi.setdefault("ItemCount", 0)
    for lsi in desc.get("LocalSecondaryIndexes", []):
        if "ProvisionedThroughput" in lsi:
            _normalize_provisioned_throughput(lsi["ProvisionedThroughput"])

    sse_spec = request_body.get("SSESpecification", {})
    if sse_spec.get("Enabled") and "SSEDescription" not in desc:
        sse_entry = {"Status": "ENABLED", "SSEType": sse_spec.get("SSEType", "AES256")}
        key_id = sse_spec.get("KMSMasterKeyId")
        if key_id and not key_id.startswith("arn:"):
            key_id = f"arn:aws:kms:us-east-1:123456789012:key/{key_id}"
        if key_id:
            sse_entry["KMSMasterKeyArn"] = key_id
        desc["SSEDescription"] = sse_entry

    table_class = request_body.get("TableClass")
    if table_class and "TableClassSummary" not in desc:
        desc["TableClassSummary"] = {"TableClass": table_class}

    resp_body["TableDescription"] = desc
    return resp_body


def handle_create_table(body: dict, raw_body: bytes) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if is_vera_internal(table_name):
        return json_error("ValidationException", f"Table name '{table_name}' is reserved")

    err = sm.check_action("CreateTable", table_name)
    if err:
        return json_error("ResourceInUseException", err)

    sm.register(table_name, "CREATING")
    resp = proxy(raw_body)

    if resp.status_code == 200:
        sm.transition(table_name, "ACTIVE")
        try:
            resp_body = json.loads(resp.get_data())
            resp_body = _augment_create_table_response(resp_body, body)
            return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
        except Exception:
            pass
    else:
        sm.remove(table_name)

    return resp


def handle_delete_table(body: dict, raw_body: bytes) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")

    err = sm.check_action("DeleteTable", table_name)
    if err:
        status = sm.get_status(table_name)
        if status is not None:
            return json_error("ResourceInUseException", err)
        # Table not in vera state — forward to DDB Local directly (may exist there after a reset)
        resp = proxy(raw_body)
        if resp.status_code == 200:
            try:
                resp_body = json.loads(resp.get_data())
                desc = resp_body.get("TableDescription", {})
                desc["TableStatus"] = "DELETING"
                resp_body["TableDescription"] = desc
                return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
            except Exception:
                pass
        return resp

    sm.transition(table_name, "DELETING")
    resp = proxy(raw_body)

    if resp.status_code == 200:
        sm.remove(table_name)
        # Patch response: DynamoDB Local returns ACTIVE, real AWS returns DELETING
        try:
            resp_body = json.loads(resp.get_data())
            desc = resp_body.get("TableDescription", {})
            desc["TableStatus"] = "DELETING"
            resp_body["TableDescription"] = desc
            return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
        except Exception:
            pass
    else:
        sm._tables[table_name] = "ACTIVE"
        logger.warning(f"DeleteTable failed for {table_name}, rolled back to ACTIVE")

    return resp


def handle_update_table(body: dict, raw_body: bytes) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")

    err = sm.check_action("UpdateTable", table_name)
    if err:
        status = sm.get_status(table_name)
        if status is None:
            return json_error("ResourceNotFoundException", err)
        return json_error("ResourceInUseException", err)

    replica_updates = body.pop("ReplicaUpdates", None)
    sse_spec = body.pop("SSESpecification", None)

    if replica_updates:
        for update in replica_updates:
            if "Create" in update:
                details = update["Create"]
                region = details.get("RegionName")
                if not region:
                    return json_error("ValidationException", "ReplicaUpdates.Create requires RegionName")
                replica = ReplicaRecord(
                    region_name=region,
                    kms_master_key_id=details.get("KMSMasterKeyId"),
                    provisioned_throughput_override=details.get("ProvisionedThroughputOverride"),
                    global_secondary_indexes=details.get("GlobalSecondaryIndexes"),
                )
                add_err = sm.add_replica(table_name, replica)
                if add_err:
                    return json_error("ValidationException", add_err)
            elif "Delete" in update:
                details = update["Delete"]
                region = details.get("RegionName")
                if not region:
                    return json_error("ValidationException", "ReplicaUpdates.Delete requires RegionName")
                del_err = sm.delete_replica(table_name, region)
                if del_err:
                    return json_error("ValidationException", del_err)

    # If nothing else to change after stripping ReplicaUpdates/SSESpecification,
    # return synthetic response (DDB Local would reject with "Nothing to update")
    remaining_keys = {k for k in body if k not in ("TableName",)}
    if not remaining_keys:
        status_code, table_desc = _describe_table_from_local(table_name)
        if status_code != 200:
            return json_error(
                table_desc.get("__type", "InternalFailure"),
                table_desc.get("message", "Failed to describe table"),
                status_code,
            )
        table_desc = _inject_replicas(table_desc, table_name)
        if sse_spec:
            table_desc["SSEDescription"] = {"Status": "UPDATING"}
        return json_ok({"TableDescription": table_desc})

    prev_status = sm.get_status(table_name)
    sm.transition(table_name, "UPDATING")

    raw_body = json.dumps(body).encode()
    resp = proxy(raw_body)

    if resp.status_code == 200:
        sm.transition(table_name, "ACTIVE")
        try:
            resp_body = json.loads(resp.get_data())
            desc = resp_body.get("TableDescription", {})
            if sse_spec:
                desc["SSEDescription"] = {"Status": "UPDATING"}
            # Inject TableId if missing
            tname = desc.get("TableName", table_name)
            if not desc.get("TableId") and tname in sm.table_ids:
                desc["TableId"] = sm.table_ids[tname]
            # Inject BillingModeSummary if missing
            if "BillingModeSummary" not in desc:
                billing = body.get("BillingMode") or desc.get("BillingMode", "PROVISIONED")
                desc["BillingModeSummary"] = {"BillingMode": billing}
            # Normalize ProvisionedThroughput fields
            if "ProvisionedThroughput" in desc:
                _normalize_provisioned_throughput(desc["ProvisionedThroughput"])
                # Update stored throughput when provisioned values change
                pt = desc["ProvisionedThroughput"]
                sm.table_throughput[table_name] = {
                    "ReadCapacityUnits": pt.get("ReadCapacityUnits", 5),
                    "WriteCapacityUnits": pt.get("WriteCapacityUnits", 5),
                }
            for gsi in desc.get("GlobalSecondaryIndexes", []):
                if "ProvisionedThroughput" in gsi:
                    _normalize_provisioned_throughput(gsi["ProvisionedThroughput"])
                # DDB Local omits IndexSizeBytes/ItemCount for CREATING GSIs
                gsi.setdefault("IndexSizeBytes", 0)
                gsi.setdefault("ItemCount", 0)
            resp_body["TableDescription"] = desc
            resp = Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
        except (json.JSONDecodeError, KeyError):
            pass
    else:
        sm._tables[table_name] = prev_status
        logger.warning(f"UpdateTable failed for {table_name}, rolled back to {prev_status}")

    return resp


def _inject_replicas(table_desc: dict, table_name: str) -> dict:
    replicas = sm.get_replicas(table_name)
    if replicas:
        table_desc["Replicas"] = [
            {
                "RegionName": r.region_name,
                "ReplicaStatus": r.replica_status,
                **({"KMSMasterKeyId": r.kms_master_key_id} if r.kms_master_key_id else {}),
                **({"ProvisionedThroughputOverride": r.provisioned_throughput_override}
                   if r.provisioned_throughput_override else {}),
                **({"GlobalSecondaryIndexes": r.global_secondary_indexes}
                   if r.global_secondary_indexes else {}),
            }
            for r in replicas.values()
        ]
    return table_desc


def handle_describe_table(body: dict, raw_body: bytes) -> Response:
    resp = proxy(raw_body)
    if resp.status_code != 200:
        return resp
    table_name = body.get("TableName", "")
    has_replicas = bool(sm.get_replicas(table_name))
    has_table_id = table_name in sm.table_ids
    if not has_replicas and not has_table_id:
        return resp
    try:
        resp_body = json.loads(resp.get_data())
        table_desc = resp_body.get("Table", {})
        if has_table_id and not table_desc.get("TableId"):
            table_desc["TableId"] = sm.table_ids[table_name]
        if has_replicas:
            table_desc = _inject_replicas(table_desc, table_name)
        resp_body["Table"] = table_desc
        return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
    except Exception:
        return resp


def handle_list_tables(body: dict, raw_body: bytes) -> Response:
    """Proxy ListTables, then strip __vera_*__ internal tables from the response."""
    resp = proxy(raw_body)
    if resp.status_code != 200:
        return resp
    try:
        resp_body = json.loads(resp.get_data())
        names = resp_body.get("TableNames", [])
        resp_body["TableNames"] = [n for n in names if not is_vera_internal(n)]
        return Response(json.dumps(resp_body), status=200, mimetype="application/x-amz-json-1.0")
    except Exception:
        return resp


# ------------------------------------------------------------------
# PITR write-op logging
# ------------------------------------------------------------------

# Actions that modify table data — we log them for PITR
_WRITE_ACTIONS = {"PutItem", "UpdateItem", "DeleteItem", "BatchWriteItem", "TransactWriteItems"}


def _extract_table_names_from_write(action: str, body: dict) -> list[str]:
    """Extract target table name(s) from a write request."""
    if action in ("PutItem", "UpdateItem", "DeleteItem"):
        tn = body.get("TableName")
        return [tn] if tn else []
    elif action == "BatchWriteItem":
        return list(body.get("RequestItems", {}).keys())
    elif action == "TransactWriteItems":
        tables = set()
        for item in body.get("TransactItems", []):
            for op in item.values():
                tn = op.get("TableName")
                if tn:
                    tables.add(tn)
        return list(tables)
    return []


def handle_write_op(action: str, body: dict, raw_body: bytes) -> Response:
    """Proxy write operations, then log to PITR if table has PITR enabled."""
    resp = proxy(raw_body)
    if resp.status_code != 200:
        return resp

    # Log for PITR
    table_names = _extract_table_names_from_write(action, body)
    for tn in table_names:
        if sm.get_pitr(tn):
            sm.log_write_op(tn, action, body)

    return resp


# ------------------------------------------------------------------
# Backup handlers
# ------------------------------------------------------------------

def handle_create_backup(body: dict) -> Response:
    table_name = body.get("TableName")
    backup_name = body.get("BackupName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not backup_name:
        return json_error("ValidationException", "BackupName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    status, table_desc = _describe_table_from_local(table_name)
    if status != 200:
        return json_error(
            table_desc.get("__type", "InternalFailure"),
            table_desc.get("message", "Failed to describe table"),
            status,
        )

    rec = sm.create_backup(table_name, backup_name, "USER", table_desc)

    return json_ok({
        "BackupDetails": {
            "BackupArn": rec.backup_arn,
            "BackupName": rec.backup_name,
            "BackupStatus": rec.status,
            "BackupType": rec.backup_type,
            "BackupCreationDateTime": rec.created_at,
            "BackupSizeBytes": rec.backup_size_bytes,
            "TableArn": rec.table_arn,
            "TableName": rec.table_name,
        }
    })


def handle_delete_backup(body: dict) -> Response:
    backup_arn = body.get("BackupArn")
    if not backup_arn:
        return json_error("ValidationException", "BackupArn is required")

    rec = sm.get_backup(backup_arn)
    if not rec:
        return json_error("BackupNotFoundException", f"Backup '{backup_arn}' not found")

    sm.delete_backup(backup_arn)

    return json_ok({
        "BackupDescription": {
            "BackupDetails": {
                "BackupArn": rec.backup_arn,
                "BackupName": rec.backup_name,
                "BackupStatus": "DELETED",
                "BackupType": rec.backup_type,
                "BackupCreationDateTime": rec.created_at,
                "BackupSizeBytes": rec.backup_size_bytes,
            },
            "SourceTableDetails": {
                "TableName": rec.table_name,
                "TableArn": rec.table_arn,
                "TableId": rec.table_id,
                "KeySchema": rec.key_schema,
                "AttributeDefinitions": rec.attribute_definitions,
                "BillingMode": rec.billing_mode,
                "ProvisionedThroughput": rec.provisioned_throughput or {},
                "TableCreationDateTime": rec.created_at,
                "ItemCount": rec.item_count,
                "TableSizeBytes": rec.backup_size_bytes,
            },
            "SourceTableFeatureDetails": {
                "GlobalSecondaryIndexes": rec.global_secondary_indexes,
                "LocalSecondaryIndexes": rec.local_secondary_indexes,
                **({"SSEDescription": rec.sse_description} if rec.sse_description else {}),
                **({"StreamDescription": rec.stream_specification} if rec.stream_specification else {}),
            },
        }
    })


def handle_describe_backup(body: dict) -> Response:
    backup_arn = body.get("BackupArn")
    if not backup_arn:
        return json_error("ValidationException", "BackupArn is required")

    rec = sm.get_backup(backup_arn)
    if not rec:
        return json_error("BackupNotFoundException", f"Backup '{backup_arn}' not found")

    return json_ok({
        "BackupDescription": {
            "BackupDetails": {
                "BackupArn": rec.backup_arn,
                "BackupName": rec.backup_name,
                "BackupStatus": rec.status,
                "BackupType": rec.backup_type,
                "BackupCreationDateTime": rec.created_at,
                "BackupSizeBytes": rec.backup_size_bytes,
                "TableArn": rec.table_arn,
                "TableName": rec.table_name,
            },
            "SourceTableDetails": {
                "TableName": rec.table_name,
                "TableArn": rec.table_arn,
                "TableId": rec.table_id,
                "KeySchema": rec.key_schema,
                "AttributeDefinitions": rec.attribute_definitions,
                "BillingMode": rec.billing_mode,
                "ProvisionedThroughput": rec.provisioned_throughput or {},
                "TableCreationDateTime": rec.created_at,
                "ItemCount": rec.item_count,
                "TableSizeBytes": rec.backup_size_bytes,
            },
            "SourceTableFeatureDetails": {
                "GlobalSecondaryIndexes": rec.global_secondary_indexes,
                "LocalSecondaryIndexes": rec.local_secondary_indexes,
                **({"SSEDescription": rec.sse_description} if rec.sse_description else {}),
                **({"StreamDescription": rec.stream_specification} if rec.stream_specification else {}),
            },
        }
    })


def handle_list_backups(body: dict) -> Response:
    table_name = body.get("TableName")

    page, last_arn = sm.list_backups(
        table_name=table_name,
        backup_type=body.get("BackupType"),
        time_lower=body.get("TimeRangeLowerBound"),
        time_upper=body.get("TimeRangeUpperBound"),
        exclusive_start_arn=body.get("ExclusiveStartBackupArn"),
        limit=int(body.get("Limit") or 100),
    )

    result: dict = {
        "BackupSummaries": [
            {
                "BackupArn": r.backup_arn,
                "BackupName": r.backup_name,
                "BackupStatus": r.status,
                "BackupType": r.backup_type,
                "BackupCreationDateTime": r.created_at,
                "BackupSizeBytes": r.backup_size_bytes,
                "TableArn": r.table_arn,
                "TableName": r.table_name,
                "TableId": r.table_id,
            }
            for r in page
        ]
    }
    if last_arn:
        result["LastEvaluatedBackupArn"] = last_arn

    return json_ok(result)


def handle_restore_table_from_backup(body: dict) -> Response:
    backup_arn = body.get("BackupArn")
    target_name = body.get("TargetTableName")
    if not backup_arn:
        return json_error("ValidationException", "BackupArn is required")
    if not target_name:
        return json_error("ValidationException", "TargetTableName is required")

    rec = sm.get_backup(backup_arn)
    if not rec:
        return json_error("BackupNotFoundException", f"Backup '{backup_arn}' not found")

    if sm.exists(target_name):
        return json_error("TableAlreadyExistsException", f"Table '{target_name}' already exists")

    table_desc = _restore_from_schema_and_items(
        target_name, rec, sm.get_backup_items(backup_arn)
    )
    if isinstance(table_desc, Response):
        return table_desc

    return json_ok({
        "TableDescription": {
            **table_desc,
            "RestoreSummary": {
                "SourceBackupArn": backup_arn,
                "SourceTableArn": rec.table_arn,
                "RestoreDateTime": rec.created_at,
                "RestoreInProgress": False,
            },
        }
    })


def handle_restore_table_to_point_in_time(body: dict) -> Response:
    source_name = body.get("SourceTableName")
    target_name = body.get("TargetTableName")
    restore_date = body.get("RestoreDateTime")
    use_latest = body.get("UseLatestRestorableTime", False)

    if not source_name:
        return json_error("ValidationException", "SourceTableName is required")
    if not target_name:
        return json_error("ValidationException", "TargetTableName is required")
    if not restore_date and not use_latest:
        return json_error("ValidationException", "Either RestoreDateTime or UseLatestRestorableTime is required")

    if not sm.get_pitr(source_name):
        return json_error(
            "PointInTimeRecoveryUnavailableException",
            f"Point in time recovery is not enabled for table '{source_name}'",
        )

    if sm.exists(target_name):
        return json_error("TableAlreadyExistsException", f"Table '{target_name}' already exists")

    # Get source table schema
    status, src_desc = _describe_table_from_local(source_name)
    if status != 200:
        return json_error(
            src_desc.get("__type", "InternalFailure"),
            src_desc.get("message", ""),
            status,
        )

    # Determine restore point
    if use_latest:
        restore_ts = datetime.now(timezone.utc).isoformat()
    else:
        # restore_date can be epoch float or ISO string
        if isinstance(restore_date, (int, float)):
            restore_ts = datetime.fromtimestamp(restore_date, tz=timezone.utc).isoformat()
        else:
            restore_ts = str(restore_date)

    # Create a temporary BackupRecord-like object for _restore_from_schema_and_items
    class _FakeRec:
        pass
    fake = _FakeRec()
    fake.key_schema = src_desc.get("KeySchema", [])
    fake.attribute_definitions = src_desc.get("AttributeDefinitions", [])
    billing = src_desc.get("BillingModeSummary", {}).get("BillingMode")
    if not billing:
        billing = src_desc.get("BillingMode")
    if not billing:
        # Infer from ProvisionedThroughput: non-zero RCU/WCU means PROVISIONED
        pt = src_desc.get("ProvisionedThroughput", {})
        if pt.get("ReadCapacityUnits", 0) > 0 or pt.get("WriteCapacityUnits", 0) > 0:
            billing = "PROVISIONED"
        else:
            billing = "PAY_PER_REQUEST"
    fake.billing_mode = billing
    fake.provisioned_throughput = src_desc.get("ProvisionedThroughput")
    fake.global_secondary_indexes = src_desc.get("GlobalSecondaryIndexes", [])
    fake.local_secondary_indexes = src_desc.get("LocalSecondaryIndexes", [])
    fake.stream_specification = src_desc.get("StreamSpecification")
    fake.table_arn = src_desc.get("TableArn", "")

    # Strategy: create empty table, then replay PITR log up to restore_ts
    table_desc = _restore_from_schema_and_items(target_name, fake, [])
    if isinstance(table_desc, Response):
        return table_desc

    # Replay PITR log entries
    log_entries = sm.get_pitr_log(source_name, restore_ts)
    _replay_pitr_log(target_name, source_name, log_entries)

    return json_ok({
        "TableDescription": {
            **table_desc,
            "RestoreSummary": {
                "SourceTableArn": fake.table_arn,
                "RestoreDateTime": restore_ts,
                "RestoreInProgress": False,
            },
        }
    })


def _restore_from_schema_and_items(target_name, rec, items) -> dict | Response:
    """Create a table from schema + write items. Returns table description dict or error Response."""
    create_payload: dict = {
        "TableName": target_name,
        "KeySchema": rec.key_schema,
        "AttributeDefinitions": rec.attribute_definitions,
        "BillingMode": getattr(rec, 'billing_mode', 'PAY_PER_REQUEST'),
    }
    billing = getattr(rec, 'billing_mode', 'PAY_PER_REQUEST')
    if billing == "PROVISIONED" and rec.provisioned_throughput:
        create_payload["ProvisionedThroughput"] = {
            "ReadCapacityUnits": rec.provisioned_throughput.get("ReadCapacityUnits", 5),
            "WriteCapacityUnits": rec.provisioned_throughput.get("WriteCapacityUnits", 5),
        }
    if rec.global_secondary_indexes:
        gsis = []
        for gsi in rec.global_secondary_indexes:
            entry = {
                "IndexName": gsi["IndexName"],
                "KeySchema": gsi["KeySchema"],
                "Projection": gsi["Projection"],
            }
            if billing == "PROVISIONED":
                pt = gsi.get("ProvisionedThroughput", {})
                entry["ProvisionedThroughput"] = {
                    "ReadCapacityUnits": pt.get("ReadCapacityUnits", 5),
                    "WriteCapacityUnits": pt.get("WriteCapacityUnits", 5),
                }
            gsis.append(entry)
        create_payload["GlobalSecondaryIndexes"] = gsis
    if rec.local_secondary_indexes:
        create_payload["LocalSecondaryIndexes"] = [
            {"IndexName": l["IndexName"], "KeySchema": l["KeySchema"], "Projection": l["Projection"]}
            for l in rec.local_secondary_indexes
        ]
    if getattr(rec, 'stream_specification', None):
        create_payload["StreamSpecification"] = rec.stream_specification

    sm.register(target_name, "CREATING")
    create_status, create_body = _ddb_local_call("CreateTable", create_payload)
    if create_status != 200:
        sm.remove(target_name)
        return json_error(
            create_body.get("__type", "InternalFailure"),
            create_body.get("message", "Failed to create table"),
            create_status,
        )
    sm.transition(target_name, "ACTIVE")

    # Write items in batches of 25
    if items:
        for i in range(0, len(items), 25):
            batch = items[i:i + 25]
            bw_status, bw_body = _ddb_local_call(
                "BatchWriteItem",
                {"RequestItems": {target_name: [{"PutRequest": {"Item": item}} for item in batch]}},
            )
            if bw_status != 200:
                logger.warning(f"Restore batch write failed at offset {i}: {bw_body}")

    # Inject vera TableId now so DescribeTable picks it up
    created_desc = create_body.get("TableDescription", {})
    if not created_desc.get("TableId") and target_name not in sm.table_ids:
        import uuid as _uuid
        sm.table_ids[target_name] = str(_uuid.uuid4())

    # Fetch the real description from DDB Local so all fields are populated
    _, result = _describe_table_from_local(target_name)
    # Patch TableStatus to ACTIVE (DDB Local may still show CREATING)
    result["TableStatus"] = "ACTIVE"
    return result


def _replay_pitr_log(target_name: str, source_name: str, log_entries: list) -> None:
    """Replay logged write operations against target table, remapping table names."""
    for entry in log_entries:
        action = entry["action"]
        req = entry["request_body"]

        if action in ("PutItem", "UpdateItem", "DeleteItem"):
            req["TableName"] = target_name
            _ddb_local_call(action, req)

        elif action == "BatchWriteItem":
            items = req.get("RequestItems", {})
            # Remap source table name to target
            if source_name in items:
                items[target_name] = items.pop(source_name)
            req["RequestItems"] = items
            _ddb_local_call(action, req)

        elif action == "TransactWriteItems":
            for item in req.get("TransactItems", []):
                for op in item.values():
                    if op.get("TableName") == source_name:
                        op["TableName"] = target_name
            _ddb_local_call(action, req)


# ------------------------------------------------------------------
# Continuous backup (PITR) config handlers
# ------------------------------------------------------------------

def handle_describe_continuous_backups(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    pitr_enabled = sm.get_pitr(table_name)
    pitr_status = "ENABLED" if pitr_enabled else "DISABLED"

    result: dict = {
        "ContinuousBackupsDescription": {
            "ContinuousBackupsStatus": "ENABLED",
            "PointInTimeRecoveryDescription": {
                "PointInTimeRecoveryStatus": pitr_status,
            },
        }
    }
    if pitr_enabled:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        result["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"].update({
            "EarliestRestorableDateTime": now.isoformat(),
            "LatestRestorableDateTime": now.isoformat(),
        })

    return json_ok(result)


def handle_update_continuous_backups(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    spec = body.get("PointInTimeRecoverySpecification", {})
    enabled = spec.get("PointInTimeRecoveryEnabled", False)

    sm.set_pitr(table_name, enabled)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    pitr_status = "ENABLED" if enabled else "DISABLED"
    pitr_desc: dict = {"PointInTimeRecoveryStatus": pitr_status}
    if enabled:
        pitr_desc["EarliestRestorableDateTime"] = now.isoformat()
        pitr_desc["LatestRestorableDateTime"] = now.isoformat()
    return json_ok({
        "ContinuousBackupsDescription": {
            "ContinuousBackupsStatus": "ENABLED",
            "PointInTimeRecoveryDescription": pitr_desc,
        }
    })


# ------------------------------------------------------------------
# Contributor Insights handlers
# ------------------------------------------------------------------

def handle_describe_contributor_insights(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    index_name = body.get("IndexName")
    ci_status = sm.get_contributor_insights(table_name, index_name)

    result: dict = {
        "TableName": table_name,
        "ContributorInsightsStatus": ci_status,
    }
    if index_name:
        result["IndexName"] = index_name
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if ci_status == "ENABLED":
        # Generate rule names matching AWS format (timestamp in milliseconds)
        ts_ms = int(now.timestamp() * 1000)
        prefixes = ["PKC", "SKC", "PKT", "SKT"]
        result["ContributorInsightsRuleList"] = [
            f"DynamoDBContributorInsights-{p}-{table_name}-{ts_ms}"
            for p in prefixes
        ]
        result["LastUpdateDateTime"] = now.isoformat()

    return json_ok(result)


def handle_update_contributor_insights(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    index_name = body.get("IndexName")
    action = body.get("ContributorInsightsAction")
    if action not in ("ENABLE", "DISABLE"):
        return json_error("ValidationException",
                          "ContributorInsightsAction must be ENABLE or DISABLE")

    new_status = "ENABLED" if action == "ENABLE" else "DISABLED"
    sm.set_contributor_insights(table_name, index_name, new_status)

    result: dict = {
        "TableName": table_name,
        "ContributorInsightsStatus": "ENABLING" if action == "ENABLE" else "DISABLING",
    }
    if index_name:
        result["IndexName"] = index_name

    return json_ok(result)


def handle_list_contributor_insights(body: dict) -> Response:
    table_name = body.get("TableName")
    max_results = int(body.get("MaxResults") or 100)
    next_token = body.get("NextToken")

    all_entries = sm.list_contributor_insights(table_name)
    all_entries.sort(key=lambda e: (e["TableName"], e.get("IndexName", "")))

    # Simple pagination by index
    start_idx = 0
    if next_token:
        try:
            start_idx = int(next_token)
        except ValueError:
            start_idx = 0

    page = all_entries[start_idx:start_idx + max_results]

    result: dict = {"ContributorInsightsSummaries": page}
    if start_idx + max_results < len(all_entries):
        result["NextToken"] = str(start_idx + max_results)

    return json_ok(result)


# ------------------------------------------------------------------
# DescribeEndpoints handler
# ------------------------------------------------------------------

def handle_describe_endpoints(body: dict) -> Response:
    host = os.environ.get("VERA_HOST", "127.0.0.1")
    port = os.environ.get("VERA_PORT", "5005")
    return json_ok({
        "Endpoints": [
            {
                "Address": f"{host}:{port}",
                "CachePeriodInMinutes": 1440,
            }
        ]
    })


# ------------------------------------------------------------------
# Global table settings handlers
# ------------------------------------------------------------------

def _build_replica_settings(table_name: str) -> list:
    """Build ReplicaSettings list from replica store + table throughput."""
    replicas = sm.get_replicas(table_name)
    if not replicas:
        return []

    # Get table throughput from DDB Local
    _, table_desc = _describe_table_from_local(table_name)
    pt = table_desc.get("ProvisionedThroughput", {})
    rcu = pt.get("ReadCapacityUnits", 0)
    wcu = pt.get("WriteCapacityUnits", 0)

    settings = []
    for r in replicas.values():
        settings.append({
            "RegionName": r.region_name,
            "ReplicaStatus": r.replica_status,
            "ReplicaProvisionedReadCapacityUnits": rcu,
            "ReplicaProvisionedReadCapacityAutoScalingSettings": {
                "AutoScalingDisabled": True,
            },
            "ReplicaProvisionedWriteCapacityUnits": wcu,
            "ReplicaProvisionedWriteCapacityAutoScalingSettings": {
                "AutoScalingDisabled": True,
            },
        })
    return settings


def handle_describe_global_table_settings(body: dict) -> Response:
    global_table_name = body.get("GlobalTableName")
    if not global_table_name:
        return json_error("ValidationException", "GlobalTableName is required")

    replicas = sm.get_replicas(global_table_name)
    if not replicas:
        return json_error("GlobalTableNotFoundException",
                          f"Global table '{global_table_name}' not found")

    return json_ok({
        "GlobalTableName": global_table_name,
        "ReplicaSettings": _build_replica_settings(global_table_name),
    })


def handle_update_global_table_settings(body: dict) -> Response:
    global_table_name = body.get("GlobalTableName")
    if not global_table_name:
        return json_error("ValidationException", "GlobalTableName is required")

    replicas = sm.get_replicas(global_table_name)
    if not replicas:
        return json_error("GlobalTableNotFoundException",
                          f"Global table '{global_table_name}' not found")

    # We accept the settings but don't actually apply throughput changes
    # to DynamoDB Local (it doesn't enforce throughput anyway).
    # Return current replica settings.
    return json_ok({
        "GlobalTableName": global_table_name,
        "ReplicaSettings": _build_replica_settings(global_table_name),
    })


# ------------------------------------------------------------------
# Table replica auto scaling handlers
# ------------------------------------------------------------------

_AUTOSCALING_ROLE_ARN = (
    "arn:aws:iam::123456789012:role/aws-service-role/"
    "dynamodb.application-autoscaling.amazonaws.com/"
    "AWSServiceRoleForApplicationAutoScaling_DynamoDBTable"
)


def _build_replica_autoscaling(table_name: str) -> list:
    """Build Replicas list for TableAutoScalingDescription."""
    replicas = sm.get_replicas(table_name)
    if not replicas:
        return []

    _, table_desc = _describe_table_from_local(table_name)
    pt = table_desc.get("ProvisionedThroughput", {})
    rcu = pt.get("ReadCapacityUnits", 5)
    wcu = pt.get("WriteCapacityUnits", 5)

    result = []
    for r in replicas.values():
        result.append({
            "RegionName": r.region_name,
            "GlobalSecondaryIndexes": [],
            "ReplicaProvisionedReadCapacityAutoScalingSettings": {
                "MinimumUnits": rcu,
                "MaximumUnits": 40000,
                "AutoScalingDisabled": False,
                "AutoScalingRoleArn": _AUTOSCALING_ROLE_ARN,
                "ScalingPolicies": [
                    {
                        "PolicyName": f"DynamoDBReadCapacityUtilization:table/{table_name}",
                        "TargetTrackingScalingPolicyConfiguration": {
                            "TargetValue": 70.0,
                        },
                    }
                ],
            },
            "ReplicaProvisionedWriteCapacityAutoScalingSettings": {
                "MinimumUnits": wcu,
                "MaximumUnits": 40000,
                "AutoScalingDisabled": False,
                "AutoScalingRoleArn": _AUTOSCALING_ROLE_ARN,
                "ScalingPolicies": [
                    {
                        "PolicyName": f"DynamoDBWriteCapacityUtilization:table/{table_name}",
                        "TargetTrackingScalingPolicyConfiguration": {
                            "TargetValue": 70.0,
                        },
                    }
                ],
            },
            "ReplicaStatus": r.replica_status,
        })
    return result


def handle_describe_table_replica_auto_scaling(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    return json_ok({
        "TableAutoScalingDescription": {
            "TableName": table_name,
            "TableStatus": sm.get_status(table_name) or "ACTIVE",
            "Replicas": _build_replica_autoscaling(table_name),
        }
    })


def handle_update_table_replica_auto_scaling(body: dict) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")
    if not sm.exists(table_name):
        return json_error("ResourceNotFoundException", f"Table '{table_name}' not found")

    # Read requested autoscaling overrides (not persisted, just reflected in response)
    rcu_update = body.get("ProvisionedReadCapacityAutoScalingUpdate", {})
    wcu_update = body.get("ProvisionedWriteCapacityAutoScalingUpdate", {})

    replicas = _build_replica_autoscaling(table_name)
    for replica in replicas:
        if rcu_update:
            s = replica["ReplicaProvisionedReadCapacityAutoScalingSettings"]
            if "MinimumUnits" in rcu_update:
                s["MinimumUnits"] = rcu_update["MinimumUnits"]
            if "MaximumUnits" in rcu_update:
                s["MaximumUnits"] = rcu_update["MaximumUnits"]
        if wcu_update:
            s = replica["ReplicaProvisionedWriteCapacityAutoScalingSettings"]
            if "MinimumUnits" in wcu_update:
                s["MinimumUnits"] = wcu_update["MinimumUnits"]
            if "MaximumUnits" in wcu_update:
                s["MaximumUnits"] = wcu_update["MaximumUnits"]

    return json_ok({
        "TableAutoScalingDescription": {
            "TableName": table_name,
            "TableStatus": sm.get_status(table_name) or "ACTIVE",
            "Replicas": replicas,
        }
    })


# ------------------------------------------------------------------
# V1 legacy global table handlers
# ------------------------------------------------------------------

def _global_table_description(global_table_name: str, replicas: dict) -> dict:
    """Build a GlobalTableDescription with all required fields."""
    from datetime import datetime, timezone
    return {
        "GlobalTableName": global_table_name,
        "GlobalTableArn": f"arn:aws:dynamodb::123456789012:global-table/{global_table_name}",
        "CreationDateTime": datetime.now(timezone.utc).isoformat(),
        "GlobalTableStatus": "ACTIVE",
        "ReplicationGroup": [
            {"RegionName": r.region_name, "ReplicaStatus": r.replica_status}
            for r in replicas.values()
        ],
    }


def handle_create_global_table(body: dict) -> Response:
    global_table_name = body.get("GlobalTableName")
    replication_group = body.get("ReplicationGroup", [])
    if not global_table_name:
        return json_error("ValidationException", "GlobalTableName is required")

    if not sm.exists(global_table_name):
        return json_error("ResourceNotFoundException",
                          f"Table '{global_table_name}' does not exist")

    existing = sm.get_replicas(global_table_name)
    if existing:
        return json_error("GlobalTableAlreadyExistsException",
                          f"Global table '{global_table_name}' already exists")

    for entry in replication_group:
        region = entry.get("RegionName")
        if not region:
            return json_error("ValidationException", "Each replica must have RegionName")
        sm.add_replica(global_table_name, ReplicaRecord(region_name=region))

    replicas = sm.get_replicas(global_table_name)
    return json_ok({"GlobalTableDescription": _global_table_description(global_table_name, replicas)})


def handle_describe_global_table(body: dict) -> Response:
    global_table_name = body.get("GlobalTableName")
    if not global_table_name:
        return json_error("ValidationException", "GlobalTableName is required")

    replicas = sm.get_replicas(global_table_name)
    if not replicas:
        return json_error("GlobalTableNotFoundException",
                          f"Global table '{global_table_name}' not found")

    return json_ok({"GlobalTableDescription": _global_table_description(global_table_name, replicas)})


def handle_list_global_tables(body: dict) -> Response:
    region_filter = body.get("RegionName")
    limit = int(body.get("Limit") or 100)
    start = body.get("ExclusiveStartGlobalTableName")

    all_names = sorted(
        name for name, reps in sm.replicas.items()
        if reps and (not region_filter or region_filter in reps)
    )

    start_idx = 0
    if start:
        try:
            start_idx = all_names.index(start) + 1
        except ValueError:
            start_idx = 0

    page = all_names[start_idx:start_idx + limit]
    result: dict = {
        "GlobalTables": [
            {
                "GlobalTableName": name,
                "ReplicationGroup": [
                    {"RegionName": r.region_name}
                    for r in sm.replicas[name].values()
                ],
            }
            for name in page
        ]
    }
    if start_idx + limit < len(all_names):
        result["LastEvaluatedGlobalTableName"] = all_names[start_idx + limit - 1]

    return json_ok(result)


def handle_update_global_table(body: dict) -> Response:
    global_table_name = body.get("GlobalTableName")
    replica_updates = body.get("ReplicaUpdates", [])
    if not global_table_name:
        return json_error("ValidationException", "GlobalTableName is required")

    replicas = sm.get_replicas(global_table_name)
    if not replicas:
        return json_error("GlobalTableNotFoundException",
                          f"Global table '{global_table_name}' not found")

    for update in replica_updates:
        if "Create" in update:
            region = update["Create"].get("RegionName")
            if not region:
                return json_error("ValidationException", "Create requires RegionName")
            err = sm.add_replica(global_table_name, ReplicaRecord(region_name=region))
            if err:
                return json_error("ReplicaAlreadyExistsException", err)
        elif "Delete" in update:
            region = update["Delete"].get("RegionName")
            if not region:
                return json_error("ValidationException", "Delete requires RegionName")
            err = sm.delete_replica(global_table_name, region)
            if err:
                return json_error("ReplicaNotFoundException", err)

    replicas = sm.get_replicas(global_table_name)
    return json_ok({"GlobalTableDescription": _global_table_description(global_table_name, replicas)})


# ------------------------------------------------------------------
# Tag handlers
# ------------------------------------------------------------------

def _resolve_table_from_resource_arn(body: dict) -> tuple[Optional[str], Optional[Response]]:
    arn = body.get("ResourceArn", "")
    if not arn:
        return None, json_error("ValidationException", "ResourceArn is required")
    table_name = _table_name_from_arn(arn)
    if not table_name:
        return None, json_error("ValidationException", f"Invalid ResourceArn: {arn}")
    if not sm.exists(table_name):
        return None, json_error("ResourceNotFoundException", f"Table not found: {table_name}", 404)
    return table_name, None


def handle_tag_resource(body: dict) -> Response:
    table_name, err = _resolve_table_from_resource_arn(body)
    if err:
        return err
    tags = body.get("Tags", [])
    if not isinstance(tags, list):
        return json_error("ValidationException", "Tags must be a list")
    sm.tag_resource(table_name, tags)
    return Response("", status=200, mimetype="application/x-amz-json-1.0")


def handle_untag_resource(body: dict) -> Response:
    table_name, err = _resolve_table_from_resource_arn(body)
    if err:
        return err
    tag_keys = body.get("TagKeys", [])
    if not isinstance(tag_keys, list):
        return json_error("ValidationException", "TagKeys must be a list")
    sm.untag_resource(table_name, tag_keys)
    return Response("", status=200, mimetype="application/x-amz-json-1.0")


def handle_list_tags_of_resource(body: dict) -> Response:
    table_name, err = _resolve_table_from_resource_arn(body)
    if err:
        return err
    tags = sorted(sm.list_tags(table_name), key=lambda t: t.get("Key", ""))
    return json_ok({"Tags": tags})


# ------------------------------------------------------------------
# Main route
# ------------------------------------------------------------------

_VERA_HANDLERS = {
    # Backup
    "CreateBackup":                       handle_create_backup,
    "DeleteBackup":                       handle_delete_backup,
    "DescribeBackup":                     handle_describe_backup,
    "ListBackups":                        handle_list_backups,
    "RestoreTableFromBackup":             handle_restore_table_from_backup,
    "RestoreTableToPointInTime":          handle_restore_table_to_point_in_time,
    "DescribeContinuousBackups":          handle_describe_continuous_backups,
    "UpdateContinuousBackups":            handle_update_continuous_backups,
    # Global table (v1 legacy)
    "CreateGlobalTable":                  handle_create_global_table,
    "DescribeGlobalTable":                handle_describe_global_table,
    "ListGlobalTables":                   handle_list_global_tables,
    "UpdateGlobalTable":                  handle_update_global_table,
    # Global table settings
    "DescribeGlobalTableSettings":        handle_describe_global_table_settings,
    "UpdateGlobalTableSettings":          handle_update_global_table_settings,
    # Table replica auto scaling
    "DescribeTableReplicaAutoScaling":    handle_describe_table_replica_auto_scaling,
    "UpdateTableReplicaAutoScaling":      handle_update_table_replica_auto_scaling,
    # Contributor Insights
    "DescribeContributorInsights":        handle_describe_contributor_insights,
    "UpdateContributorInsights":          handle_update_contributor_insights,
    "ListContributorInsights":            handle_list_contributor_insights,
    # Endpoints
    "DescribeEndpoints":                  handle_describe_endpoints,
    # Tags
    "TagResource":                        handle_tag_resource,
    "UntagResource":                      handle_untag_resource,
    "ListTagsOfResource":                 handle_list_tags_of_resource,
}


@app.route("/vera/reset-state", methods=["POST"])
def handle_vera_reset_state():
    """Reset all vera state machine metadata (used by eval harness between test runs)."""
    sm.reset()
    return Response(json.dumps({"message": "vera state reset"}), status=200, mimetype="application/json")


@app.route("/", methods=["POST"])
def handle_request():
    target = request.headers.get("X-Amz-Target", "")
    action = target.split(".")[-1] if "." in target else target

    raw_body = request.get_data()
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return json_error("SerializationException", "Request body is not valid JSON")

    logger.info(f"[{action}] {body.get('TableName', body.get('GlobalTableName', ''))}")

    # Block direct access to internal tables
    table_name = body.get("TableName", "")
    if table_name and is_vera_internal(table_name) and action not in _VERA_HANDLERS:
        return json_error("ResourceNotFoundException", f"Table not found: {table_name}")

    if action == "CreateTable":
        return handle_create_table(body, raw_body)
    elif action == "DeleteTable":
        return handle_delete_table(body, raw_body)
    elif action == "UpdateTable":
        return handle_update_table(body, raw_body)
    elif action == "DescribeTable":
        return handle_describe_table(body, raw_body)
    elif action == "ListTables":
        return handle_list_tables(body, raw_body)
    elif action in _WRITE_ACTIONS:
        return _maybe_patch_consumed_capacity(handle_write_op(action, body, raw_body))
    elif action in _VERA_HANDLERS:
        return _VERA_HANDLERS[action](body)
    else:
        return _maybe_patch_consumed_capacity(proxy(raw_body))


# Need this import for PITR handler
from datetime import datetime, timezone


if __name__ == "__main__":
    logger.info("Starting vera-dynamodb...")
    start_embedded_dynamodb_local()

    # Wire up DDB caller for state machine persistence
    sm.set_ddb_caller(_ddb_local_call)
    sm.ensure_internal_tables()

    sync_from_dynamodb_local()
    sm.load_persisted_state()

    host = os.environ.get("VERA_HOST", "127.0.0.1")
    port = int(os.environ.get("VERA_PORT", "5005"))
    app.run(host=host, port=port, debug=False)
