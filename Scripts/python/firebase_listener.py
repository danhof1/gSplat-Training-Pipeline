#!/usr/bin/env python3
# Monitors Firestore for new uploads and triggers the pipeline

import time
import subprocess
import threading
import firebase_admin
from firebase_admin import credentials, firestore

from pathlib import Path
from datetime import datetime
import sys

# CONFIG
SERVICE_ACCOUNT_PATH = "/home/h702839428/Desktop/Full_Project/FIRE/Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json"
POLL_INTERVAL = 20  # seconds
PROCESSED_DOCS_PATH = "/tmp/processed_doc_ids.txt"
COLLECTION_PATH = "Summary"
RUN_PIPELINE_SCRIPT = "/home/h702839428/Desktop/Full_Project/FIRE/Scripts/python/run_pipeline.sh"

# Initialize Firebase (only once)
try:
    print("⚙️  Initializing Firebase Admin SDK...")
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully.")
    else:
        print("ℹ️ Firebase already initialized. Skipping re-init.")
    db = firestore.client()
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    sys.exit(1)

# Load processed document IDs
def load_processed_doc_ids():
    print("📂 Loading processed document list...")
    if not Path(PROCESSED_DOCS_PATH).exists():
        print("ℹ️ No processed document file found. Starting fresh.")
        return set()
    with open(PROCESSED_DOCS_PATH, "r") as f:
        processed = set(line.strip() for line in f.readlines())
    print(f"✅ Loaded {len(processed)} processed doc IDs.")
    return processed

# Save processed document ID
def save_processed_doc_id(doc_id):
    with open(PROCESSED_DOCS_PATH, "a") as f:
        f.write(doc_id + "\n")

# Run pipeline and stream output
def run_pipeline_for_user(uid):
    print(f"\n🚀 Running pipeline for UID: {uid}")
    process = subprocess.Popen(
        ["bash", RUN_PIPELINE_SCRIPT, uid],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode == 0:
        print(f"✅ Pipeline completed for UID: {uid}")
    else:
        print(f"❌ Pipeline failed for UID: {uid}")

# Poll Firestore for new Summary docs
def monitor_firestore():
    seen_docs = load_processed_doc_ids()
    print(f"[{datetime.now()}] 🔎 Monitoring Firebase collection: {COLLECTION_PATH}")
    while True:
        try:
            print(f"[{datetime.now()}] 📡 Polling Firestore for new uploads...")
            docs = db.collection(COLLECTION_PATH).stream()
            found_any = False
            for doc in docs:
                found_any = True
                doc_id = doc.id
                if doc_id in seen_docs:
                    print(f"🔁 Already processed document: {doc_id}")
                    continue

                data = doc.to_dict()
                print(f"📄 Document: {doc_id} -> {data}")
                uid = data.get("userId")
                if not uid:
                    print("⚠️ Skipping document (no userId found).")
                    continue

                print(f"🆕 New upload detected! UID: {uid}, doc_id: {doc_id}")
                seen_docs.add(doc_id)
                save_processed_doc_id(doc_id)

                # Trigger pipeline
                threading.Thread(target=run_pipeline_for_user, args=(uid,), daemon=True).start()

            if not found_any:
                print("ℹ️ No documents found in collection.")

        except Exception as e:
            print(f"❌ Error polling Firestore: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    monitor_firestore()
