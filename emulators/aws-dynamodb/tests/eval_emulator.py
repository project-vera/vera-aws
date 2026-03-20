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

# Keys whose values are dynamic (timestamps, ARNs, UUIDs, counters, sizes).
# Stripped from both expected and actual before comparison.
DYNAMIC_KEYS = {
    "CreationDateTime",
    "TableArn",
    "TableId",
    "IndexArn",
    "LatestStreamArn",
    "KMSMasterKeyArn",         # contains account ID and region, differs from real AWS
    "LatestStreamLabel",
    "LastIncreaseDateTime",
    "LastDecreaseDateTime",
    "LastUpdateToPayPerRequestDateTime",
    "ItemCount",
    "TableSizeBytes",
    "IndexSizeBytes",
    "TableNames",          # contains real account table names in RST golden output
    "NextToken",           # pagination token; value is fake in RST
    "NumberOfDecreasesToday",  # not returned by DynamoDB Local
}

# Status fields that are compared semantically rather than literally.
# vera completes transitions synchronously, so RST transient states
# (CREATING, DELETING, UPDATING) map to their terminal equivalents.
_STATUS_EQUIVALENCES = {
    "CREATING": "ACTIVE",
    "UPDATING": "ACTIVE",
    "DELETING": "DELETING",  # both sides should be DELETING or absent
}
STATUS_KEYS = {"TableStatus", "IndexStatus"}


def _normalize_status(value: str) -> str:
    """Map transient status to its terminal equivalent for comparison."""
    return _STATUS_EQUIVALENCES.get(value, value)


def strip_dynamic(obj):
    """Recursively remove dynamic keys from a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: strip_dynamic(v) for k, v in obj.items() if k not in DYNAMIC_KEYS}
    if isinstance(obj, list):
        return [strip_dynamic(item) for item in obj]
    return obj


def _sort_key(obj):
    return json.dumps(obj, sort_keys=True)


def is_subset(expected, actual, _key=None) -> bool:
    """
    Return True if every key/value in expected exists in actual (recursively).
    Lists of dicts are compared as unordered sets (order-independent).
    Status fields (TableStatus, IndexStatus) are compared after normalizing
    transient states (CREATING→ACTIVE, UPDATING→ACTIVE).
    """
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(
            k in actual and is_subset(v, actual[k], _key=k)
            for k, v in expected.items()
        )
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        try:
            exp_sorted = sorted(expected, key=_sort_key)
            act_sorted = sorted(actual, key=_sort_key)
            return all(is_subset(e, a) for e, a in zip(exp_sorted, act_sorted))
        except TypeError:
            return all(is_subset(e, a) for e, a in zip(expected, actual))
    if _key in STATUS_KEYS and isinstance(expected, str) and isinstance(actual, str):
        return _normalize_status(expected) == _normalize_status(actual)
    return expected == actual


def compare_outputs(expected_str: str, actual_str: str) -> tuple[bool, str]:
    """
    Check that expected (from RST) is a subset of actual (from emulator),
    after stripping dynamic keys from both.

    Returns (match, reason).
    """
    if not expected_str:
        return True, "no expected output"

    try:
        expected = json.loads(expected_str)
    except json.JSONDecodeError:
        return True, "expected output is not valid JSON — skipped"

    try:
        actual = json.loads(actual_str)
    except json.JSONDecodeError:
        return False, "actual output is not valid JSON"

    expected_clean = strip_dynamic(expected)
    actual_clean = strip_dynamic(actual)

    if is_subset(expected_clean, actual_clean):
        return True, "match"

    exp_str = json.dumps(expected_clean, sort_keys=True, indent=2)
    act_str = json.dumps(actual_clean, sort_keys=True, indent=2)
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

    _FAKE_AUTH = "AWS4-HMAC-SHA256 Credential=fake/20000101/us-east-1/dynamodb/aws4_request, SignedHeaders=host, Signature=fake"
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

    if table_names:
        print(f"  Reset: deleted {len(table_names)} table(s): {', '.join(table_names)}")
    else:
        print("  Reset: no tables to delete")


def save_checkpoint(results, checkpoint_file):
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_commands(cli_dir: Path):
    """
    Parse RST files and return list of (cmd_str, expected_output, reset_before) tuples.
    reset_before=True marks the first command of each Example block — the emulator is
    reset before running it, so each Example starts from a clean slate.
    Commands requiring IDs or file:// parameters are skipped.
    """
    data = parse_aws_commands_from_directory(cli_dir, quiet=True)
    commands = []
    for cmd_list in data.values():
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
            ))
    return commands


def run_evaluation(
    cli_dir,
    checkpoint_file="eval_results.json",
    start_from=0,
    endpoint_url="http://localhost:5005",
):
    commands = load_commands(Path(cli_dir))
    print(f"Loaded {len(commands)} commands from {cli_dir}\n")

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


    start_time = time.time()
    results = {
        "cli_dir": str(cli_dir),
        "endpoint_url": endpoint_url,
        "total_commands": len(commands),
        "started_at": datetime.now().isoformat(),
        "commands": {},
    }

    if start_from > 0 and Path(checkpoint_file).exists():
        print(f"Resuming from index {start_from}...")
        with open(checkpoint_file, encoding="utf-8") as f:
            results = json.load(f)

    for idx in range(start_from, len(commands)):
        cmd, expected_output, reset_before = commands[idx]

        print(f"\n{'='*70}")
        print(f"Command {idx + 1}/{len(commands)}")
        print(f"{'='*70}")

        if reset_before and idx > 0:
            reset_emulator(endpoint_url)

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
    exit_passed = sum(1 for r in results["commands"].values() if r["result"]["success"])
    output_matched = sum(
        1 for r in results["commands"].values()
        if r["result"]["success"] and r["output_match"]
    )
    exit_failed = total - exit_passed
    output_mismatched = exit_passed - output_matched

    print(f"\n\n{'='*70}")
    print("EVALUATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total:            {total}")
    print(f"Exit OK:          {exit_passed}  ({exit_passed/total*100:.1f}%)")
    print(f"  Output match:   {output_matched}  ({output_matched/total*100:.1f}%)")
    print(f"  Output mismatch:{output_mismatched}  ({output_mismatched/total*100:.1f}%)")
    print(f"Exit failed:      {exit_failed}  ({exit_failed/total*100:.1f}%)")
    print(f"Runtime: {elapsed:.1f}s")
    print(f"Results: {checkpoint_file}")

    results["completed_at"] = datetime.now().isoformat()
    results["summary"] = {
        "total": total,
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
    args = parser.parse_args()

    try:
        run_evaluation(args.cli_dir, args.checkpoint, args.start_from, args.endpoint)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved.")
        sys.exit(0)


if __name__ == "__main__":
    main()
