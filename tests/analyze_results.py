#!/usr/bin/env python3
"""
Analyze evaluation results from eval_ls.py
"""

import json
import sys
from pathlib import Path
from collections import Counter


def analyze_results(results_file):
    """Analyze evaluation results and print accuracy score."""
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count successful commands
    commands = data.get('commands', {})
    
    if not commands:
        print("No command results found.")
        return
    
    successful = 0
    total = len(commands)
    
    for cmd_data in commands.values():
        if cmd_data.get('restart_success') and cmd_data.get('result'):
            if cmd_data['result']['success']:
                successful += 1
    
    # Print simple accuracy score
    print(f"{successful}/{total}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze evaluation results from eval_ls.py'
    )
    
    parser.add_argument(
        'results_file',
        default='eval_results.json',
        nargs='?',
        help='Results JSON file (default: eval_results.json)'
    )
    
    args = parser.parse_args()
    
    # Check if results file exists
    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)
    
    analyze_results(results_path)


if __name__ == "__main__":
    main()
