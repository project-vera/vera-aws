"""
Independent test for ARN-based Tag API.

Tests TagResource, UntagResource, ListTagsOfResource using the table ARN
returned by CreateTable (not hardcoded ARNs).

Run with emulator already started:
    python tests/test_arn_tags.py
"""

import json
import sys
import boto3
import requests
from botocore.config import Config

ENDPOINT = "http://localhost:5005"

client = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    config=Config(retries={"max_attempts": 1}),
)


def call(action: str, payload: dict) -> dict:
    """Call via boto3 — handles SigV4 signing automatically."""
    import botocore.exceptions
    method = getattr(client, _to_snake(action))
    try:
        resp = method(**payload)
        resp.pop("ResponseMetadata", None)
        return {"status": 200, "body": resp}
    except botocore.exceptions.ClientError as e:
        code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        return {"status": code, "body": e.response["Error"]}


def _to_snake(name: str) -> str:
    import re
    s = re.sub(r"([A-Z])", r"_\1", name).lstrip("_").lower()
    return s


def _raw(action: str, payload: dict) -> dict:
    """Low-level call returning raw status code (for error cases)."""
    import requests as req
    import datetime
    headers = {
        "Content-Type": "application/x-amz-json-1.0",
        "X-Amz-Target": f"DynamoDB_20120810.{action}",
        "Authorization": "AWS4-HMAC-SHA256 Credential=test/20260405/us-east-1/dynamodb/aws4_request, SignedHeaders=host, Signature=fake",
        "X-Amz-Date": "20260405T000000Z",
    }
    r = req.post(ENDPOINT, json=payload, headers=headers)
    try:
        return {"status": r.status_code, "body": r.json()}
    except Exception:
        return {"status": r.status_code, "body": r.text}


def reset():
    # Delete all user tables via vera (which proxies to DDB Local)
    r = call("ListTables", {})
    for name in r["body"].get("TableNames", []):
        call("DeleteTable", {"TableName": name})
    # Reset vera state machine
    requests.post(f"{ENDPOINT}/vera/reset-state")


def check(label: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))
    if not condition:
        global _failures
        _failures += 1


_failures = 0


def main():
    global _failures
    reset()

    print("\n=== Setup: create table ===")
    resp = call("CreateTable", {
        "TableName": "TagTestTable",
        "AttributeDefinitions": [{"AttributeName": "PK", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    })
    check("CreateTable succeeds", resp["status"] == 200)
    table_arn = resp["body"].get("TableDescription", {}).get("TableArn", "")
    check("TableArn is present", bool(table_arn), table_arn)
    check("TableArn contains :table/", ":table/" in table_arn, table_arn)
    print(f"  TableArn = {table_arn}")

    print("\n=== TagResource ===")
    resp = call("TagResource", {
        "ResourceArn": table_arn,
        "Tags": [
            {"Key": "Owner", "Value": "blueTeam"},
            {"Key": "Env", "Value": "test"},
        ],
    })
    check("TagResource returns 200", resp["status"] == 200)

    print("\n=== ListTagsOfResource ===")
    resp = call("ListTagsOfResource", {"ResourceArn": table_arn})
    check("ListTagsOfResource returns 200", resp["status"] == 200)
    tags = {t["Key"]: t["Value"] for t in resp["body"].get("Tags", [])}
    check("Owner tag present", tags.get("Owner") == "blueTeam", str(tags))
    check("Env tag present", tags.get("Env") == "test", str(tags))

    print("\n=== TagResource (overwrite) ===")
    resp = call("TagResource", {
        "ResourceArn": table_arn,
        "Tags": [{"Key": "Owner", "Value": "redTeam"}],
    })
    check("Overwrite TagResource returns 200", resp["status"] == 200)
    resp = call("ListTagsOfResource", {"ResourceArn": table_arn})
    tags = {t["Key"]: t["Value"] for t in resp["body"].get("Tags", [])}
    check("Owner tag overwritten", tags.get("Owner") == "redTeam", str(tags))
    check("Env tag still present", tags.get("Env") == "test", str(tags))

    print("\n=== UntagResource ===")
    resp = call("UntagResource", {
        "ResourceArn": table_arn,
        "TagKeys": ["Env"],
    })
    check("UntagResource returns 200", resp["status"] == 200)
    resp = call("ListTagsOfResource", {"ResourceArn": table_arn})
    tags = {t["Key"]: t["Value"] for t in resp["body"].get("Tags", [])}
    check("Env tag removed", "Env" not in tags, str(tags))
    check("Owner tag still present", "Owner" in tags, str(tags))

    print("\n=== Error: invalid ARN ===")
    resp = call("TagResource", {
        "ResourceArn": "not-an-arn",
        "Tags": [{"Key": "X", "Value": "Y"}],
    })
    check("Invalid ARN returns 400", resp["status"] == 400)

    print("\n=== Error: non-existent table ARN ===")
    fake_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/DoesNotExist"
    resp = call("ListTagsOfResource", {"ResourceArn": fake_arn})
    check("Non-existent table returns 404", resp["status"] == 404)

    print("\n=== ARN helper: extract table name from various ARN formats ===")
    # Test that the emulator accepts ARNs with region/account different from ddblocal default
    resp = call("TagResource", {
        "ResourceArn": "arn:aws:dynamodb:us-west-2:999999999999:table/TagTestTable",
        "Tags": [{"Key": "Region", "Value": "west"}],
    })
    check("ARN with different region/account still resolves table", resp["status"] == 200)

    print(f"\n{'='*50}")
    if _failures == 0:
        print("All tests PASSED")
    else:
        print(f"{_failures} test(s) FAILED")
    return _failures


if __name__ == "__main__":
    sys.exit(main())
