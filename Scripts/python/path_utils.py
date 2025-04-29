#!/usr/bin/env python3
# path_utils.py - Centralized path handling for the Gaussian Splatting pipeline

import os
import sys
import tempfile
import shutil
import atexit
import json
from pathlib import Path

# Global registry of temporary directories to clean up at exit
_temp_dirs = []
_user_data_dirs = {}  # Cache user directories so we reuse the same one

# Root directory for persistent pipeline data
_PIPELINE_DATA_DIR = "/tmp/gs_pipeline_data"

def get_project_root():
    """Returns the absolute path to the project root directory"""
    # Get the directory of the current script
    current_script = Path(os.path.abspath(sys.argv[0]))
    
    # Navigate up to find project root 
    # This assumes the script is being run from within the project structure
    current_dir = current_script.parent
    
    # Try to find a marker of the project root (like Scripts/python directory)
    while current_dir != current_dir.parent:  # Stop at filesystem root
        if (current_dir / "Scripts" / "python").exists() or (current_dir / "python").exists():
            return str(current_dir)
        current_dir = current_dir.parent
    
    # If we couldn't find a clear project root, use the directory of this file
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_script_dir():
    """Returns the directory containing the Python scripts"""
    project_root = get_project_root()
    if os.path.exists(os.path.join(project_root, "Scripts", "python")):
        return os.path.join(project_root, "Scripts", "python")
    return os.path.join(project_root, "python")

def get_service_account_path():
    """Returns the path to the Firebase service account JSON file"""
    # Check standard locations for the service account file
    possible_paths = [
        os.path.join(get_project_root(), "Service"),
        os.path.join(get_project_root(), "..", "Service"),
        "/home/h702839428/Desktop/Full_Project/FIRE/Service",
    ]
    
    for service_dir in possible_paths:
        if os.path.exists(service_dir):
            # Look for the firebase admin SDK JSON file
            try:
                for file in os.listdir(service_dir):
                    if file.endswith(".json") and "firebase-adminsdk" in file:
                        return os.path.join(service_dir, file)
            except (FileNotFoundError, NotADirectoryError):
                continue
    
    # Default fallback
    return "/home/h702839428/Desktop/Full_Project/FIRE/Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json"

def get_convert_script_path():
    """Returns the path to the directory containing convert.py"""
    # Check standard locations for the convert script
    possible_paths = [
        os.path.join(get_project_root(), "gaussian-splatting"),
        os.path.join(get_project_root(), "..", "Gauss_Project", "gaussian-splatting"),
        "/home/h702839428/Desktop/Full_Project/Gauss_Project/gaussian-splatting",
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "convert.py")):
            return path
    
    # Default fallback
    return "/home/h702839428/Desktop/Full_Project/Gauss_Project/gaussian-splatting"

def get_user_data_dir(user_id):
    """Returns the base directory for a specific user's data.
    Creates a persistent directory in /tmp that won't be cleaned up automatically
    until the entire pipeline is complete."""
    # Ensure the pipeline data directory exists
    os.makedirs(_PIPELINE_DATA_DIR, exist_ok=True)
    
    # Create a user-specific directory within the pipeline data directory
    user_dir = os.path.join(_PIPELINE_DATA_DIR, f"user_{user_id}")
    ensure_dir_exists(user_dir)
    
    print(f"Using persistent pipeline directory for user {user_id}: {user_dir}")
    return user_dir

def get_pipeline_cleanup_file(user_id):
    """Returns the path to a file that tracks which directories to clean up"""
    pipeline_dir = os.path.join(_PIPELINE_DATA_DIR, "cleanup")
    ensure_dir_exists(pipeline_dir)
    return os.path.join(pipeline_dir, f"cleanup_{user_id}.json")

def register_temp_for_cleanup(temp_dir, user_id):
    """Registers a temporary directory to be cleaned up at the end of the pipeline"""
    cleanup_file = get_pipeline_cleanup_file(user_id)
    
    dirs_to_cleanup = []
    if os.path.exists(cleanup_file):
        try:
            with open(cleanup_file, 'r') as f:
                dirs_to_cleanup = json.load(f)
        except json.JSONDecodeError:
            dirs_to_cleanup = []
    
    if temp_dir not in dirs_to_cleanup:
        dirs_to_cleanup.append(temp_dir)
    
    with open(cleanup_file, 'w') as f:
        json.dump(dirs_to_cleanup, f)

def cleanup_pipeline_dirs(user_id):
    """Clean up all directories registered for cleanup for this user"""
    cleanup_file = get_pipeline_cleanup_file(user_id)
    
    if not os.path.exists(cleanup_file):
        return
    
    try:
        with open(cleanup_file, 'r') as f:
            dirs_to_cleanup = json.load(f)
        
        for dir_path in dirs_to_cleanup:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                print(f"Cleaned up pipeline directory: {dir_path}")
        
        # Remove the cleanup file itself
        os.remove(cleanup_file)
    except Exception as e:
        print(f"Warning: Failed to clean up pipeline directories: {str(e)}")

def get_user_state_file(user_id):
    """Returns the path to the pipeline state file for a specific user"""
    user_dir = get_user_data_dir(user_id)
    return os.path.join(user_dir, "pipeline_state.json")

def create_temp_dir(prefix="gs_pipeline_"):
    """Creates a temporary directory that will be automatically cleaned up at exit"""
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    _temp_dirs.append(temp_dir)
    return temp_dir

def create_user_temp_dir(user_id, prefix="gs_"):
    """Creates a temporary directory for a specific user that will be cleaned up at exit"""
    temp_dir = tempfile.mkdtemp(prefix=f"{prefix}{user_id}_")
    _temp_dirs.append(temp_dir)
    
    # Also register for pipeline cleanup
    register_temp_for_cleanup(temp_dir, user_id)
    
    return temp_dir

def cleanup_temp_dirs():
    """Clean up all registered temporary directories for this specific script run"""
    for dir_path in _temp_dirs:
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                print(f"Cleaned up temporary directory: {dir_path}")
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory {dir_path}: {str(e)}")

def ensure_dir_exists(dir_path):
    """Ensures a directory exists, creating it if necessary"""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

# Register the cleanup function to run at exit
atexit.register(cleanup_temp_dirs)