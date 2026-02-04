#!/usr/bin/env python3
"""
Script to print AWS CLI commands with a custom endpoint URL.
Useful for testing with LocalStack or other AWS mock services.
"""

import json
import sys
from pathlib import Path


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


def print_commands_with_endpoint(json_file, endpoint_url, include_id=None, include_file=None):
    """
    Load commands from JSON and print them with custom endpoint.
    
    Args:
        json_file: Path to the JSON file
        endpoint_url: Endpoint URL to add to commands
        filter_use_id: Optional boolean to filter by use_id field (True/False/None for all)
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_commands = 0
    printed_commands = 0
    
    for file_path, commands in data.items():
        for cmd_data in commands:
            total_commands += 1
            
            # Apply include filters if specified
            if cmd_data['use_id'] and not include_id:
                # print(f"Skipping command: {cmd_data['cmd']} (uses ID parameters)", file=sys.stderr)
                continue
            if cmd_data['use_file'] and not include_file:
                # print(f"Skipping command: {cmd_data['cmd']} (uses file parameters)", file=sys.stderr)
                continue

            # Add endpoint and print
            modified_cmd = add_endpoint_to_command(cmd_data['cmd'], endpoint_url)
            print(modified_cmd)
            printed_commands += 1
    
    # Print summary to stderr so it doesn't interfere with command output
    print(f"\n# Total commands: {total_commands}", file=sys.stderr)
    print(f"# Printed: {printed_commands}", file=sys.stderr)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Print AWS CLI commands with custom endpoint URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Print all commands with LocalStack endpoint
  python print_commands_with_endpoint.py --endpoint http://localhost:4566

  # Print only commands without ID parameters (more likely to work in fresh environment)
  python print_commands_with_endpoint.py --endpoint http://localhost:4566 --no-id
  
  # Print only commands with ID parameters
  python print_commands_with_endpoint.py --endpoint http://localhost:4566 --with-id
  
  # Save to a file
  python print_commands_with_endpoint.py --endpoint http://localhost:4566 > commands.sh
        """
    )
    
    parser.add_argument(
        '--endpoint',
        '-e',
        # required=True,
        default='http://localhost:4566',
        help='Endpoint URL (e.g., http://localhost:4566)'
    )
    
    parser.add_argument(
        '--json-file',
        '-j',
        default='aws_commands.json',
        help='Path to JSON file (default: aws_commands.json)'
    )
    
    parser.add_argument(
        '--include-file',
        action='store_true',
        help='Only print commands that use file parameters'
    )

    parser.add_argument(
        '--include-id',
        action='store_true',
        help='Only print commands that use ID parameters'
    )
    
    args = parser.parse_args()
    
    # Determine filter
    include_id = False
    include_file = False
    if args.include_file:
        include_file = True
    
    if args.include_id:
        include_id = True
    
    # Check if JSON file exists
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)
    
    print_commands_with_endpoint(json_path, args.endpoint, include_id, include_file)


if __name__ == "__main__":
    main()
