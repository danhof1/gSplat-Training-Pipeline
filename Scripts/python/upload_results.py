#!/usr/bin/env python3
# upload_results.py - Step 5: Upload results to Firebase

import os
import sys
import json
import argparse
import tempfile
import subprocess
from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
from firebase_admin import firestore

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

def upload_results_to_firebase(container_name, output_paths, user_id, service_account_path='gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json', project_id='gauss-mobile'):
    """Copy result files from container and upload them to Firebase Storage and Firestore"""
    print_colored(f"Uploading results to Firebase Storage for user {user_id}...", Colors.YELLOW)

    with tempfile.TemporaryDirectory() as temp_dir:
        uploaded_files = []
        
        # Extract and process each output directory
        for dir_type, docker_path in output_paths.items():
            # Create a directory for this output type
            type_dir = os.path.join(temp_dir, dir_type)
            os.makedirs(type_dir, exist_ok=True)
            
            print_colored(f"Copying {dir_type} from Docker at {docker_path}...", Colors.YELLOW)
            
            # Copy files from container - don't fail if a path doesn't exist
            try:
                run_command(["docker", "cp", f"{container_name}:{docker_path}/.", type_dir], check=False)
            except Exception as e:
                print_colored(f"Warning: Could not copy from {docker_path}: {str(e)}", Colors.YELLOW)
                continue
                
            # Check if we got any files
            files = list(Path(type_dir).glob("**/*.*"))
            if not files:
                print_colored(f"No files found in {dir_type} directory", Colors.YELLOW)
                continue
                
            print_colored(f"Found {len(files)} files in {dir_type}", Colors.GREEN)

        # Initialize Firebase if not already initialized
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id,
                    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', f"{project_id}.firebasestorage.app")
                })


            db = firestore.client()
            bucket = storage.bucket()
        except Exception as e:
            print_colored(f"Error initializing Firebase: {str(e)}", Colors.RED)
            return False

        # Find all .ply and .obj files
        file_paths = []
        for ext in ['.ply', '.obj']:
            file_paths.extend(list(Path(temp_dir).glob(f"**/*{ext}")))
            
        if not file_paths:
            print_colored("No .ply or .obj files found to upload.", Colors.RED)
            return False

        for file_path in file_paths:
            try:
                file_name = file_path.name
                model_name = file_path.stem
                file_size = os.path.getsize(file_path)
                storage_path = f"users/{user_id}/models/{model_name}/{file_name}"

                print_colored(f"Uploading file {file_name} to Firebase Storage at {storage_path}...", Colors.YELLOW)
                blob = bucket.blob(storage_path)
                blob.upload_from_filename(str(file_path))
                blob.make_public()
                public_url = blob.public_url

                print_colored(f"Adding reference to Firestore plyFiles collection...", Colors.YELLOW)
                db.collection('plyFiles').document().set({
                    'fileName': file_name,
                    'originalName': file_name,
                    'downloadURL': public_url,
                    'storagePath': storage_path,
                    'contentType': '',
                    'size': file_size,
                    'uploadedAt': firestore.SERVER_TIMESTAMP,
                    'userId': user_id
                })

                print_colored(f"Successfully uploaded {file_name} to Firebase", Colors.GREEN)
                print_colored(f"Public URL: {public_url}", Colors.GREEN)
                
                uploaded_files.append({
                    'fileName': file_name,
                    'url': public_url,
                    'path': storage_path,
                    'type': file_path.suffix[1:]  # 'ply' or 'obj'
                })

                # If this is an OBJ file, also check for associated MTL and texture files
                if file_path.suffix.lower() == '.obj':
                    # Check for MTL file
                    mtl_file = file_path.with_suffix('.mtl')
                    if mtl_file.exists():
                        mtl_storage_path = f"users/{user_id}/models/{model_name}/{mtl_file.name}"
                        mtl_blob = bucket.blob(mtl_storage_path)
                        mtl_blob.upload_from_filename(str(mtl_file))
                        mtl_blob.make_public()
                        
                        # Look for texture files in the same directory
                        texture_dir = file_path.parent
                        for img_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                            for img_file in texture_dir.glob(f"*{img_ext}"):
                                img_storage_path = f"users/{user_id}/models/{model_name}/{img_file.name}"
                                img_blob = bucket.blob(img_storage_path)
                                img_blob.upload_from_filename(str(img_file))
                                img_blob.make_public()
                                
                                uploaded_files.append({
                                    'fileName': img_file.name,
                                    'url': img_blob.public_url,
                                    'path': img_storage_path,
                                    'type': 'texture'
                                })

            except Exception as e:
                print_colored(f"Error uploading file {file_path}: {str(e)}", Colors.RED)
                continue

        # Add a processing status document to track completed models
        try:
            db.collection('users').document(user_id).collection('modelProcessing').add({
                'status': 'completed',
                'files': uploaded_files,
                'completedAt': firestore.SERVER_TIMESTAMP,
                'processingPath': output_paths.get('vanilla_gs_dir', '')
            })
            print_colored("Added processing status document to Firestore", Colors.GREEN)
        except Exception as e:
            print_colored(f"Error adding processing status: {str(e)}", Colors.RED)

        if uploaded_files:
            print_colored(f"Successfully uploaded {len(uploaded_files)} files to Firebase", Colors.GREEN)
            return True
        else:
            print_colored("No files were uploaded", Colors.RED)
            return False

