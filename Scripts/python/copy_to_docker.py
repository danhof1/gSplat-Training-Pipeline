#!/usr/bin/env python3
# copy_to_docker.py - Step 3: Copy converted data to Docker container

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

def run_command(cmd, check=True):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(cmd, check=check, text=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print_colored(f"Error executing command: {' '.join(cmd)}", Colors.RED)
        print_colored(f"Error message: {e.stderr}", Colors.RED)
        if check:
            sys.exit(1)
        return None

def check_container(container_name):
    """Check if the container exists and is running"""
    print_colored(f"Checking if container {container_name} is running...", Colors.YELLOW)
    cmd = ["docker", "ps", "-qf", f"name={container_name}"]
    container_id = run_command(cmd).strip()
    
    if not container_id:
        print_colored(f"Error: Container {container_name} not found or not running.", Colors.RED)
        print_colored("Available containers:", Colors.YELLOW)
        run_command(["docker", "ps"])
        sys.exit(1)
    
    return container_id

def copy_to_container(container_name, local_path, container_path):
    """Copy files from local path to container"""
    print_colored(f"Creating destination directory in container: {container_path}", Colors.YELLOW)
    run_command(["docker", "exec", container_name, "mkdir", "-p", container_path])
    
    print_colored("Copying files to container...", Colors.YELLOW)
    run_command(["docker", "cp", f"{local_path}/.", f"{container_name}:{container_path}"])
    
    print_colored("Verifying files in container...", Colors.YELLOW)
    run_command(["docker", "exec", container_name, "ls", "-la", container_path])

def clean_metadata_files(container_name, container_path):
    """Remove metadata files that might interfere with training"""
    print_colored("Removing metadata files that might interfere with training...", Colors.YELLOW)
    run_command([
        "docker", "exec", container_name, 
        "bash", "-c", f"find {container_path} -name '*.metadata.json' -delete"
    ])
    print_colored("Metadata files removed.", Colors.GREEN)

def main():
    parser = argparse.ArgumentParser(description='Step 3: Copy data to Docker container')
    parser.add_argument('--user-id', help='Firebase user ID')
    parser.add_argument('--input-path', help='Path to converted data')
    parser.add_argument('--container', help='Name of the Docker container')
    parser.add_argument('--container-path', default='/app/data', help='Destination path in container')
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
    
    print_colored(f"======= Step 3: Copying Data to Docker =======", Colors.BLUE)
    print_colored(f"User ID: {user_id}", Colors.YELLOW)
    print_colored(f"Input path: {input_path}", Colors.YELLOW)
    
    # Check if input path exists
    if not os.path.exists(input_path):
        print_colored(f"Error: Input path {input_path} does not exist", Colors.RED)
        sys.exit(1)
    
    # If container name is not provided, auto-detect the running container
    if not args.container:
        print_colored("No container specified, detecting running container...", Colors.YELLOW)
        container_id = run_command(["docker", "ps", "-q"]).strip()
        
        if not container_id:
            print_colored("Error: No Docker containers running", Colors.RED)
            sys.exit(1)
        
        if len(container_id.splitlines()) > 1:
            print_colored("Multiple containers are running, please specify one with --container", Colors.RED)
            print_colored("Available containers:", Colors.YELLOW)
            run_command(["docker", "ps"])
            sys.exit(1)
        
        container_name = run_command(["docker", "inspect", "--format='{{.Name}}'", container_id]).strip().replace("'", "").replace("/", "")
        print_colored(f"Found running container: {container_name}", Colors.GREEN)
    else:
        container_name = args.container
        check_container(container_name)
    
    # User-specific container path to avoid conflicts
    user_container_path = f"{args.container_path}/{user_id}"
    
    # Copy data to container
    copy_to_container(container_name, input_path, user_container_path)
    
    # Clean metadata files
    clean_metadata_files(container_name, user_container_path)
    
    print_colored("Data transfer to Docker completed successfully!", Colors.GREEN)
    
    # Update pipeline state for next step
    state.update({
        'user_id': user_id,
        'download_path': input_path,
        'container_name': container_name,
        'container_path': user_container_path,
        'step3_completed': True
    })
    
    with open(state_file, 'w') as f:
        json.dump(state, f)
    
    print_colored(f"Pipeline state updated in {state_file}", Colors.GREEN)
    print_colored(f"Files are available in the container at: {user_container_path}", Colors.BLUE)
    print_colored("Ready for Step 4: Run Training", Colors.BLUE)

if __name__ == "__main__":
    main()