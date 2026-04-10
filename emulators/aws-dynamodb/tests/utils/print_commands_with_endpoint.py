#!/usr/bin/env python3
"""
Script to print AWS CLI commands for testing.
Parses RST files from cli directory and outputs them with either:
- awscli wrapper (default)
- --endpoint-url for LocalStack (--ls flag)
"""

import sys
from pathlib import Path
from utils.parse_aws_commands import parse_aws_commands_from_directory


def add_endpoint_to_command(cmd, endpoint_url):
    """
    Add endpoint URL to an AWS CLI command.
    Inserts --endpoint-url after 'aws' and before the service name.
    
    Example:
        Input: "aws ec2 describe-instances --region us-east-1"
        Output: "aws --endpoint-url=http://localhost:4566 ec2 describe-instances --region us-east-1"
    """
    if not cmd.startswith('aws '):
        return cmd
    
    # Split at 'aws ' and insert endpoint after it
    rest_of_cmd = cmd[4:]  # Remove 'aws '
    return f"aws --endpoint-url={endpoint_url} {rest_of_cmd}"


def to_awscli_command(cmd):
    """
    Convert an 'aws ...' command to use the awscli wrapper.

    Example:
        Input:  "aws ec2 describe-instances --region us-east-1"
        Output: "awscli ec2 describe-instances --region us-east-1"
    """
    if not cmd.startswith('aws '):
        return cmd
    return f"awscli {cmd[4:]}"


def print_commands(data, include_id=None, include_file=None, use_localstack=False, endpoint_url=None):
    """
    Print commands from parsed data.

    Args:
        data: Dictionary of parsed commands from parse_aws_commands_from_directory
        include_id: Include commands that require ID parameters
        include_file: Include commands that require file:// parameters
        use_localstack: If True, add --endpoint-url for LocalStack
        endpoint_url: Endpoint URL to use (only when use_localstack=True)
    """
    total_commands = 0
    printed_commands = 0

    for file_path, commands in data.items():
        for cmd_data in commands:
            total_commands += 1

            # Apply include filters if specified
            if cmd_data['use_id'] and not include_id:
                continue
            if cmd_data['use_file'] and not include_file:
                continue

            # Transform command based on mode
            if use_localstack:
                print(add_endpoint_to_command(cmd_data['cmd'], endpoint_url))
            else:
                print(to_awscli_command(cmd_data['cmd']))
            printed_commands += 1

    # Print summary to stderr so it doesn't interfere with command output
    print(f"\n# Total commands: {total_commands}", file=sys.stderr)
    print(f"# After filtering: {printed_commands}", file=sys.stderr)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Print AWS CLI commands for testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate commands for emulator (using awscli wrapper)
  python print_commands_with_endpoint.py > test.sh

  # Generate commands for LocalStack
  python print_commands_with_endpoint.py --ls > test_ls.sh

  # Generate commands for LocalStack with custom endpoint
  python print_commands_with_endpoint.py --ls --endpoint http://localhost:4566 > test_ls.sh

  # Include commands with ID parameters
  python print_commands_with_endpoint.py --include-id > test.sh
        """
    )

    parser.add_argument(
        '--cli-dir',
        '-d',
        default='cli',
        help='Path to CLI directory with RST files (default: cli)'
    )

    parser.add_argument(
        '--ls',
        action='store_true',
        help='Generate commands for LocalStack (adds --endpoint-url)'
    )

    parser.add_argument(
        '--endpoint',
        '-e',
        default='http://localhost:4566',
        help='Endpoint URL for LocalStack (default: http://localhost:4566)'
    )

    parser.add_argument(
        '--include-file',
        action='store_true',
        help='Include commands that use file parameters'
    )

    parser.add_argument(
        '--include-id',
        action='store_true',
        help='Include commands that use ID parameters'
    )

    args = parser.parse_args()

    # Check if CLI directory exists
    cli_dir = Path(args.cli_dir)
    if not cli_dir.exists():
        print(f"Error: CLI directory not found: {cli_dir}", file=sys.stderr)
        print(f"Please ensure the directory exists or specify with --cli-dir", file=sys.stderr)
        sys.exit(1)

    # Parse RST files from cli directory
    mode = "LocalStack" if args.ls else "Emulator (awscli wrapper)"
    print(f"Parsing RST files from: {cli_dir}", file=sys.stderr)
    print(f"Mode: {mode}", file=sys.stderr)
    if args.ls:
        print(f"Endpoint: {args.endpoint}", file=sys.stderr)
    
    data = parse_aws_commands_from_directory(cli_dir, quiet=True)
    
    if not data:
        print(f"Error: No commands found in {cli_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Count total commands for summary
    total_in_data = sum(len(cmds) for cmds in data.values())
    print(f"Found {len(data)} files with {total_in_data} commands", file=sys.stderr)
    print("", file=sys.stderr)  # Blank line for readability
    
    # Print commands
    print_commands(data, args.include_id, args.include_file, args.ls, args.endpoint)


if __name__ == "__main__":
    main()
