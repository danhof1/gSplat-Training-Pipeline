import firebase_admin
from firebase_admin import firestore, credentials, storage
import os
import tempfile
import argparse
import json
import sys
import shutil


def download_directory_from_firebase(service_account_path, user_id, local_base_dir=None, 
                                     bucket_name="gauss-mobile.firebasestorage.app"):
    """
    Downloads all files from a user's Firebase Storage directory recursively
    
    Args:
        service_account_path (str): Path to the service account JSON file
        user_id (str): User ID to download data for
        local_base_dir (str, optional): Local base directory where files will be saved.
                                       If None, creates a temporary directory
        bucket_name (str): Firebase Storage bucket name
    
    Returns:
        str: Path to the local directory containing downloaded files
        int: Number of files downloaded
    """
    try:
        # Initialize Firebase Admin SDK with service account if not already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        
        # Set up Firebase directory path for this user
        firebase_directory = f"users/{user_id}/Gauss/input/"
        print(f"Firebase directory: {firebase_directory}")
        
        # Create a directory if no local directory specified
        if local_base_dir is None:
            # Create temporary parent directory
            temp_parent_dir = tempfile.mkdtemp(prefix=f"firebase_{user_id}_")
            # Create structured input directory within the temp directory
            local_base_dir = os.path.join(temp_parent_dir, "input")
            os.makedirs(local_base_dir, exist_ok=True)
            print(f"Created temporary directory: {temp_parent_dir}")
            print(f"Input files will be in: {local_base_dir}")
        else:
            # Ensure the local directory exists and has proper structure
            input_dir = os.path.join(local_base_dir, "input")
            os.makedirs(input_dir, exist_ok=True)
            local_base_dir = input_dir
            print(f"Using specified directory structure: {local_base_dir}")
        
        # Get the specific bucket
        bucket = storage.bucket(name=bucket_name)
        
        # List all blobs with the specified prefix
        blobs = list(bucket.list_blobs(prefix=firebase_directory))
        
        if not blobs or (len(blobs) == 1 and blobs[0].name == firebase_directory):
            print(f"No files found for user {user_id} in directory {firebase_directory}")
            return local_base_dir, 0
            
        # Track number of files downloaded
        download_count = 0
        
        # Download each file
        for blob in blobs:
            # Skip if this is a directory marker (ends with '/')
            if blob.name.endswith('/'):
                continue
                
            # Calculate relative path from firebase_directory
            if blob.name.startswith(firebase_directory):
                relative_path = blob.name[len(firebase_directory):]
                if relative_path.startswith('/'):
                    relative_path = relative_path[1:]
            else:
                relative_path = blob.name
                
            # Construct the local file path (directly in input dir)
            local_file_path = os.path.join(local_base_dir, relative_path)
            
            # Create local subdirectories if needed
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Download the file
            blob.download_to_filename(local_file_path)
            download_count += 1
            
            # Print progress every 10 files
            if download_count % 10 == 0:
                print(f"Downloaded {download_count} files so far...")
        
        # Return the parent temp directory (not just the input subdir)
        parent_dir = os.path.dirname(local_base_dir)
        print(f"Successfully downloaded {download_count} files for user {user_id} to {local_base_dir}")
        print(f"Parent directory structure: {parent_dir}")
        
        return parent_dir, download_count
        
    except Exception as e:
        print(f"Error downloading directory: {e}")
        return None, 0

def update_pipeline_state(user_data_dir, state_info):
    """Update the pipeline state file with download information"""
    state_file = os.path.join(user_data_dir, "pipeline_state.json")
    
    # Load existing state if it exists
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
        except:
            state_data = {}
    else:
        state_data = {}
    
    # Update with new information
    state_data.update(state_info)
    
    # Write back to file
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    print(f"Updated pipeline state at {state_file}")

def prune_firebase_data(user_id, service_account_path, bucket_name="gauss-mobile.firebasestorage.app"):
    print("🧹 Pruning Firebase Storage and Firestore...")
    try:
        # Initialize Firebase Admin SDK if needed
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)

        # Prune Firebase Storage
        bucket = storage.bucket(name=bucket_name)
        firebase_directory = f"users/{user_id}/Gauss/input/"
        blobs = list(bucket.list_blobs(prefix=firebase_directory))
        for blob in blobs:
            print(f"🗑️ Deleting storage file: {blob.name}")
            blob.delete()

        # Prune Firestore contents under /users/<userId>/Gauss/input/contents/*
        firestore_client = firestore.client()
        contents_ref = firestore_client.collection("users").document(user_id).collection("Gauss").document("input").collection("contents")
        contents_docs = contents_ref.stream()
        for doc in contents_docs:
            print(f"🗑️ Deleting Firestore doc: contents/{doc.id}")
            doc.reference.delete()

        # Prune Firestore Summary document(s) for this UID
        summary_docs = firestore_client.collection("Summary").where("userId", "==", user_id).stream()
        for doc in summary_docs:
            print(f"🗑️ Deleting Summary doc: {doc.id}")
            doc.reference.delete()

        print("✅ Pruning complete.")
    except Exception as e:
        print(f"❌ Error during pruning: {e}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Download user data from Firebase Storage')
    parser.add_argument('--user-id', required=True, help='User ID to download data for')
    parser.add_argument('--output-dir', help='Directory to store downloaded files')
    parser.add_argument('--service-account', 
                       default=os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH',
                                            '/home/h702839428/Desktop/Full_Project/FIRE/Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json'),
                       help='Path to Firebase service account JSON file')
    parser.add_argument('--bucket-name', 
                       default=os.environ.get('FIREBASE_BUCKET_NAME', 'gauss-mobile.firebasestorage.app'),
                       help='Firebase Storage bucket name')
    
    args = parser.parse_args()
    
    # Determine project root from script location (assuming this is in python dir)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Set up data directory for this user if output dir not specified
    if not args.output_dir:
        user_data_dir = os.path.join(project_root, "data", args.user_id)
        os.makedirs(user_data_dir, exist_ok=True)
        
        # We'll create the input structure when downloading
        output_dir = user_data_dir
    else:
        output_dir = args.output_dir
        user_data_dir = os.path.dirname(output_dir)
    
    # Download the files
    download_dir, file_count = download_directory_from_firebase(
        args.service_account,
        args.user_id,
        output_dir,
        args.bucket_name
    )
    
    if download_dir and file_count > 0:
        # Update the pipeline state file
        state_info = {
            "user_id": args.user_id,
            "download_complete": True,
            "download_path": download_dir,
            "input_path": os.path.join(download_dir, "input"),
            "files_downloaded": file_count
        }
        update_pipeline_state(user_data_dir, state_info)
        print(f"All files downloaded to: {os.path.join(download_dir, 'input')}")

        prune_firebase_data(args.user_id, args.service_account, args.bucket_name)

        return 0
    else:
        print(f"Failed to download files for user {args.user_id}")
        # Update the pipeline state file with error
        state_info = {
            "user_id": args.user_id,
            "download_complete": False,
            "download_error": "No files found or download failed"
        }
        update_pipeline_state(user_data_dir, state_info)
        return 1

if __name__ == "__main__":
    sys.exit(main())