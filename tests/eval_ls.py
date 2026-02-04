#!/usr/bin/env python3
"""
Evaluate AWS CLI commands against LocalStack.
Runs each command in isolation with a fresh LocalStack restart.
"""

import json
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
    
    try:
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        result['exit_code'] = process.returncode
        result['stdout'] = process.stdout
        result['stderr'] = process.stderr
        result['success'] = process.returncode == 0
        
    except subprocess.TimeoutExpired:
        result['error'] = f'Command timed out after {timeout}s'
    except Exception as e:
        result['error'] = str(e)
    
    return result


def restart_localstack(timeout=60, retry=3):
    """
    Restart LocalStack.
    
    Returns:
        bool: True if restart successful, False otherwise
    """
    print("  → Restarting LocalStack...", flush=True)
    
    result = run_command('localstack restart', timeout=timeout)
    
    if result['success']:
        # Wait a bit for LocalStack to be ready
        print("  → Waiting for LocalStack to be ready...", flush=True)
        time.sleep(5)
        return True
    else:
        print(f"  ✗ Failed to restart LocalStack: {result.get('error') or result.get('stderr')}", flush=True)
        if retry > 0:
            return restart_localstack(timeout, retry - 1)
        else:
            return False


def save_checkpoint(results, checkpoint_file):
    """Save results to checkpoint file."""
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def run_evaluation(script_file, checkpoint_file='eval_results.json', start_from=0):
    """
    Run evaluation of commands from bash script.
    
    Args:
        script_file: Path to bash script with commands
        checkpoint_file: Path to save results JSON
        start_from: Command index to start from (for resuming)
    """
    # Parse commands
    print(f"Parsing commands from: {script_file}")
    commands = parse_bash_script(script_file)
    print(f"Total commands to evaluate: {len(commands)}\n")
    
    if len(commands) == 0:
        print("No commands found in script.")
        return
    
    # Load existing results if resuming
    results = {
        'script_file': str(script_file),
        'total_commands': len(commands),
        'started_at': datetime.now().isoformat(),
        'commands': {}
    }
    
    if start_from > 0 and Path(checkpoint_file).exists():
        print(f"Resuming from command index {start_from}...")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    
    # Main evaluation loop
    for idx in range(start_from, len(commands)):
        cmd = commands[idx]
        
        print(f"\n{'='*80}")
        print(f"Command {idx + 1}/{len(commands)}")
        print(f"{'='*80}")
        print(f"Command: {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
        
        # Step 1: Restart LocalStack
        restart_success = restart_localstack()
        
        if not restart_success:
            # Save result even if restart failed
            results['commands'][idx] = {
                'command': cmd,
                'index': idx,
                'restart_success': False,
                'result': None,
                'timestamp': datetime.now().isoformat()
            }
            save_checkpoint(results, checkpoint_file)
            print(f"  ✗ Failed to restart LocalStack, stopping evaluation")
            # should stop the evaluation
            break
        
        # Step 2: Run the command
        print(f"  → Running command...", flush=True)
        cmd_result = run_command(cmd, timeout=30)
        
        # Print result summary
        if cmd_result['success']:
            print(f"  ✓ Success (exit code: {cmd_result['exit_code']})")
        else:
            print(f"  ✗ Failed (exit code: {cmd_result['exit_code']})")
            if cmd_result['error']:
                print(f"    Error: {cmd_result['error']}")
            if cmd_result['stderr']:
                print(f"    Stderr: {cmd_result['stderr'][:200]}...")
        
        # Step 3: Save result
        results['commands'][idx] = {
            'command': cmd,
            'index': idx,
            'restart_success': True,
            'result': cmd_result,
            'timestamp': datetime.now().isoformat()
        }
        
        # Step 4: Save checkpoint
        print(f"  → Saving checkpoint...", flush=True)
        save_checkpoint(results, checkpoint_file)
    
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
    print(f"\nResults saved to: {checkpoint_file}")
    
    results['completed_at'] = datetime.now().isoformat()
    results['summary'] = {
        'total': total,
        'successful': successful,
        'failed': failed,
        'skipped': skipped
    }
    save_checkpoint(results, checkpoint_file)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Evaluate AWS CLI commands against LocalStack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run evaluation on all commands
  python eval_ls.py test.sh
  
  # Resume from command index 10
  python eval_ls.py test.sh --start-from 10
  
  # Use custom checkpoint file
  python eval_ls.py test.sh --checkpoint my_results.json
        """
    )
    
    parser.add_argument(
        'script_file',
        help='Bash script file containing commands to evaluate'
    )
    
    parser.add_argument(
        '--checkpoint',
        '-c',
        default='eval_results.json',
        help='Checkpoint file to save results (default: eval_results.json)'
    )
    
    parser.add_argument(
        '--start-from',
        '-s',
        type=int,
        default=0,
        help='Command index to start from (for resuming, default: 0)'
    )
    
    args = parser.parse_args()
    
    # Check if script file exists
    script_path = Path(args.script_file)
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}", file=sys.stderr)
        sys.exit(1)
    
    # Run evaluation
    try:
        run_evaluation(script_path, args.checkpoint, args.start_from)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        sys.exit(0)


if __name__ == "__main__":
    main()
