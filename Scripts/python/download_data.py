#!/usr/bin/env python3
# download_data.py - Step 1: Download data from Firestore

import os
import sys
import json
import argparse
from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import shutil

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

def process_collection(db, user_id, collection_path, local_path):
    """Recursively process a Firestore collection and create local files/folders"""
    print_colored(f"Processing collection for user {user_id}: {collection_path}", Colors.YELLOW)
    
    # Create the local directory if it doesn't exist
    Path(local_path).mkdir(parents=True, exist_ok=True)
    
    # Get all documents in the collection under the user's path
    collection_ref = db.collection('users').document(user_id).collection(collection_path)
    docs = collection_ref.stream()
    docs_list = list(docs)
    
    if not docs_list:
        print_colored(f"No documents found in {collection_path} for user {user_id}", Colors.YELLOW)
        return
    
    # Process each document
    for doc in docs_list:
        data = doc.to_dict()
        print_colored(f"Processing document: {doc.id}", Colors.YELLOW)
        
        if data.get('type') == 'folder':
            # If it's a folder, create it and process its contents
            folder_name = data.get('name', doc.id)
            folder_path = os.path.join(local_path, folder_name)
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            
            # Process the subcollection - using proper subcollection path
            subcollection_ref = collection_ref.document(doc.id).collection('contents')
            subcollection_docs = subcollection_ref.stream()
            subcollection_docs_list = list(subcollection_docs)
            
            for subdoc in subcollection_docs_list:
                subdata = subdoc.to_dict()
                print_colored(f"Processing subdocument: {subdoc.id}", Colors.YELLOW)
                
                if subdata.get('type') == 'file':
                    # Process files directly without recursive call
                    file_name = subdata.get('name', subdoc.id)
                    file_path = os.path.join(folder_path, file_name)
                    original_path = subdata.get('path', '')
                    
                    if os.path.exists(original_path):
                        # If the original file exists, copy it
                        shutil.copy2(original_path, file_path)
                        print_colored(f"Copied file from original location: {original_path} -> {file_path}", Colors.GREEN)
                    else:
                        # Create an empty placeholder file
                        Path(file_path).touch()
                        print_colored(f"Created empty placeholder file: {file_path} (original not found at {original_path})", Colors.YELLOW)
                    
                    # Optionally create a metadata file
                    metadata = {
                        'source': 'firestore',
                        'originalPath': original_path,
                        'size': subdata.get('size', 0),
                        'userId': subdata.get('userId', user_id),
                        'createdAt': str(subdata.get('createdAt', ''))
                    }
                    
                    with open(f"{file_path}.metadata.json", 'w') as f:
                        json.dump(metadata, f, indent=2)
        
        elif data.get('type') == 'file':
            # For files in the root collection
            file_name = data.get('name', doc.id)
            file_path = os.path.join(local_path, file_name)
            original_path = data.get('path', '')
            
            if os.path.exists(original_path):
                # If the original file exists, copy it
                shutil.copy2(original_path, file_path)
                print_colored(f"Copied file from original location: {original_path} -> {file_path}", Colors.GREEN)
            else:
                # Create an empty placeholder file
                Path(file_path).touch()
                print_colored(f"Created empty placeholder file: {file_path} (original not found at {original_path})", Colors.YELLOW)
            
            # Optionally create a metadata file
            metadata = {
                'source': 'firestore',
                'originalPath': original_path,
                'size': data.get('size', 0),
                'userId': data.get('userId', user_id),
                'createdAt': str(data.get('createdAt', ''))
            }
            
            with open(f"{file_path}.metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Step 1: Download data from Firestore')
    parser.add_argument('--project-id', default='gauss-mobile', help='Firebase project ID')
    parser.add_argument('--collection', default='Gauss', help='Firestore collection name')
    parser.add_argument('--user-id', required=True, help='Firebase user ID to download data for')
    parser.add_argument('--service-account', default='gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json', 
                      help='Path to service account key JSON file')
    parser.add_argument('--output-path', default='/home/h702839428/Desktop/Full_Project/FIRE/dedicated_SENDTO', 
                      help='Local download path')
    
    args = parser.parse_args()
    
    # Validate user ID
    if not args.user_id:
        print_colored("Error: User ID is required", Colors.RED)
        sys.exit(1)
    
    # Validate service account file
    if not os.path.isfile(args.service_account):
        print_colored(f"Error: Service account file not found at {args.service_account}", Colors.RED)
        sys.exit(1)
    
    # Set up local download path - include user ID in the path
    download_path = os.path.join(args.output_path, args.user_id, 'data')
    Path(download_path).mkdir(parents=True, exist_ok=True)
    
    print_colored(f"======= Step 1: Downloading Data from Firestore =======", Colors.BLUE)
    print_colored(f"User ID: {args.user_id}", Colors.YELLOW)
    
    # Initialize Firebase Admin with service account
    try:
        cred = credentials.Certificate(args.service_account)
        firebase_admin.initialize_app(cred, {
            'projectId': args.project_id,
            'storageBucket': f"{args.project_id}.appspot.com"
        })
        db = firestore.client()
    except Exception as e:
        print_colored(f"Error initializing Firebase: {str(e)}", Colors.RED)
        sys.exit(1)
    
    # Download data from Firestore
    print_colored(f"Downloading collection '{args.collection}' for user '{args.user_id}' to '{download_path}'...", Colors.GREEN)
    try:
        process_collection(db, args.user_id, args.collection, download_path)
        print_colored("Download completed successfully!", Colors.GREEN)
        
        # Save pipeline state for next step
        state_file = os.path.join(args.output_path, args.user_id, "pipeline_state.json")
        with open(state_file, 'w') as f:
            json.dump({
                'user_id': args.user_id,
                'download_path': download_path,
                'project_id': args.project_id,
                'collection': args.collection,
                'step1_completed': True
            }, f)
        
        print_colored(f"Pipeline state saved to {state_file}", Colors.GREEN)
        
    except Exception as e:
        print_colored(f"Error downloading data: {str(e)}", Colors.RED)
        sys.exit(1)
    
    print_colored(f"Data download completed for user {args.user_id}!", Colors.GREEN)
    print_colored(f"Downloaded to: {download_path}", Colors.GREEN)
    print_colored("Ready for Step 2: Data Conversion", Colors.BLUE)

if __name__ == "__main__":
    main()