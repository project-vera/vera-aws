# Vera AWS DynamoDB

Local Amazon DynamoDB emulator with state machine enforcement, backup/restore, PITR, and global table support.

Built on top of [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) (official AWS image) as the data backend. Vera adds a state machine layer that enforces table lifecycle transitions and blocks invalid operations — matching the behavior of real DynamoDB. It also implements several DynamoDB features that DynamoDB Local does not support natively, including on-demand backups, point-in-time recovery (PITR), global tables, and contributor insights.

## Architecture

```
Client (AWS CLI / boto3 / SDK)
        │
        ▼
vera-dynamodb  :5005   ← state machine + proxy + backup/PITR/global table
        │
        ▼
dynamodb-local :8000   ← data storage (official AWS image, embedded)
```

**vera-dynamodb** intercepts table lifecycle operations (`CreateTable`, `DeleteTable`, `UpdateTable`) to enforce state transitions:

```
CREATING → ACTIVE → UPDATING → ACTIVE
                 ↘           ↗
                  DELETING (terminal)
```

It also intercepts write operations (`PutItem`, `UpdateItem`, `DeleteItem`, `BatchWriteItem`, `TransactWriteItems`) for PITR logging, and implements 22 API actions that DynamoDB Local does not support.

All other operations (`GetItem`, `Query`, `Scan`, `BatchGetItem`, `TransactGetItems`, etc.) are passed straight through to DynamoDB Local.

On startup, vera syncs existing tables from DynamoDB Local into its state machine as `ACTIVE`, and reloads persisted backup/PITR/replica state from internal metadata tables.

### Internal tables

Vera uses DynamoDB Local itself for persistent storage of metadata:

| Table | Purpose |
|---|---|
| `__vera_meta__` | Backup records, PITR config, replica metadata, contributor insights |
| `__vera_pitr_log__` | Write operation log for point-in-time recovery |
| `__vera_bk_{id}__` | Cloned table data for each on-demand backup |

These tables are hidden from `ListTables` and blocked from direct user access.

## Setup

### Local development

```bash
./install.sh
```

This will:
- Install Python dependencies via `uv`
- Install Java if not present (required by DynamoDB Local)
- Download the DynamoDB Local JAR to `./dynamodb-local/`
- Add a `[vera]` profile to `~/.aws/credentials`
- Create an `awscli` wrapper in `.venv/bin/` that points to `http://localhost:5005`

Then start the emulator:

```bash
uv run python main.py
```

vera-dynamodb starts DynamoDB Local as a subprocess on port 8000, then listens on port 5005.

Use the `awscli` wrapper to avoid typing `--endpoint-url` every time:

```bash
uv run awscli dynamodb list-tables
uv run awscli dynamodb create-table \
  --table-name Users \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### With Docker Compose

vera-dynamodb bundles DynamoDB Local inside the same container — no separate service needed.

From the repo root:

```bash
docker compose up vera-dynamodb
```

vera-dynamodb is available at `http://localhost:5005`.

## Usage

Point any AWS CLI or SDK at `http://localhost:5005` with any credentials (DynamoDB Local ignores auth).

### AWS CLI

```bash
aws dynamodb create-table \
  --endpoint-url http://localhost:5005 \
  --table-name Users \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb put-item \
  --endpoint-url http://localhost:5005 \
  --table-name Users \
  --item '{"id": {"S": "user-1"}, "name": {"S": "Alice"}}'

aws dynamodb get-item \
  --endpoint-url http://localhost:5005 \
  --table-name Users \
  --key '{"id": {"S": "user-1"}}'

aws dynamodb list-tables --endpoint-url http://localhost:5005
aws dynamodb delete-table --endpoint-url http://localhost:5005 --table-name Users
```

Set `AWS_ENDPOINT_URL_DYNAMODB` to avoid repeating `--endpoint-url`:

```bash
export AWS_ENDPOINT_URL_DYNAMODB=http://localhost:5005
aws dynamodb list-tables
```

### boto3 (Python)

```python
import boto3

ddb = boto3.client(
    "dynamodb",
    endpoint_url="http://localhost:5005",
    region_name="us-east-1",
    aws_access_key_id="fake",
    aws_secret_access_key="fake",
)

ddb.create_table(
    TableName="Orders",
    AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
    KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
    BillingMode="PAY_PER_REQUEST",
)

ddb.put_item(
    TableName="Orders",
    Item={"order_id": {"S": "ord-123"}, "status": {"S": "pending"}},
)

resp = ddb.get_item(TableName="Orders", Key={"order_id": {"S": "ord-123"}})
print(resp["Item"])
# {'order_id': {'S': 'ord-123'}, 'status': {'S': 'pending'}}
```

### Run the evaluator

With the emulator running (`uv run python main.py`):

```bash
cd tests
uv run python eval_emulator.py
```

The evaluator runs all commands from the RST example files against the running emulator, compares output against expected golden values, and saves results to `eval_results.json`. Use `show_mismatches.py` to inspect failures:

```bash
uv run python show_mismatches.py eval_results.json
# writes eval_results.out with expected/actual diffs for each mismatch
```