def main():
    parser = argparse.ArgumentParser(description='Step 5: Upload results to Firebase')
    parser.add_argument('--user-id', help='Firebase user ID')
    parser.add_argument('--container', help='Name of the Docker container')
    parser.add_argument('--vanilla-gs-dir', help='Path to vanilla GS output in container')
    parser.add_argument('--refined-ply-dir', help='Path to refined PLY output in container')
    parser.add_argument('--refined-mesh-dir', help='Path to refined mesh output in container')
    parser.add_argument('--service-account', default='../../Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json', 
                      help='Path to service account key JSON file')
    parser.add_argument('--project-id', default='gauss-mobile', help='Firebase project ID')
    parser.add_argument('--state-file', help='Path to pipeline state file')
    
    args = parser.parse_args()
    
    # Check if we have a state file and load it if available
    if args.state_file and os.path.exists(args.state_file):
        with open(args.state_file, 'r') as f:
            state = json.load(f)
        
        # Use state values if arguments aren't provided
        user_id = args.user_id or state.get('user_id')
        container_name = args.container or state.get('container_name')
        output_paths = state.get('output_paths', {})
        
        # Override with command-line arguments if provided
        if args.vanilla_gs_dir:
            output_paths['vanilla_gs_dir'] = args.vanilla_gs_dir
        if args.refined_ply_dir:
            output_paths['refined_ply_dir'] = args.refined_ply_dir
        if args.refined_mesh_dir:
            output_paths['refined_mesh_dir'] = args.refined_mesh_dir
            
        base_path = os.path.dirname(os.path.dirname(args.state_file)) if args.state_file else None
    else:
        # If we don't have a state file, we need explicit arguments
        if not args.user_id or not args.container:
            print_colored("Error: user-id and container are required if no state file is provided", Colors.RED)
            sys.exit(1)
        
        user_id = args.user_id
        container_name = args.container
        output_paths = {}
        
        # Set output paths from arguments or use defaults based on user ID
        if args.vanilla_gs_dir:
            output_paths['vanilla_gs_dir'] = args.vanilla_gs_dir
        else:
            output_paths['vanilla_gs_dir'] = f"/app/output/vanilla_gs/{user_id}"
            
        if args.refined_ply_dir:
            output_paths['refined_ply_dir'] = args.refined_ply_dir
        else:
            output_paths['refined_ply_dir'] = f"/app/output/refined_ply/{user_id}"
            
        if args.refined_mesh_dir:
            output_paths['refined_mesh_dir'] = args.refined_mesh_dir
        else:
            output_paths['refined_mesh_dir'] = f"/app/output/refined_mesh/{user_id}"
    
    print_colored(f"======= Step 5: Uploading Results to Firebase =======", Colors.BLUE)
    print_colored(f"User ID: {user_id}", Colors.YELLOW)
    print_colored(f"Container: {container_name}", Colors.YELLOW)
    print_colored(f"Output paths:", Colors.YELLOW)
    for path_type, path in output_paths.items():
        print_colored(f"  {path_type}: {path}", Colors.YELLOW)
    
    # Upload results to Firebase
    success = upload_results_to_firebase(
        container_name, 
        output_paths, 
        user_id, 
        args.service_account, 
        args.project_id
    )
    
    if success:
        print_colored("Results uploaded successfully!", Colors.GREEN)
        
        # Update pipeline state to complete
        if args.state_file:
            with open(args.state_file, 'r') as f:
                state = json.load(f)
                
            state.update({
                'step5_completed': True,
                'pipeline_completed': True
            })
            
            with open(args.state_file, 'w') as f:
                json.dump(state, f)
                
            print_colored(f"Pipeline state updated in {args.state_file}", Colors.GREEN)
        
        print_colored("🎉 Pipeline completed successfully! 🎉", Colors.GREEN)
    else:
        print_colored("Failed to upload results.", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()