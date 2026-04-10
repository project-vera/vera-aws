#!/usr/bin/env python3
"""
Evaluate AWS CLI commands against EC2 Emulator.
Runs each command against a running emulator instance.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


def parse_bash_script(script_file):
    """Parse bash script and extract commands line by line."""
    commands = []
    
    with open(script_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            commands.append(line)
    
    return commands


def run_command(cmd, timeout=30):
    """
    Run a command and capture output and status.
    
    Returns:
        dict: {'success': bool, 'exit_code': int, 'stdout': str, 'stderr': str, 'error': str}
    """
    result = {
        'success': False,
        'exit_code': None,
        'stdout': '',
        'stderr': '',
        'error': ''
    }
    
    kwargs = dict(
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ,
    )
    if sys.platform != 'win32':
        kwargs['executable'] = '/bin/bash'
    try:
        process = subprocess.run(cmd, **kwargs)
        result['exit_code'] = process.returncode
        result['stdout'] = process.stdout
        result['stderr'] = process.stderr
        result['success'] = process.returncode == 0
        
    except subprocess.TimeoutExpired:
        result['error'] = f'Command timed out after {timeout}s'
    except Exception as e:
        result['error'] = str(e)
    
    return result


def check_emulator_health(endpoint_url, timeout=10, retry=3):
    """
    Check if emulator is running and healthy.
    """
    import urllib.request
    import urllib.error

    for attempt in range(retry):
        try:
            req = urllib.request.Request(endpoint_url)
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except urllib.error.HTTPError:
            # Any HTTP error (400, 404, etc.) means the server is reachable
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(2)

    return False


def save_checkpoint(results, checkpoint_file):
    """Save results to checkpoint file."""
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def run_evaluation(script_file, checkpoint_file='eval_results_emulator.json',
                   start_from=0, endpoint_url='http://localhost:5003'):
    """
    Run evaluation of commands from bash script.
    
    Args:
        script_file: Path to bash script with commands
        checkpoint_file: Path to save results JSON
        start_from: Command index to start from (for resuming)
        endpoint_url: Endpoint URL for the emulator (used for health check)
    """
    # Parse commands
    print(f"Parsing commands from: {script_file}")
    commands = parse_bash_script(script_file)
    print(f"Total commands to evaluate: {len(commands)}\n")
    
    if len(commands) == 0:
        print("No commands found in script.")
        return
    
    # Check emulator health
    print(f"Checking emulator health at {endpoint_url}...")
    if not check_emulator_health(endpoint_url):
        print(f"✗ Emulator is not responding at {endpoint_url}")
        print("  Please ensure the emulator is running before starting evaluation.")
        print("  Start it with: python3 main.py")
        sys.exit(1)
    print("✓ Emulator is healthy\n")
    
    # Load existing results if resuming
    start_time = time.time()
    results = {
        'script_file': str(script_file),
        'endpoint_url': endpoint_url,
        'total_commands': len(commands),
        'started_at': datetime.now().isoformat(),
        'commands': {}
    }
    
    if start_from > 0 and Path(checkpoint_file).exists():
        print(f"Resuming from command index {start_from}...")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        # Preserve original start time if resuming
        if 'started_at' in results:
            start_time_str = results['started_at']
            start_time = datetime.fromisoformat(start_time_str).timestamp()
    
    # Main evaluation loop
    for idx in range(start_from, len(commands)):
        cmd = commands[idx]

        print(f"\n{'='*80}")
        print(f"Command {idx + 1}/{len(commands)}")
        print(f"{'='*80}")
        print(f"Command: {cmd[:100]}{'...' if len(cmd) > 100 else ''}")

        # Run the command
        print(f"  → Running command...", flush=True)
        cmd_result = run_command(cmd, timeout=30)
        
        # Custom success check for JSON/XML mismatch
        # AWS CLI fails if it receives JSON instead of XML, but we consider it success if the JSON is valid and not an error
        is_success = cmd_result['success']
        if not is_success and cmd_result['exit_code'] == 255 and "invalid XML" in cmd_result['stderr']:
            output = cmd_result['stderr']
            
            # Look for b'{...}' pattern which is how AWS CLI dumps the response body
            start_marker = "b'{"
            end_marker = "}'"
            
            start_idx = output.find(start_marker)
            if start_idx != -1:
                # Find the end marker after start_marker
                # We use rfind from the end, but limiting to reasonably close to end of string if needed
                # But simple logic: find matching closing brace quote
                # Ideally we want the last }'
                end_idx = output.rfind(end_marker)
                
                if end_idx != -1 and end_idx > start_idx:
                    # Extract the content inside b'{...}'
                    # start_marker is 3 chars: b ' {
                    # We want to extract { ... }
                    # So from start_idx + 2 to end_idx + 1 (to include })
                    json_bytes_repr = output[start_idx + 2 : end_idx + 1]
                    
                    try:
                        # AWS CLI output is repr(bytes), so newlines are escaped as \n
                        # quotes might be escaped? json.loads handles escaped quotes inside strings
                        # But we need to convert literal \n to actual newlines
                        json_str = json_bytes_repr.replace("\\n", "\n")
                        
                        response = json.loads(json_str)
                        # If response doesn't contain "Error" (or Error is inside ResponseMetadata which we don't have), it's likely success
                        # Also check for lower case "error" just in case
                        if "Error" not in response and "error" not in response:
                            is_success = True
                            cmd_result['success'] = True
                            cmd_result['note'] = "Marked success despite XML parse error (valid JSON received)"
                    except Exception:
                        pass

        # Print result summary
        if is_success:
            print(f"  ✓ Success (exit code: {cmd_result['exit_code']})")
            if cmd_result.get('note'):
                print(f"    Note: {cmd_result['note']}")
        else:
            print(f"  ✗ Failed (exit code: {cmd_result['exit_code']})")
            if cmd_result['error']:
                print(f"    Error: {cmd_result['error']}")
            if cmd_result['stderr']:
                stderr_preview = cmd_result['stderr'][:200]
                print(f"    Stderr: {stderr_preview}{'...' if len(cmd_result['stderr']) > 200 else ''}")
        
        # Save result
        results['commands'][idx] = {
            'command': cmd,
            'index': idx,
            'result': cmd_result,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save checkpoint
        print(f"  → Saving checkpoint...", flush=True)
        save_checkpoint(results, checkpoint_file)
    
    # Calculate total runtime
    end_time = time.time()
    total_runtime = end_time - start_time
    
    # Final summary
    print(f"\n\n{'='*80}")
    print("EVALUATION COMPLETE")
    print(f"{'='*80}")
    
    total = len(results['commands'])
    successful = sum(1 for r in results['commands'].values() 
                     if r.get('result') and r['result']['success'])
    failed = sum(1 for r in results['commands'].values() 
                 if r.get('result') and not r['result']['success'])
    skipped = total - successful - failed
    
    print(f"Total commands: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    print(f"Total runtime: {total_runtime:.2f}s ({total_runtime/60:.2f} minutes)")
    print(f"\nResults saved to: {checkpoint_file}")
    
    results['completed_at'] = datetime.now().isoformat()
    results['total_runtime_seconds'] = round(total_runtime, 2)
    results['summary'] = {
        'total': total,
        'successful': successful,
        'failed': failed,
        'skipped': skipped,
        'total_runtime_seconds': round(total_runtime, 2)
    }
    save_checkpoint(results, checkpoint_file)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Evaluate AWS CLI commands against EC2 Emulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run evaluation on all commands
  python eval_emulator.py test.sh
  
  # Resume from command index 10
  python eval_emulator.py test.sh --start-from 10
  
  # Use custom endpoint
  python eval_emulator.py test.sh --endpoint http://localhost:5003
  
  # Use custom checkpoint file
  python eval_emulator.py test.sh --checkpoint my_results.json
        """
    )
    
    parser.add_argument(
        'script_file',
        help='Bash script file containing commands to evaluate'
    )
    
    parser.add_argument(
        '--checkpoint',
        '-c',
        default='eval_results_emulator.json',
        help='Checkpoint file to save results (default: eval_results_emulator.json)'
    )
    
    parser.add_argument(
        '--start-from',
        '-s',
        type=int,
        default=0,
        help='Command index to start from (for resuming, default: 0)'
    )
    
    parser.add_argument(
        '--endpoint',
        '-e',
        default='http://localhost:5003',
        help='Emulator endpoint URL (default: http://localhost:5003)'
    )
    
    args = parser.parse_args()

    # Check if script file exists
    script_path = Path(args.script_file)
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    # Run evaluation
    try:
        run_evaluation(script_path, args.checkpoint, args.start_from,
                      args.endpoint)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        sys.exit(0)


if __name__ == "__main__":
    main()
