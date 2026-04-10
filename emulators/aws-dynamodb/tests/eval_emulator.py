#!/usr/bin/env python3
"""
Evaluate AWS CLI commands against DynamoDB Emulator (vera-dynamodb).
Runs each command from the RST examples against a running emulator instance,
comparing output against the expected output from the RST (minus dynamic fields).

Usage:
  python eval_emulator.py
  python eval_emulator.py --start-from 10
  python eval_emulator.py --endpoint http://localhost:5005
  python eval_emulator.py --checkpoint my_results.json
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from utils.parse_aws_commands import parse_aws_commands_from_directory
from utils.print_commands_with_endpoint import to_awscli_command

# Dynamic fields where the key MUST be present in actual but the value is not compared.
# Use for fields the emulator always produces but with different values (ARNs, timestamps).
REQUIRED_DYNAMIC_KEYS = {
    # Timestamps — emulator produces these but values differ every run
    "CreationDateTime",
    "LastIncreaseDateTime",
    "LastDecreaseDateTime",
    "LatestStreamLabel",
    "BackupCreationDateTime",
    "TableCreationDateTime",
    "RestoreDateTime",
    "LastUpdateDateTime",
    # ARNs — emulator generates correct structure but region/account differ from RST
    "BackupArn",
    "TableArn",
    "IndexArn",
    "LatestStreamArn",
    "GlobalTableArn",
    "SourceBackupArn",
    "SourceTableArn",
    # Runtime counters/sizes — emulator returns real values but RST reflects real AWS data
    "ItemCount",
    "TableSizeBytes",
    "IndexSizeBytes",
    "BackupSizeBytes",
    "NumberOfDecreasesToday",
    # Capacity units — vera injects from stored provisioned throughput
    "ReadCapacityUnits",
    "WriteCapacityUnits",
    # Structural fields emulator always returns
    "BillingModeSummary",
    "Backfilling",
    "RestoreInProgress",
    # IDs — vera generates a UUID
    "TableId",
    # PITR restore window timestamps
    "EarliestRestorableDateTime",
    "LatestRestorableDateTime",
    # ARNs — may appear in SSE or autoscaling responses
    "KMSMasterKeyArn",
    "AutoScalingRoleArn",
    # Autoscaling policy details — vera generates these for replicas
    "ContributorInsightsRuleList",
    "ScalingPolicies",
    "PolicyName",
    "TargetTrackingScalingPolicyConfiguration",
    # Replica capacity details
    "ReplicaProvisionedReadCapacityUnits",
    "ReplicaProvisionedWriteCapacityUnits",
}

# Dynamic fields that are completely stripped from both expected and actual.
# Use only for fields the emulator genuinely does not produce.
OPTIONAL_DYNAMIC_KEYS = {
    # RST golden output contains fake pagination tokens; vera uses simple integer tokens
    "NextToken",
    # Endpoint address differs
    "Address",
    # Not produced by emulator
    "ItemCollectionMetrics",
    # Only present when billing mode changed from PAY_PER_REQUEST → PROVISIONED
    "LastUpdateToPayPerRequestDateTime",
    # Pagination differs: RST reflects real AWS table set, vera has different tables
    "ContributorInsightsSummaries",
}

# Combined set for convenience
DYNAMIC_KEYS = REQUIRED_DYNAMIC_KEYS | OPTIONAL_DYNAMIC_KEYS

# Status fields that are compared semantically rather than literally.
# vera completes transitions synchronously, so RST transient states
# (CREATING, DELETING, UPDATING) map to their terminal equivalents.
_STATUS_EQUIVALENCES = {
    "CREATING": "ACTIVE",
    "UPDATING": "ACTIVE",
    "DELETING": "DELETING",
    "ENABLING": "ENABLED",
    "DISABLING": "DISABLED",
}
# BackupStatus uses CREATING→AVAILABLE instead of CREATING→ACTIVE
_BACKUP_STATUS_EQUIVALENCES = {
    "CREATING": "AVAILABLE",
}
STATUS_KEYS = {
    "TableStatus",
    "IndexStatus",
    "BackupStatus",
    "GlobalTableStatus",
    "ContributorInsightsStatus",
    "ReplicaStatus",
    "PointInTimeRecoveryStatus",
    "ContinuousBackupsStatus",
}


def _normalize_status(value: str, key: str = None) -> str:
    """Map transient status to its terminal equivalent for comparison."""
    if key == "BackupStatus":
        return _BACKUP_STATUS_EQUIVALENCES.get(value, value)
    return _STATUS_EQUIVALENCES.get(value, value)


# Sentinel value used to mark dynamic fields in the expected output.
# When is_subset sees _ANY as the expected value, it only checks the key
# exists in actual (any value accepted) rather than comparing values.
# This means missing dynamic fields in actual are still caught.
_ANY = object()


def mark_dynamic(obj):
    """
    Recursively process expected output for dynamic fields:
    - REQUIRED_DYNAMIC_KEYS: replace value with _ANY (key must exist in actual,
      value comparison is skipped)
    - OPTIONAL_DYNAMIC_KEYS: remove the key entirely (key may or may not exist
      in actual — we don't check)
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in REQUIRED_DYNAMIC_KEYS:
                result[k] = _ANY   # key required, value unconstrained
            elif k in OPTIONAL_DYNAMIC_KEYS:
                pass               # strip entirely — presence not required
            else:
                result[k] = mark_dynamic(v)
        return result
    if isinstance(obj, list):
        return [mark_dynamic(item) for item in obj]
    return obj



def is_subset(expected, actual, _key=None) -> bool:
    """
    Return True if every key/value in expected exists in actual (recursively).
    Lists of dicts are compared as unordered sets (order-independent).
    Status fields (TableStatus, IndexStatus) are compared after normalizing
    transient states (CREATING→ACTIVE, UPDATING→ACTIVE).
    Empty dicts ({}) in expected are treated as "any value acceptable" (present or absent).
    _ANY sentinel means: key must exist in actual but any value is accepted.
    """
    if expected is _ANY:
        # Key exists in actual (caller already checked via dict lookup); value is unconstrained.
        return True
    if isinstance(expected, dict) and isinstance(actual, dict):
        for k, v in expected.items():
            # Skip empty-dict checks — an empty dict means
            # "we have no stable fields to assert" so any actual value (or absence) is OK
            if isinstance(v, dict) and not v:
                continue
            if k not in actual:
                return False
            if not is_subset(v, actual[k], _key=k):
                return False
        return True
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        # Match each expected item to a distinct actual item (order-independent).
        # Each actual item may only be used once.
        remaining = list(range(len(actual)))
        for e in expected:
            matched = False
            for i in remaining:
                if is_subset(e, actual[i]):
                    remaining.remove(i)
                    matched = True
                    break
            if not matched:
                return False
        return True
    if _key in STATUS_KEYS and isinstance(expected, str) and isinstance(actual, str):
        return _normalize_status(expected, _key) == _normalize_status(actual, _key)
    return expected == actual


def _has_duplicate_keys(json_str: str) -> bool:
    """Return True if the JSON string contains any object with duplicate keys."""
    seen_dups = []

    def _pairs_hook(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            seen_dups.append(True)
        return dict(pairs)

    try:
        json.loads(json_str, object_pairs_hook=_pairs_hook)
    except Exception:
        pass
    return bool(seen_dups)


def compare_outputs(expected_str: str, actual_str: str) -> tuple[bool, str]:
    """
    Check that expected (from RST) is a subset of actual (from emulator).

    Dynamic keys (ARNs, timestamps, UUIDs, etc.) in the expected output have
    their values replaced with _ANY — the key must still be present in actual,
    but any value is accepted.  This catches missing fields while ignoring
    value differences that are inherently dynamic.

    Returns (match, reason).
    """
    if not expected_str:
        return True, "no expected output"

    # Skip comparison if expected JSON has duplicate keys (malformed RST output)
    if _has_duplicate_keys(expected_str):
        return True, "expected output has duplicate JSON keys — skipped"

    try:
        expected = json.loads(expected_str)
    except json.JSONDecodeError:
        return True, "expected output is not valid JSON — skipped"

    try:
        actual = json.loads(actual_str)
    except json.JSONDecodeError:
        return False, "actual output is not valid JSON"

    # Mark dynamic fields in expected with _ANY (key required, value unconstrained).
    # Do NOT strip dynamic fields from actual — we want to detect missing fields.
    expected_marked = mark_dynamic(expected)

    if is_subset(expected_marked, actual):
        return True, "match"

    # For the failure message, show cleaned versions (replace _ANY sentinel with "<dynamic>")
    def _replace_any(obj):
        if obj is _ANY:
            return "<dynamic>"
        if isinstance(obj, dict):
            return {k: _replace_any(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace_any(i) for i in obj]
        return obj

    exp_str = json.dumps(_replace_any(expected_marked), sort_keys=True, indent=2)
    act_str = json.dumps(actual, sort_keys=True, indent=2)
    reason = f"expected (subset):\n{exp_str}\nactual:\n{act_str}"
    return False, reason


def run_command(cmd, timeout=30):
    """Run a shell command, return result dict."""
    result = {
        "success": False,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "error": "",
    }
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ,
            executable="/bin/bash",
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["success"] = proc.returncode == 0
    except subprocess.TimeoutExpired:
        result["error"] = f"Command timed out after {timeout}s"
    except Exception as e:
        result["error"] = str(e)
    return result


def check_emulator_health(endpoint_url, timeout=10, retries=3):
    """Return True if the emulator responds on the given URL."""
    import urllib.request
    import urllib.error

    for _ in range(retries):
        try:
            urllib.request.urlopen(endpoint_url, timeout=timeout)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    return False


def reset_emulator(endpoint_url):
    """Delete all tables in the emulator to start from a clean state."""
    import urllib.request

    # Must use the same credentials as the 'vera' AWS profile so we hit the same
    # DynamoDB Local namespace (DynamoDB Local partitions tables by access key ID).
    _FAKE_AUTH = "AWS4-HMAC-SHA256 Credential=test/20000101/us-east-1/dynamodb/aws4_request, SignedHeaders=host, Signature=fake"
    _HEADERS = {
        "Content-Type": "application/x-amz-json-1.0",
        "Authorization": _FAKE_AUTH,
    }

    def ddb_request(target, body):
        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(body).encode(),
            headers={**_HEADERS, "X-Amz-Target": f"DynamoDB_20120810.{target}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

    try:
        table_names = ddb_request("ListTables", {}).get("TableNames", [])
    except Exception as e:
        print(f"  warning: could not list tables for reset: {e}")
        return

    for name in table_names:
        try:
            ddb_request("DeleteTable", {"TableName": name})
        except Exception:
            # Table may have deletion protection enabled; disable it first.
            try:
                ddb_request("UpdateTable", {
                    "TableName": name,
                    "DeletionProtectionEnabled": False,
                })
                ddb_request("DeleteTable", {"TableName": name})
            except Exception:
                pass

    # Also delete all backups (they persist independently of tables)
    backup_count = 0
    try:
        backups = ddb_request("ListBackups", {}).get("BackupSummaries", [])
        for b in backups:
            try:
                ddb_request("DeleteBackup", {"BackupArn": b["BackupArn"]})
                backup_count += 1
            except Exception:
                pass
    except Exception:
        pass

    # Wipe all vera state machine metadata (CI, replicas, PITR, backups) via internal endpoint.
    # This clears orphaned records from any credentials namespace, ensuring a truly clean slate.
    try:
        import urllib.request as _ur
        req = _ur.Request(
            endpoint_url.rstrip("/") + "/vera/reset-state",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _ur.urlopen(req, timeout=5)
    except Exception as e:
        print(f"  warning: could not reset vera state: {e}")

    deleted = []
    if table_names:
        deleted.append(f"{len(table_names)} table(s)")
    if backup_count:
        deleted.append(f"{backup_count} backup(s)")
    if deleted:
        print(f"  Reset: deleted {', '.join(deleted)}")
    else:
        print("  Reset: no tables to delete")


def save_checkpoint(results, checkpoint_file):
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_commands(cli_dir: Path):
    """
    Parse RST files and return:
      - commands: list of (cmd_str, expected_output, reset_before, rst_file, file_contents) tuples
      - total_rst_count: total number of RST files in cli_dir (including skipped ones)

    reset_before=True marks the first command of each Example block — the emulator is
    reset before running it, so each Example starts from a clean slate.
    Commands requiring IDs are skipped. Commands with file:// are now supported when
    file_contents were parsed from the RST; only skipped if file_contents are missing.
    """
    # Count all RST files (denominator)
    all_rst_files = sorted(Path(cli_dir).rglob("*.rst"))
    total_rst_count = len(all_rst_files)

    data = parse_aws_commands_from_directory(cli_dir, quiet=True)
    commands = []
    for rst_file, cmd_list in data.items():
        file_commands = [
            entry for entry in cmd_list
            if not entry["use_id"] and not entry["use_file"]
        ]
        seen_examples = set()
        for entry in file_commands:
            example_idx = entry.get("example_index", 0)
            is_first_in_example = example_idx not in seen_examples
            seen_examples.add(example_idx)
            commands.append((
                to_awscli_command(entry["cmd"]),
                entry.get("output", ""),
                is_first_in_example,  # reset_before: True for first command of each Example
                rst_file,
                entry.get("file_contents", {}),
            ))
    return commands, total_rst_count


def resolve_backup_arn(cmd: str, endpoint_url: str) -> str:
    """
    If cmd contains a hardcoded backup ARN placeholder, replace it with a real
    ARN fetched from the emulator via list-backups.

    Matches: --backup-arn arn:aws:dynamodb:...:table/<name>/backup/<suffix>
    Extracts the table name and fetches the most recent backup ARN for it.
    """
    import re, urllib.request
    pattern = r'(--backup-arn\s+)(arn:[^\s]+/backup/[^\s]+)'
    m = re.search(pattern, cmd)
    if not m:
        return cmd

    placeholder_arn = m.group(2)
    # Extract table name from the ARN: arn:...:table/<TableName>/backup/...
    table_match = re.search(r':table/([^/]+)/backup/', placeholder_arn)
    if not table_match:
        return cmd
    table_name = table_match.group(1)

    # Fetch real backup ARN from emulator
    _AUTH = "AWS4-HMAC-SHA256 Credential=test/20000101/us-east-1/dynamodb/aws4_request, SignedHeaders=host, Signature=fake"
    try:
        body = json.dumps({"TableName": table_name}).encode()
        req = urllib.request.Request(
            endpoint_url,
            data=body,
            headers={
                "Content-Type": "application/x-amz-json-1.0",
                "X-Amz-Target": "DynamoDB_20120810.ListBackups",
                "Authorization": _AUTH,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        summaries = data.get("BackupSummaries", [])
        if not summaries:
            return cmd  # no backup found, let command fail naturally
        real_arn = summaries[-1]["BackupArn"]  # most recent
        return cmd[:m.start(2)] + real_arn + cmd[m.end(2):]
    except Exception:
        return cmd  # on error, leave cmd unchanged


def write_temp_files(file_contents: dict, tmp_dir: Path) -> dict:
    """
    Write file_contents to tmp_dir. Returns a mapping of filename -> absolute path.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for filename, content in file_contents.items():
        dest = tmp_dir / filename
        dest.write_text(content, encoding="utf-8")
        written[filename] = str(dest)
    return written


def rewrite_file_refs(cmd: str, filename_to_path: dict) -> str:
    """
    Replace file://filename.json with file:///absolute/path/to/filename.json in cmd.
    """
    for filename, abs_path in filename_to_path.items():
        cmd = cmd.replace(f"file://{filename}", f"file://{abs_path}")
    return cmd


def run_evaluation(
    cli_dir,
    checkpoint_file="eval_results.json",
    start_from=0,
    endpoint_url="http://localhost:5005",
    rst_filter=None,
):
    commands, total_rst_count = load_commands(Path(cli_dir))
    if rst_filter:
        # Keep only commands belonging to the specified RST files (basename match)
        normalized = {f if f.endswith(".rst") else f + ".rst" for f in rst_filter}
        commands = [c for c in commands if Path(c[3]).name in normalized]
    print(f"Loaded {len(commands)} commands from {total_rst_count} RST files in {cli_dir}\n")

    print(f"Checking emulator at {endpoint_url}...")
    if not check_emulator_health(endpoint_url):
        print(f"✗ Emulator not responding at {endpoint_url}")
        print("  Start it with: uv run python main.py")
        sys.exit(1)
    print("✓ Emulator is healthy")

    if start_from == 0:
        print("Resetting emulator state...")
        reset_emulator(endpoint_url)
    print()

    # Temp directory for file:// parameters
    tmp_dir = Path(__file__).parent / "tmp"

    start_time = time.time()
    results = {
        "cli_dir": str(cli_dir),
        "endpoint_url": endpoint_url,
        "total_commands": len(commands),
        "total_rst_files": total_rst_count,
        "started_at": datetime.now().isoformat(),
        "commands": {},
    }

    if start_from > 0 and Path(checkpoint_file).exists():
        print(f"Resuming from index {start_from}...")
        with open(checkpoint_file, encoding="utf-8") as f:
            results = json.load(f)

    for idx in range(start_from, len(commands)):
        cmd, expected_output, reset_before, rst_file, file_contents = commands[idx]

        print(f"\n{'='*70}")
        print(f"Command {idx + 1}/{len(commands)}")
        print(f"{'='*70}")

        if reset_before and idx > 0:
            reset_emulator(endpoint_url)

        # Write any file:// parameters to the tmp directory and rewrite cmd
        if file_contents:
            filename_to_path = write_temp_files(file_contents, tmp_dir)
            cmd = rewrite_file_refs(cmd, filename_to_path)

        # Resolve hardcoded backup ARN placeholders with real ARNs from the emulator
        cmd = resolve_backup_arn(cmd, endpoint_url)

        print(f"  {cmd[:120]}{'...' if len(cmd) > 120 else ''}")

        cmd_result = run_command(cmd, timeout=30)

        output_match, match_reason = True, "not checked (command failed)"
        if cmd_result["success"]:
            output_match, match_reason = compare_outputs(
                expected_output, cmd_result["stdout"]
            )

        if cmd_result["success"] and output_match:
            print(f"  ✓ exit={cmd_result['exit_code']}  output=match")
        elif cmd_result["success"] and not output_match:
            print(f"  ~ exit={cmd_result['exit_code']}  output=MISMATCH")
            # Show first 400 chars of diff
            print(f"    {match_reason[:400]}")
        else:
            print(f"  ✗ exit={cmd_result['exit_code']}")
            if cmd_result["error"]:
                print(f"    error: {cmd_result['error']}")
            if cmd_result["stderr"]:
                print(f"    stderr: {cmd_result['stderr'][:300]}")

        results["commands"][idx] = {
            "command": cmd,
            "index": idx,
            "rst_file": rst_file,
            "reset_before": reset_before,
            "result": cmd_result,
            "expected_output": expected_output,
            "output_match": output_match,
            "match_reason": match_reason,
            "timestamp": datetime.now().isoformat(),
        }
        save_checkpoint(results, checkpoint_file)

    elapsed = time.time() - start_time
    total = len(results["commands"])
    total_rst = results.get("total_rst_files", 0)

    # Command-level counts
    exit_passed = sum(1 for r in results["commands"].values() if r["result"]["success"])
    output_matched = sum(
        1 for r in results["commands"].values()
        if r["result"]["success"] and r["output_match"]
    )
    exit_failed = total - exit_passed
    output_mismatched = exit_passed - output_matched

    # RST-level counts: an RST passes if ALL its runnable commands exit OK and output match
    rst_results: dict[str, list[bool]] = {}
    for r in results["commands"].values():
        rst = r.get("rst_file", "unknown")
        passed = r["result"]["success"] and r["output_match"]
        rst_results.setdefault(rst, []).append(passed)
    rst_passed = sum(1 for passes in rst_results.values() if all(passes))
    rst_with_commands = len(rst_results)
    rst_failed = rst_with_commands - rst_passed
    # RST files that had no runnable commands (all skipped) count as not-passed
    rst_no_commands = total_rst - rst_with_commands

    print(f"\n\n{'='*70}")
    print("EVALUATION COMPLETE")
    print(f"{'='*70}")
    print(f"RST files:        {rst_passed}/{total_rst}  ({rst_passed/total_rst*100:.1f}% pass)")
    print(f"  All cmds OK:    {rst_passed}")
    print(f"  Some cmd fail:  {rst_failed}")
    print(f"  No runnable cmd:{rst_no_commands}")
    print()
    print(f"Commands total:   {total}")
    print(f"Exit OK:          {exit_passed}  ({exit_passed/total*100:.1f}%)")
    print(f"  Output match:   {output_matched}  ({output_matched/total*100:.1f}%)")
    print(f"  Output mismatch:{output_mismatched}  ({output_mismatched/total*100:.1f}%)")
    print(f"Exit failed:      {exit_failed}  ({exit_failed/total*100:.1f}%)")
    print(f"Runtime: {elapsed:.1f}s")
    print(f"Results: {checkpoint_file}")

    # Print failing RST files
    failing_rst = sorted(rst for rst, passes in rst_results.items() if not all(passes))
    if failing_rst:
        print(f"\nFailing RST files ({len(failing_rst)}):")
        for rst in failing_rst:
            passes = rst_results[rst]
            n_fail = sum(1 for p in passes if not p)
            print(f"  {rst}  ({n_fail}/{len(passes)} cmds failed)")

    results["completed_at"] = datetime.now().isoformat()
    results["summary"] = {
        "total_rst_files": total_rst,
        "rst_passed": rst_passed,
        "rst_failed": rst_failed,
        "rst_no_runnable_commands": rst_no_commands,
        "total_commands": total,
        "exit_passed": exit_passed,
        "output_matched": output_matched,
        "output_mismatched": output_mismatched,
        "exit_failed": exit_failed,
        "runtime_seconds": round(elapsed, 2),
    }
    save_checkpoint(results, checkpoint_file)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate AWS CLI commands against vera-dynamodb"
    )
    parser.add_argument(
        "--cli-dir", "-d", default="cli/dynamodb",
        help="Directory with RST example files (default: cli/dynamodb)"
    )
    parser.add_argument(
        "--checkpoint", "-c", default="eval_results.json",
        help="Output JSON file (default: eval_results.json)"
    )
    parser.add_argument(
        "--start-from", "-s", type=int, default=0,
        help="Resume from this command index"
    )
    parser.add_argument(
        "--endpoint", "-e", default="http://localhost:5005",
        help="vera-dynamodb endpoint (default: http://localhost:5005)"
    )
    parser.add_argument(
        "--rst", "-r", nargs="+", metavar="FILE",
        help="Only run commands from these RST files (e.g. --rst query.rst put-item.rst)"
    )
    args = parser.parse_args()

    try:
        run_evaluation(args.cli_dir, args.checkpoint, args.start_from, args.endpoint, args.rst)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved.")
        sys.exit(0)


if __name__ == "__main__":
    main()
