"""
vera-dynamodb: DynamoDB proxy with state machine enforcement.

Architecture:
  Client -> vera-dynamodb (this server, port 5005)
               |
               +--> [State Machine] for table lifecycle ops
               |
               +--> [DynamoDB Local] for all data ops (port 8000)

Protocol: POST / with X-Amz-Target header + JSON body (application/x-amz-json-1.0)
"""

import os
import json
import logging
import socket
import subprocess
import time
import requests
from flask import Flask, request, Response

from emulator_core.state_machine import TableStateMachine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera-dynamodb")

app = Flask(__name__)

DYNAMODB_LOCAL_URL = os.environ.get("DYNAMODB_LOCAL_URL", "http://localhost:8000")

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_JAR = os.path.join(_HERE, "dynamodb-local", "DynamoDBLocal.jar")
_DEFAULT_LIB = os.path.join(_HERE, "dynamodb-local", "DynamoDBLocal_lib")

sm = TableStateMachine()

# Actions that touch table lifecycle — vera intercepts these.
# All other actions are passed straight through.
TABLE_ACTIONS = {"CreateTable", "DeleteTable", "UpdateTable", "DescribeTable", "ListTables"}


def json_error(code: str, message: str, http_status: int = 400) -> Response:
    body = json.dumps({"__type": code, "message": message})
    return Response(body, status=http_status, mimetype="application/x-amz-json-1.0")


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
        return Response(resp.content, status=resp.status_code, mimetype="application/x-amz-json-1.0")
    except requests.exceptions.ConnectionError:
        return json_error("ServiceUnavailableException",
                          f"DynamoDB Local not reachable at {DYNAMODB_LOCAL_URL}", 503)


def start_embedded_dynamodb_local() -> None:
    """Start DynamoDB Local as a subprocess if JAR is present."""
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
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for DynamoDB Local to be ready (up to 15s)
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
    """Pull existing tables from DynamoDB Local into the state machine."""
    try:
        resp = requests.post(
            DYNAMODB_LOCAL_URL,
            json={},
            headers={
                "X-Amz-Target": "DynamoDB_20120810.ListTables",
                "Content-Type": "application/x-amz-json-1.0",
                "Authorization": "AWS4-HMAC-SHA256 Credential=fake/20000101/us-east-1/dynamodb/aws4_request, SignedHeaders=host, Signature=fake",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            table_names = resp.json().get("TableNames", [])
            sm.import_existing(table_names)
            logger.info(f"Synced {len(table_names)} tables from DynamoDB Local")
        else:
            logger.warning(f"ListTables sync failed: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.warning(f"Could not sync from DynamoDB Local: {e}")


# ------------------------------------------------------------------
# Table action handlers
# ------------------------------------------------------------------

def _augment_create_table_response(resp_body: dict, request_body: dict) -> dict:
    """
    Inject fields that DynamoDB Local omits but real DynamoDB returns.
    Mutates and returns resp_body.
    """
    desc = resp_body.get("TableDescription", {})

    # SSEDescription: DynamoDB Local accepts --sse-specification but doesn't echo it back.
    sse_spec = request_body.get("SSESpecification", {})
    if sse_spec.get("Enabled") and "SSEDescription" not in desc:
        sse_entry = {"Status": "ENABLED", "SSEType": sse_spec.get("SSEType", "AES256")}
        key_id = sse_spec.get("KMSMasterKeyId")
        if key_id and not key_id.startswith("arn:"):
            key_id = f"arn:aws:kms:us-east-1:000000000000:key/{key_id}"
        if key_id:
            sse_entry["KMSMasterKeyArn"] = key_id
        desc["SSEDescription"] = sse_entry

    # TableClassSummary: DynamoDB Local accepts --table-class but doesn't echo it back.
    table_class = request_body.get("TableClass")
    if table_class and "TableClassSummary" not in desc:
        desc["TableClassSummary"] = {"TableClass": table_class}

    resp_body["TableDescription"] = desc
    return resp_body


def handle_create_table(body: dict, raw_body: bytes) -> Response:
    table_name = body.get("TableName")
    if not table_name:
        return json_error("ValidationException", "TableName is required")

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
        if status is None:
            return json_error("ResourceNotFoundException", err)
        return json_error("ResourceInUseException", err)

    sm.transition(table_name, "DELETING")

    resp = proxy(raw_body)

    if resp.status_code == 200:
        sm.remove(table_name)
    else:
        # Roll back: DynamoDB Local rejected the delete
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

    prev_status = sm.get_status(table_name)
    sm.transition(table_name, "UPDATING")

    resp = proxy(raw_body)

    if resp.status_code == 200:
        sm.transition(table_name, "ACTIVE")
    else:
        sm._tables[table_name] = prev_status
        logger.warning(f"UpdateTable failed for {table_name}, rolled back to {prev_status}")

    return resp


# ------------------------------------------------------------------
# Main route
# ------------------------------------------------------------------

@app.route("/", methods=["POST"])
def handle_request():
    target = request.headers.get("X-Amz-Target", "")
    # e.g. "DynamoDB_20120810.CreateTable" -> "CreateTable"
    action = target.split(".")[-1] if "." in target else target

    raw_body = request.get_data()

    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return json_error("SerializationException", "Request body is not valid JSON")

    logger.info(f"[{action}] {body.get('TableName', '')}")

    if action == "CreateTable":
        return handle_create_table(body, raw_body)
    elif action == "DeleteTable":
        return handle_delete_table(body, raw_body)
    elif action == "UpdateTable":
        return handle_update_table(body, raw_body)
    else:
        # DescribeTable, ListTables, PutItem, GetItem, Query, Scan, etc.
        return proxy(raw_body)


if __name__ == "__main__":
    logger.info("Starting vera-dynamodb...")
    start_embedded_dynamodb_local()
    sync_from_dynamodb_local()
    host = os.environ.get("VERA_HOST", "127.0.0.1")
    port = int(os.environ.get("VERA_PORT", "5005"))
    app.run(host=host, port=port, debug=False)
