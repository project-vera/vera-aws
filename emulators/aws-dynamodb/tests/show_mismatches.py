#!/usr/bin/env python3
"""
Show output mismatches from an eval results JSON file.

Usage:
  python show_mismatches.py eval_results_fix.json
  python show_mismatches.py eval_results_fix.json --rst scan.rst

Output is written to <input_basename>.out in the same directory.
"""

import json
import sys
from pathlib import Path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Show output mismatches from eval results"
    )
    parser.add_argument("input", help="eval results JSON file")
    parser.add_argument("--rst", nargs="*", help="filter to specific RST file(s)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent / input_path

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    commands = data.get("commands", {})

    rst_filter = None
    if args.rst:
        rst_filter = {r if r.endswith(".rst") else r + ".rst" for r in args.rst}

    mismatches = []
    for idx, entry in sorted(commands.items(), key=lambda x: int(x[0])):
        if rst_filter and entry.get("rst_file") not in rst_filter:
            continue
        result = entry.get("result", {})
        if not result.get("success"):
            continue
        if entry.get("output_match"):
            continue
        mismatches.append(entry)

    output_path = input_path.with_suffix(".out")
    lines = []

    lines.append(f"Output mismatches: {len(mismatches)}")
    lines.append("=" * 70)

    for entry in mismatches:
        idx = entry.get("index", "?")
        rst = entry.get("rst_file", "")
        cmd = entry.get("command", "")
        expected = entry.get("expected_output", "")
        actual = entry.get("result", {}).get("stdout", "")
        reason = entry.get("match_reason", "")

        lines.append(f"\n[{idx}] {rst}")
        lines.append(f"CMD: {cmd}")
        lines.append("")

        lines.append("EXPECTED:")
        if expected:
            try:
                lines.append(json.dumps(json.loads(expected), indent=2))
            except json.JSONDecodeError:
                lines.append(expected)
        else:
            lines.append("(empty)")

        lines.append("")
        lines.append("ACTUAL:")
        if actual:
            try:
                lines.append(json.dumps(json.loads(actual), indent=2))
            except json.JSONDecodeError:
                lines.append(actual)
        else:
            lines.append("(empty)")

        lines.append("")
        lines.append("-" * 70)

    output = "\n".join(lines) + "\n"

    output_path.write_text(output, encoding="utf-8")
    print(f"Wrote {len(mismatches)} mismatches to {output_path}")


if __name__ == "__main__":
    main()
