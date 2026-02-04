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
        r'--[\w-]*-arn\b',     # Matches --arn-id, --arn-ids, etc.
        r'--arn\b',            # Matches --arn exactly
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


def parse_aws_commands(file_path):
    """Parse AWS CLI commands from an RST file with their outputs."""
    commands = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for lines that contain 'aws' command
        stripped = line.strip()
        if stripped.startswith('aws '):
            # Found an AWS command, now collect all continuation lines
            command_lines = [stripped]
            
            # Check for line continuations (backslash at end)
            j = i + 1
            while j < len(lines) and (command_lines[-1].endswith('\\') or command_lines[-1].endswith('^') or command_lines[-1].endswith('`')):
                next_line = lines[j].strip()
                if next_line:  # Skip empty lines
                    command_lines.append(next_line)
                j += 1
            
            # Join the command lines
            # handle ^ and ` in the command, replace with \\
            command_lines = [line.replace('^', '\\').replace('`', '\\') for line in command_lines]
            full_command = ' '.join(line.rstrip('\\').strip() for line in command_lines)
            
            # Extract output for this command
            output = extract_output(lines, j)
            
            # Check if command uses ID parameters
            use_id = has_id_parameter(full_command)
            use_file = has_file_parameter(full_command)
            
            commands.append({
                "cmd": full_command,
                "use_id": use_id,
                "use_file": use_file,
                "output": output
            })
            
            # Move index past the command we just processed
            i = j
        else:
            i += 1
    
    return commands


def main():
    """Parse all RST files and save AWS commands to JSON."""
    # Find all RST files in tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
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
            rel_path = str(rst_file.relative_to(tests_dir.parent))
            results[rel_path] = commands
            total_commands += len(commands)
    
    # Save to JSON file
    output_file = Path(__file__).parent / "aws_commands.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"Total AWS commands found: {total_commands}")
    print(f"Files with commands: {len(results)}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
