#!/usr/bin/env python3
# run_training.py - Step 4: Run training in Docker container

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

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

def activate_conda_env(container_name):
    """Check available conda environments in the container"""
    print_colored("Checking conda environments in container...", Colors.YELLOW)
    cmd = [
        "docker", "exec", container_name,
        "bash", "-c", "source /opt/conda/etc/profile.d/conda.sh && conda env list"
    ]
    conda_envs = run_command(cmd)
    print_colored("Available conda environments:", Colors.YELLOW)
    print(conda_envs)
    
    # Find the appropriate environment name based on what's available
    # Default to "sugar" since we see it in the output
    env_name = "sugar"
    
    # Try to find the environment that contains "gaussian" first (your preferred env)
    for line in conda_envs.splitlines():
        if "gaussian" in line.lower():
            env_name = line.split()[0]
            break
    
    # If no gaussian environment found, look for other likely environments in priority order
    if env_name == "sugar":
        print_colored("No gaussian environment found, using 'sugar' environment.", Colors.YELLOW)
    
    print_colored(f"Will use conda environment: {env_name}", Colors.GREEN)
    return env_name

def run_training(container_name, container_path, user_id, override_env=''):
    """Run the training pipeline in the container with proper conda environment"""
    # First, activate the conda environment to ensure dependencies are available
    if override_env:
        env_name = override_env
        print_colored(f"Using provided conda environment: {env_name}", Colors.GREEN)
    else:
        env_name = activate_conda_env(container_name)
    
    print_colored(f"Starting training pipeline on {container_path} for user {user_id}...", Colors.GREEN)
    
    # Build the training command with conda environment activation
    train_cmd = [
        "docker", "exec", "-it", container_name,
        "bash", "-c", 
        f"cd /app && source /opt/conda/etc/profile.d/conda.sh && conda activate {env_name} && "
        f"python train_full_pipeline.py -s {container_path} -r dn_consistency --high_poly True --export_obj True"
    ]
    
    # Execute the training command
    print_colored("Executing training command:", Colors.YELLOW)
    print_colored(" ".join(train_cmd), Colors.YELLOW)
    
    # Run with live output streaming
    process = subprocess.Popen(
        train_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Stream the output
    for line in process.stdout:
        print(line, end='')
    
    # Wait for process to complete
    process.wait()
    
    if process.returncode != 0:
        print_colored("Training pipeline completed with errors.", Colors.RED)
        return False
    
    print_colored("Training pipeline completed successfully!", Colors.GREEN)
    return True

def main():
    parser = argparse.ArgumentParser(description='Step 4: Run training in Docker container')
    parser.add_argument('--user-id', help='Firebase user ID')
    parser.add_argument('--container', help='Name of the Docker container')
    parser.add_argument('--container-path', help='Path to data in container')
    parser.add_argument('--env-name', help='Override conda environment name')
    parser.add_argument('--state-file', help='Path to pipeline state file')
    
    args = parser.parse_args()
    
    # Check if we have a state file and load it if available
    if args.state_file and os.path.exists(args.state_file):
        with open(args.state_file, 'r') as f:
            state = json.load(f)
        
        # Use state values if arguments aren't provided
        user_id = args.user_id or state.get('user_id')
        container_name = args.container or state.get('container_name')
        container_path = args.container_path or state.get('container_path')
        base_path = os.path.dirname(os.path.dirname(args.state_file)) if args.state_file else None
    else:
        # If we don't have a state file, we need explicit arguments
        if not args.user_id or not args.container or not args.container_path:
            print_colored("Error: user-id, container, and container-path are required if no state file is provided", Colors.RED)
            sys.exit(1)
        
        user_id = args.user_id
        container_name = args.container
        container_path = args.container_path
        base_path = os.path.dirname(os.path.dirname(state.get('download_path'))) if state.get('download_path') else None
        
        state = {
            'user_id': user_id,
            'container_name': container_name,
            'container_path': container_path
        }
    
    # Create state file path if not provided
    if not args.state_file and base_path:
        state_file = os.path.join(base_path, "pipeline_state.json")
    else:
        state_file = args.state_file
    
    print_colored(f"======= Step 4: Running Training =======", Colors.BLUE)
    print_colored(f"User ID: {user_id}", Colors.YELLOW)
    print_colored(f"Container: {container_name}", Colors.YELLOW)
    print_colored(f"Container path: {container_path}", Colors.YELLOW)
    
    # Run the training
    if run_training(container_name, container_path, user_id, args.env_name):
        print_colored("Training completed successfully!", Colors.GREEN)
        
        # Update output paths based on known directory structure
        # These paths are based on the common output locations from the training script
        output_paths = {
            'vanilla_gs_dir': f"/app/output/vanilla_gs/{user_id}",
            'refined_ply_dir': f"/app/output/refined_ply/{user_id}",
            'refined_mesh_dir': f"/app/output/refined_mesh/{user_id}"
        }
        
        # Update pipeline state for next step
        state.update({
            'user_id': user_id,
            'container_name': container_name,
            'container_path': container_path,
            'output_paths': output_paths,
            'step4_completed': True
        })
        
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        print_colored(f"Pipeline state updated in {state_file}", Colors.GREEN)
        print_colored("Ready for Step 5: Upload Results", Colors.BLUE)
    else:
        print_colored("Training failed, pipeline cannot continue.", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()