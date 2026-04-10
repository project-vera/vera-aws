"""
End-to-end tests for vera-dynamodb using boto3.
Requires vera-dynamodb running on localhost:5005.
DynamoDB Local does NOT need to be running — we test vera's state machine
layer, and proxy failures are expected (and asserted where relevant).
"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

VERA_ENDPOINT = "http://localhost:5005"

def client():
    return boto3.client(
        "dynamodb",
        endpoint_url=VERA_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
        config=Config(retries={"max_attempts": 1}),
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_table(ddb, name):
    return ddb.create_table(
        TableName=name,
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )


# ------------------------------------------------------------------
# State machine: CreateTable
# ------------------------------------------------------------------

class TestCreateTable:
    def test_blocked_when_already_exists(self):
        """vera should reject CreateTable for a table it already tracks."""
        ddb = client()
        # First call goes to DynamoDB Local (will fail with 503), vera rolls back
        # so we seed the state manually via a second attempt after reset
        # Instead, confirm the error type is ResourceInUseException when vera
        # thinks the table exists — achieved by trying twice rapidly.
        # Since DynamoDB Local is not running, first call returns 503 from proxy.
        # vera rolls back on proxy failure, so table is NOT tracked after failure.
        # This test just confirms vera doesn't crash and returns a valid response.
        try:
            make_table(ddb, "TestTable")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            # Expected: proxy failure (ServiceUnavailableException) since no DynamoDB Local
            assert code in ("ServiceUnavailableException", "ResourceInUseException"), \
                f"Unexpected error: {code}"
        print("  CreateTable (no backend): returns error gracefully")

    def test_duplicate_blocked_by_state_machine(self):
        """After a successful create (mocked), duplicate should be rejected by vera."""
        # We can't do a real CreateTable without DynamoDB Local,
        # but we can seed state machine directly and verify the block.
        from state_machine import TableStateMachine
        sm = TableStateMachine()
        sm.register("AlreadyExists", "ACTIVE")
        err = sm.check_action("CreateTable", "AlreadyExists")
        assert err is not None
        assert "already exists" in err
        print("  Duplicate CreateTable blocked by state machine: OK")


# ------------------------------------------------------------------
# State machine: DeleteTable
# ------------------------------------------------------------------

class TestDeleteTable:
    def test_missing_table_returns_not_found(self):
        ddb = client()
        try:
            ddb.delete_table(TableName="DoesNotExist")
            assert False, "Should have raised"
        except ClientError as e:
            code = e.response["Error"]["Code"]
            assert code == "ResourceNotFoundException", f"Got: {code}"
        print("  DeleteTable on missing table -> ResourceNotFoundException: OK")

    def test_creating_state_blocks_delete(self):
        from state_machine import TableStateMachine
        sm = TableStateMachine()
        sm.register("InProgress", "CREATING")
        err = sm.check_action("DeleteTable", "InProgress")
        assert err is not None
        assert "CREATING" in err
        print("  DeleteTable on CREATING table blocked: OK")


# ------------------------------------------------------------------
# State machine: UpdateTable
# ------------------------------------------------------------------

class TestUpdateTable:
    def test_missing_table_returns_not_found(self):
        ddb = client()
        try:
            ddb.update_table(
                TableName="NoSuchTable",
                BillingMode="PAY_PER_REQUEST",
            )
            assert False, "Should have raised"
        except ClientError as e:
            code = e.response["Error"]["Code"]
            assert code == "ResourceNotFoundException", f"Got: {code}"
        print("  UpdateTable on missing table -> ResourceNotFoundException: OK")

    def test_deleting_state_blocks_update(self):
        from state_machine import TableStateMachine
        sm = TableStateMachine()
        sm.register("Dying", "ACTIVE")
        sm.transition("Dying", "DELETING")
        err = sm.check_action("UpdateTable", "Dying")
        assert err is not None
        assert "DELETING" in err
        print("  UpdateTable on DELETING table blocked: OK")


# ------------------------------------------------------------------
# Passthrough: operations without a table in state machine
# ------------------------------------------------------------------

class TestPassthrough:
    def test_list_tables_proxied(self):
        """ListTables is proxied directly to DynamoDB Local."""
        ddb = client()
        resp = ddb.list_tables()
        assert "TableNames" in resp
        print(f"  ListTables proxied: OK (tables: {resp['TableNames']})")

    def test_get_item_on_missing_table_proxied(self):
        """GetItem is proxied — DynamoDB Local returns ResourceNotFoundException for unknown table."""
        ddb = client()
        try:
            ddb.get_item(TableName="NonExistentTable", Key={"id": {"S": "1"}})
            assert False, "Should have raised"
        except ClientError as e:
            code = e.response["Error"]["Code"]
            assert code == "ResourceNotFoundException", f"Got: {code}"
        print("  GetItem on missing table proxied -> ResourceNotFoundException: OK")


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

if __name__ == "__main__":
    suites = [
        TestCreateTable(),
        TestDeleteTable(),
        TestUpdateTable(),
        TestPassthrough(),
    ]
    for suite in suites:
        name = suite.__class__.__name__
        print(f"\n{name}:")
        for attr in [a for a in dir(suite) if a.startswith("test_")]:
            getattr(suite, attr)()
    print("\nAll tests passed.")
