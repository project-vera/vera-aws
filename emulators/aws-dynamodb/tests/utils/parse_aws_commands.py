#!/usr/bin/env python3
"""
Parser to extract AWS CLI commands and their outputs from RST test files.
"""

import re
import json
from pathlib import Path


def has_id_parameter(command):
    """Check if command contains any ID-related parameters."""
    id_patterns = [
        r'--[\w-]*-id\b',      # Matches --allocation-id, --group-id, --transit-gateway-attachment-id, etc.
        r'--id\b',             # Matches --id exactly
        r'--[\w-]*-ids\b',     # Matches --instance-ids, --vpc-endpoint-ids, etc.
        r'--ids\b',            # Matches --ids exactly
        # ARN patterns removed: vera emulator generates real ARNs dynamically,
        # so --backup-arn, --resource-arn etc. are now runnable with setup commands.
        r'--resources\b',      # Matches --resources exactly
    ]
    for pattern in id_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False

def has_file_parameter(command):
    """Check if command contains any file-related parameters. like file://xxx"""
    file_pattern = r'file://'
    return re.search(file_pattern, command, re.IGNORECASE) is not None


def extract_output(lines, start_idx):
    """Extract output section after a command."""
    output_lines = []
    i = start_idx
    
    # Look for "Output::" or "Command::" marker
    while i < len(lines):
        line = lines[i]
        if 'Output::' in line or 'output is returned' in line.lower() or 'produces no output' in line.lower():
            if 'no output' in line.lower() or 'produces no output' in line.lower():
                return ""
            # Found output section, skip to next line
            i += 1
            break
        i += 1
    
    # If we didn't find output marker, return empty
    if i >= len(lines):
        return ""
    
    # Collect output lines (indented content after Output::)
    while i < len(lines):
        line = lines[i]
        
        # Stop if we hit a non-indented line (except blank lines)
        if line.strip() and not line.startswith((' ', '\t')):
            break
        
        # Stop if we hit another example or section
        if line.strip().startswith('**') or line.strip().startswith('For more information'):
            break
            
        output_lines.append(line.rstrip())
        i += 1
    
    # Clean up the output
    output = '\n'.join(output_lines).strip()
    return output


def extract_file_contents(lines, start_idx, end_idx):
    """
    Extract all 'Contents of ``filename``::' blocks between start_idx and end_idx.
    Returns a dict mapping filename -> file content string.
    """
    file_contents = {}
    i = start_idx
    # Pattern: Contents of ``filename``::  or  Contents of the ``filename`` file::
    file_header_re = re.compile(r'Contents of(?: the)? ``([^`]+)``(?: file)?::')
    while i < end_idx:
        line = lines[i]
        m = file_header_re.search(line)
        if m:
            filename = m.group(1)
            # Collect indented content after the header line
            content_lines = []
            i += 1
            while i < end_idx:
                content_line = lines[i]
                # Stop if we hit a non-indented non-blank line
                if content_line.strip() and not content_line.startswith((' ', '\t')):
                    break
                content_lines.append(content_line.rstrip())
                i += 1
            content = '\n'.join(content_lines).strip()
            if content:
                file_contents[filename] = content
        else:
            i += 1
    return file_contents


def parse_aws_commands(file_path):
    """Parse AWS CLI commands from an RST file with their outputs."""
    commands = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_example = 0  # increments each time we see **Example N:** header
    i = 0
    while i < len(lines):
        line = lines[i]

        # Track Example boundaries (e.g. "**Example 1: ...**")
        stripped_line = line.strip()
        if stripped_line.startswith('**Example') and stripped_line.endswith('**'):
            current_example += 1
            i += 1
            continue

        # Look for lines that contain 'aws' command
        stripped = stripped_line
        if stripped.startswith('aws '):
            # Found an AWS command, now collect all continuation lines
            command_lines = [stripped]

            # Check for line continuations (backslash at end, or unclosed quotes)
            j = i + 1
            while j < len(lines):
                last = command_lines[-1]
                joined = ' '.join(command_lines)
                has_continuation = last.endswith('\\') or last.endswith('^') or last.endswith('`')
                # Count unescaped double-quotes in what we have so far
                unmatched_quotes = joined.count('"') % 2 == 1
                if not has_continuation and not unmatched_quotes:
                    break
                next_line = lines[j].strip()
                if next_line:
                    command_lines.append(next_line)
                j += 1

            # Join the command lines
            # handle ^ and ` in the command, replace with \\
            command_lines = [line.replace('^', '\\').replace('`', '\\') for line in command_lines]
            full_command = ' '.join(line.rstrip('\\').strip() for line in command_lines)

            # Find end of this command's section: the next aws command line or end of file
            # We need to find the next top-level 'aws ' line to bound file_contents extraction
            k = j
            while k < len(lines):
                next_stripped = lines[k].strip()
                if next_stripped.startswith('aws '):
                    break
                k += 1
            # file_contents are between end of command (j) and next command (k)
            file_contents = {}
            if has_file_parameter(full_command):
                file_contents = extract_file_contents(lines, j, k)

            # Extract output for this command
            output = extract_output(lines, j)

            # Check if command uses ID parameters
            use_id = has_id_parameter(full_command)
            # use_file is True only if file:// is referenced but content was not found in RST
            use_file = has_file_parameter(full_command) and not file_contents

            commands.append({
                "cmd": full_command,
                "use_id": use_id,
                "use_file": use_file,
                "file_contents": file_contents,
                "output": output,
                "example_index": current_example,
            })

            # Move index past the command we just processed
            i = j
        else:
            i += 1

    return commands

def parse_aws_commands_from_directory(directory: Path, quiet: bool = True) -> dict[str, list[dict]]:
    """Parse all RST files in a directory and return the total number of commands and the results."""
    results = {}
    if not directory.exists():
        if not quiet:
            print(f"Directory not found: {directory}")
        return results

    # Find all RST files in directory
    rst_files = sorted(directory.rglob("*.rst"))
    
    if not quiet:
        print(f"Found {len(rst_files)} RST files")
        print("Parsing commands...")
    
    total_commands = 0
    for rst_file in rst_files:
        commands = parse_aws_commands(rst_file)
        
        if commands:
            # Use relative path as key
            rel_path = str(rst_file.relative_to(directory))
            results[rel_path] = commands    
            total_commands += len(commands)

    if not quiet:
        print(f"Total commands found: {total_commands}")
    return results


def main():
    """Parse all RST files and save AWS commands to JSON."""
    # Find all RST files in cli directory
    # Script is in utils/, so go up one level to tests/ then look for cli/
    tests_dir = Path(__file__).parent.parent / "cli"
    
    if not tests_dir.exists():
        print(f"CLI directory not found: {tests_dir}")
        return
    
    rst_files = sorted(tests_dir.rglob("*.rst"))
    
    print(f"Found {len(rst_files)} RST files")
    print("Parsing commands...")
    
    # Dictionary to store results
    results = {}
    total_commands = 0
    
    for rst_file in rst_files:
        commands = parse_aws_commands(rst_file)
        
        if commands:
            # Use relative path as key
            rel_path = str(rst_file.relative_to(tests_dir))
            results[rel_path] = commands
            total_commands += len(commands)
    
    # Save to JSON file
    output_file = Path(__file__).parent.parent / "aws_commands.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"Total AWS commands found: {total_commands}")
    print(f"Files with commands after filtering: {len(results)}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