Options:

```bash
uv run python eval_emulator.py --start-from 10               # resume from command 10
uv run python eval_emulator.py --checkpoint out.json         # custom output file
uv run python eval_emulator.py --endpoint http://localhost:5006
uv run python eval_emulator.py --rst create-table.rst put-item.rst  # run specific RST files only
```

### e2e tests (boto3)

```bash
cd tests
uv run pytest test_e2e.py -v
```

## State Machine Enforcement

vera blocks operations that would be invalid on real DynamoDB:

| Operation | Blocked when table is |
|---|---|
| `CreateTable` | Already exists (`ACTIVE`, `CREATING`, `UPDATING`) |
| `DeleteTable` | `CREATING` or already `DELETING` |
| `UpdateTable` | `CREATING` or `DELETING` |

Blocked operations return the same error codes as real DynamoDB:
- `ResourceInUseException` — table exists or is in a conflicting state
- `ResourceNotFoundException` — table does not exist

## Features

### On-demand backups

Full backup/restore lifecycle implemented on top of DynamoDB Local:

- `CreateBackup` — clones the table schema and all items into an internal `__vera_bk_{id}__` table
- `DeleteBackup` — marks the backup as `DELETED` and drops the clone table
- `DescribeBackup` — returns full backup metadata (status, size, type, timestamps)
- `ListBackups` — supports filtering by table name, backup type, and time range, with pagination
- `RestoreTableFromBackup` — creates a new table from a backup's schema and items

Backups are persistent across emulator restarts (stored in DynamoDB Local).

### Point-in-time recovery (PITR)

PITR is implemented via write-op logging and replay:

1. `UpdateContinuousBackups` enables/disables PITR per table
2. When PITR is enabled, all write operations (`PutItem`, `UpdateItem`, `DeleteItem`, `BatchWriteItem`, `TransactWriteItems`) are logged to `__vera_pitr_log__` with timestamps
3. `RestoreTableToPointInTime` creates a new empty table, then replays logged write operations up to the specified `RestoreDateTime`
4. `DescribeContinuousBackups` returns current PITR status

### Global tables

Both legacy (v1) and v2 global table APIs are supported:

**Legacy API (v1):**
- `CreateGlobalTable`, `DescribeGlobalTable`, `ListGlobalTables`, `UpdateGlobalTable`
- `DescribeGlobalTableSettings`, `UpdateGlobalTableSettings`

**v2 API (via UpdateTable):**
- `UpdateTable` with `ReplicaUpdates` parameter — adds/removes replica metadata
- `DescribeTable` — returns `Replicas` field with replica regions and status

Since vera runs a single DynamoDB Local instance, replicas are metadata-only (no real multi-region data isolation). This matches LocalStack's approach.

### Contributor insights

- `DescribeContributorInsights` — returns status per table/index
- `UpdateContributorInsights` — enables/disables per table/index
- `ListContributorInsights` — lists all tables/indexes with contributor insights, with pagination

### Other

- `DescribeEndpoints` — returns vera's own address
- `DescribeTableReplicaAutoScaling` / `UpdateTableReplicaAutoScaling` — returns/accepts auto scaling settings (stub values)

### Response augmentation

vera patches DynamoDB Local responses to better match real AWS behavior:

- `DeleteTable` returns `TableStatus: "DELETING"` (DynamoDB Local returns `"ACTIVE"`)
- `ListTables` hides internal `__vera_*` tables
- `DescribeTable` injects `Replicas` field when global table replicas exist
- `CreateTable` / `DescribeTable` responses include `SSEDescription` and `TableClassSummary` fields

## API Coverage

### Supported operations

vera supports all operations that DynamoDB Local 3.3.0 implements, plus 22 additional operations that DynamoDB Local does not support natively.

| Layer | Operations |
|---|---|
| State machine | `CreateTable`, `DeleteTable`, `UpdateTable` |
| Write ops (proxied + PITR logged) | `PutItem`, `UpdateItem`, `DeleteItem`, `BatchWriteItem`, `TransactWriteItems` |
| Proxied directly | `DescribeTable`, `ListTables`, `GetItem`, `BatchGetItem`, `Query`, `Scan`, `TransactGetItems`, `DescribeTimeToLive`, `UpdateTimeToLive`, `DescribeLimits`, and all other core data-plane operations |
| Vera-implemented (not in DDB Local) | `CreateBackup`, `DeleteBackup`, `DescribeBackup`, `ListBackups`, `RestoreTableFromBackup`, `RestoreTableToPointInTime`, `DescribeContinuousBackups`, `UpdateContinuousBackups`, `CreateGlobalTable`, `DescribeGlobalTable`, `DescribeGlobalTableSettings`, `ListGlobalTables`, `UpdateGlobalTable`, `UpdateGlobalTableSettings`, `DescribeContributorInsights`, `ListContributorInsights`, `UpdateContributorInsights`, `DescribeEndpoints`, `DescribeTableReplicaAutoScaling`, `UpdateTableReplicaAutoScaling` |

## Testing

