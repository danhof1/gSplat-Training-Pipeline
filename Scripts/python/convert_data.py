#!/usr/bin/env python3
# convert_data.py - Step 2: Convert downloaded data

import os
import sys
import json
import argparse
from pathlib import Path
import subprocess

# ANSI color codes for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

def print_colored(message, color):
    """Print colored message to terminal"""
    print(f"{color}{message}{Colors.ENDC}")

def run_convert_script(source_path, convert_script_path):
    """Run the convert.py script on the data before sending to Docker"""
    print_colored(f"Running conversion script on data: {source_path}...", Colors.YELLOW)
    
    # Build the conversion command
    convert_cmd = [
        "python",
        os.path.join(convert_script_path, "convert.py"),
        "-s", source_path
    ]
    
    # Execute the conversion command
    print_colored("Executing conversion command:", Colors.YELLOW)
    print_colored(" ".join(convert_cmd), Colors.YELLOW)
    
    # Run with live output streaming
    process = subprocess.Popen(
        convert_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        cwd=convert_script_path  # Set working directory to script location
    )
    
    # Stream the output
    for line in process.stdout:
        print(line, end='')
    
    # Wait for process to complete
    process.wait()
    
    if process.returncode != 0:
        print_colored("Conversion failed.", Colors.RED)
        return False
    
    print_colored("Conversion completed successfully!", Colors.GREEN)
    return True

def main():
    parser = argparse.ArgumentParser(description='Step 2: Convert downloaded data')
    parser.add_argument('--user-id', help='Firebase user ID')
    parser.add_argument('--input-path', help='Path to downloaded data')
    parser.add_argument('--convert-script-path', default='/home/h702839428/Desktop/Full_Project/Gauss_Project/gaussian-splatting',
                      help='Path to the directory containing convert.py')
    parser.add_argument('--state-file', help='Path to pipeline state file')
    
    args = parser.parse_args()
    
    # Check if we have a state file and load it if available
    if args.state_file and os.path.exists(args.state_file):
        with open(args.state_file, 'r') as f:
            state = json.load(f)
        
        # Use state values if arguments aren't provided
        user_id = args.user_id or state.get('user_id')
        input_path = args.input_path or state.get('download_path')
        base_path = os.path.dirname(os.path.dirname(args.state_file)) if args.state_file else None
    else:
        # If we don't have a state file, we need explicit arguments
        if not args.user_id or not args.input_path:
            print_colored("Error: user-id and input-path are required if no state file is provided", Colors.RED)
            sys.exit(1)
        
        user_id = args.user_id
        input_path = args.input_path
        base_path = os.path.dirname(os.path.dirname(input_path))
        
        # Create a state file for future steps
        state = {
            'user_id': user_id,
            'download_path': input_path
        }
    
    # Create state file path if not provided
    if not args.state_file and base_path:
        state_file = os.path.join(base_path, "pipeline_state.json")
    else:
        state_file = args.state_file
    
    print_colored(f"======= Step 2: Converting Data =======", Colors.BLUE)
    print_colored(f"User ID: {user_id}", Colors.YELLOW)
    print_colored(f"Input path: {input_path}", Colors.YELLOW)
    
    # Check if input path exists
    if not os.path.exists(input_path):
        print_colored(f"Error: Input path {input_path} does not exist", Colors.RED)
        sys.exit(1)
    
    # Check if conversion script exists
    convert_script = os.path.join(args.convert_script_path, "convert.py")
    if not os.path.isfile(convert_script):
        print_colored(f"Error: Conversion script not found at {convert_script}", Colors.RED)
        sys.exit(1)
    
    # Run the conversion script
    if run_convert_script(input_path, args.convert_script_path):
        print_colored("Conversion completed successfully!", Colors.GREEN)
        
        # Update pipeline state for next step
        state.update({
            'user_id': user_id,
            'download_path': input_path,
            'convert_script_path': args.convert_script_path,
            'step2_completed': True
        })
        
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        print_colored(f"Pipeline state updated in {state_file}", Colors.GREEN)
        print_colored("Ready for Step 3: Copy to Docker", Colors.BLUE)
    else:
        print_colored("Conversion failed, pipeline cannot continue.", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()