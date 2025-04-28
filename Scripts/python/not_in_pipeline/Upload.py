import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import argparse
import sys

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

# Initialize Firebase Admin SDK
def initialize_firebase(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print_colored(f"Error initializing Firebase: {str(e)}", Colors.RED)
        sys.exit(1)

def upload_folder_to_firestore(folder_path, collection_path, user_id, parent_doc_ref=None):
    """
    Upload a folder structure to Firestore with user separation
    
    Args:
        folder_path: Path to the folder to upload
        collection_path: Base collection path in Firestore
        user_id: Firebase user ID to separate data
        parent_doc_ref: Parent document reference for recursive calls
    """
    # Get the folder name from the path
    folder_name = "input"  # Changed from os.path.basename(folder_path) to "input"
    
    # Create a document for the current folder itself
    folder_id = folder_name.replace('.', '_').replace('#', '_').replace('$', '_').replace('/', '_').replace('[', '_').replace(']', '_')
    
    if parent_doc_ref is None:
        # This is the root folder - stored under user's collection
        folder_doc_ref = db.collection('users').document(user_id).collection(collection_path).document(folder_id)
    else:
        # This is a subfolder
        folder_doc_ref = parent_doc_ref.collection('contents').document(folder_id)
    
    # Set folder metadata
    folder_doc_ref.set({
        'name': folder_name,
        'type': 'folder',
        'path': folder_path,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'userId': user_id  # Add user ID to metadata
    })
    
    print_colored(f"Created folder document for '{folder_name}' under user {user_id}", Colors.GREEN)
    
    # Process folder contents
    files = os.listdir(folder_path)
    for file in files:
        file_path = os.path.join(folder_path, file)
        if os.path.isdir(file_path):
            # If it's a directory, recursively process it
            upload_folder_to_firestore(file_path, collection_path, user_id, folder_doc_ref)
        else:
            # If it's a file, create a document for it
            file_id = file.replace('.', '_').replace('#', '_').replace('$', '_').replace('/', '_').replace('[', '_').replace(']', '_')
            folder_doc_ref.collection('contents').document(file_id).set({
                'name': file,
                'type': 'file',
                'path': file_path,
                'size': os.path.getsize(file_path),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'userId': user_id  # Add user ID to metadata
            })
            print_colored(f"Uploaded file metadata for '{file}'", Colors.BLUE)

def main():
    parser = argparse.ArgumentParser(description='Upload folder structure to Firestore with user separation')
    parser.add_argument('--folder-path', default='/home/h702839428/Desktop/Full_Project/Datasets/UnConverted/Water',
                      help='Path to the folder to upload')
    parser.add_argument('--collection', default='Gauss',
                      help='Firestore collection name')
    parser.add_argument('--user-id', required=True,
                      help='Firebase user ID to separate data')
    parser.add_argument('--service-account', default='gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json',
                      help='Path to service account key JSON file')
    
    args = parser.parse_args()
    
    print_colored("======= Folder Structure Upload with User Separation =======", Colors.BLUE)
    print_colored(f"User ID: {args.user_id}", Colors.YELLOW)
    print_colored(f"Source folder: {args.folder_path}", Colors.YELLOW)
    print_colored(f"Destination collection: {args.collection}", Colors.YELLOW)
    
    # Validate folder path
    if not os.path.isdir(args.folder_path):
        print_colored(f"Error: Folder not found at {args.folder_path}", Colors.RED)
        sys.exit(1)
    
    global db
    # Initialize Firebase
    db = initialize_firebase(args.service_account)
    
    # Create root collection and upload the folder structure with user ID
    upload_folder_to_firestore(args.folder_path, args.collection, args.user_id)
    
    print_colored('Folder structure uploaded successfully!', Colors.GREEN)
    print_colored(f'All data is separated under user ID: {args.user_id}', Colors.GREEN)

# Test case
if __name__ == "__main__":
    # For manual testing, uncomment this block:
    """
    import sys
    sys.argv = [
        'upload.py',
        '--folder-path', '/home/h702839428/Desktop/Full_Project/Datasets/UnConverted/Water',
        '--collection', 'Gauss',
        '--user-id', 'EQrX57dmjWP6pXc63PaYbtklZY92',
        '--service-account', 'gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json'
    ]
    """
    main()