Tests live in `tests/`. The test suite uses 43 AWS CLI commands crawled from the official [aws-cli examples](https://github.com/aws/aws-cli/tree/develop/awscli/examples/dynamodb) (stored in `tests/cli/dynamodb/`).

### Command filtering

From 74 total example commands across 41 RST files:

| Filter | Count | Reason |
|---|---|---|
| Contains `--*-id` / `--*-arn` parameters | 8 | Require dynamically generated IDs unavailable at test time |
| Contains `file://` parameters | 23 | Require local fixture files not present in the test environment |
| **Runnable** | **43** | Executed by the evaluator |

### Output comparison

The evaluator compares actual emulator output against the RST golden output after normalizing fields that differ between local and real AWS.

Dynamic fields fall into two categories:

**Required dynamic fields** — key must be present in actual output, but the value is not compared (emulator produces these with structurally correct but different values):

| Field | Reason |
|---|---|
| `CreationDateTime`, `LastIncreaseDateTime`, `LastDecreaseDateTime`, `LatestStreamLabel`, `BackupCreationDateTime`, `TableCreationDateTime` | Timestamps differ every run |
| `RestoreDateTime`, `LastUpdateDateTime`, `EarliestRestorableDateTime`, `LatestRestorableDateTime` | Timestamps differ every run |
| `TableArn`, `IndexArn`, `LatestStreamArn`, `BackupArn`, `GlobalTableArn`, `SourceTableArn`, `SourceBackupArn` | ARNs contain account ID / region that differ from real AWS |
| `KMSMasterKeyArn`, `AutoScalingRoleArn` | ARNs vera generates with fake account ID |
| `TableId` | UUID vera generates per table (DynamoDB Local returns empty string) |
| `ItemCount`, `TableSizeBytes`, `IndexSizeBytes`, `BackupSizeBytes` | Runtime data — vera returns actual values, RST reflects pre-populated real AWS tables |
| `NumberOfDecreasesToday` | DynamoDB Local always returns 0; key is present |
| `ReadCapacityUnits`, `WriteCapacityUnits` | Vera injects from stored provisioned throughput; values are structurally correct |
| `BillingModeSummary`, `Backfilling`, `RestoreInProgress` | Vera injects these; values are accurate |
| `ContributorInsightsRuleList` | Vera generates rule names with real timestamp suffix |
| `ScalingPolicies`, `PolicyName`, `TargetTrackingScalingPolicyConfiguration` | Vera constructs autoscaling policy stubs |
| `ReplicaProvisionedReadCapacityUnits`, `ReplicaProvisionedWriteCapacityUnits` | Vera computes from actual table throughput |

**Optional dynamic fields** — stripped from both sides before comparison (emulator does not produce these):

| Field | Reason |
|---|---|
| `LastUpdateToPayPerRequestDateTime` | Only present when billing mode changed from PAY_PER_REQUEST; vera does not track |
| `NextToken` | RST golden output contains fake AWS pagination tokens; vera uses simple integer tokens |
| `ItemCollectionMetrics` | DynamoDB Local does not return item collection metrics |
| `ContributorInsightsSummaries` | Pagination differs: RST reflects real AWS table set; vera has different tables at eval time |

**Semantically compared fields** (present in comparison but normalized):

| Field | Normalization |
|---|---|
| `TableStatus`, `IndexStatus`, `BackupStatus`, `GlobalTableStatus`, `ContributorInsightsStatus`, `ReplicaStatus`, `PointInTimeRecoveryStatus`, `ContinuousBackupsStatus` | Transient states map to their terminal equivalent: `CREATING` → `ACTIVE`, `UPDATING` → `ACTIVE`, `ENABLING` → `ENABLED`, `DISABLING` → `DISABLED`. vera completes state transitions synchronously. |

Comparison uses **subset matching**: expected fields must be present and equal in the actual response, but the actual response may contain additional fields. List fields (e.g. `AttributeDefinitions`, `GlobalSecondaryIndexes`) are compared as unordered sets — each expected item must match a distinct actual item regardless of order.

### Results

Current eval results against 41 RST example files (193 runnable commands):

| Metric | Value |
|---|---|
| RST files passing | 39 / 41 (95.1%) |
| Commands exit OK | 193 / 193 (100%) |
| Commands output match | 190 / 193 (98.4%) |

The 2 failing RST files:
- `list-tables.rst` — the `--starting-token` command passes a fake AWS pagination token that DynamoDB Local cannot interpret, returning an empty list instead of the expected page
- `list-backups.rst` — the `--max-items 1` command returns the second backup instead of the first due to backup naming in the setup

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `VERA_HOST` | `127.0.0.1` | Bind address |
| `VERA_PORT` | `5005` | Listen port |
| `DYNAMODB_LOCAL_URL` | `http://localhost:8000` | DynamoDB Local endpoint |
| `DYNAMODB_LOCAL_JAR` | `./dynamodb-local/DynamoDBLocal.jar` | Path to DynamoDB Local JAR |
| `DYNAMODB_LOCAL_LIB` | `./dynamodb-local/DynamoDBLocal_lib` | Path to native libs |
