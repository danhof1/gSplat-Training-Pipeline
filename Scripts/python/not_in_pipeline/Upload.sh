#!/bin/bash

# upload.sh - Helper script for running Upload.py with user credentials
# Usage: ./upload.sh [USER_ID]

# Set default values
DEFAULT_USER_ID="EQrX57dmjWP6pXc63PaYbtklZY92"
DEFAULT_FOLDER_PATH="/home/h702839428/Desktop/Full_Project/Datasets/UnConverted/Water"
DEFAULT_COLLECTION="Gauss"
DEFAULT_SERVICE_ACCOUNT="gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json"

# Display colorful output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo -e "${BLUE}Gaussian Splatting Upload Script${NC}"
    echo "This script helps run Upload.py with the correct parameters."
    echo 
    echo "Usage:"
    echo "  ./upload.sh [options]"
    echo
    echo "Options:"
    echo "  -u, --user-id USER_ID       Firebase user ID (default: $DEFAULT_USER_ID)"
    echo "  -f, --folder-path PATH      Source folder path (default: $DEFAULT_FOLDER_PATH)"
    echo "  -c, --collection NAME       Firestore collection name (default: $DEFAULT_COLLECTION)"
    echo "  -s, --service-account PATH  Path to service account key file"
    echo "  -h, --help                  Show this help message"
    echo
    echo "Examples:"
    echo "  ./upload.sh -u EQrX57dmjWP6pXc63PaYbtklZY92"
    echo "  ./upload.sh --folder-path /path/to/images --user-id user123"
    echo
}

# Parse command line arguments
USER_ID=$DEFAULT_USER_ID
FOLDER_PATH=$DEFAULT_FOLDER_PATH
COLLECTION=$DEFAULT_COLLECTION
SERVICE_ACCOUNT=$DEFAULT_SERVICE_ACCOUNT

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user-id)
            USER_ID="$2"
            shift 2
            ;;
        -f|--folder-path)
            FOLDER_PATH="$2"
            shift 2
            ;;
        -c|--collection)
            COLLECTION="$2"
            shift 2
            ;;
        -s|--service-account)
            SERVICE_ACCOUNT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            # If a single parameter is provided without a flag, assume it's the USER_ID
            if [[ $1 != -* && -z "$2" ]]; then
                USER_ID="$1"
                shift
            else
                echo -e "${RED}Error: Unknown option $1${NC}"
                show_help
                exit 1
            fi
            ;;
    esac
done

# Validate inputs
if [ -z "$USER_ID" ]; then
    echo -e "${RED}Error: User ID is required${NC}"
    show_help
    exit 1
fi

if [ ! -d "$FOLDER_PATH" ]; then
    echo -e "${RED}Error: Folder path '$FOLDER_PATH' does not exist${NC}"
    exit 1
fi

if [ ! -f "$SERVICE_ACCOUNT" ]; then
    echo -e "${YELLOW}Warning: Service account file '$SERVICE_ACCOUNT' not found${NC}"
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Display confirmation
echo -e "${BLUE}====== Gaussian Splatting Upload ======${NC}"
echo -e "${YELLOW}User ID:${NC} $USER_ID"
echo -e "${YELLOW}Folder Path:${NC} $FOLDER_PATH"
echo -e "${YELLOW}Collection:${NC} $COLLECTION"
echo -e "${YELLOW}Service Account:${NC} $SERVICE_ACCOUNT"
echo

# Confirm before proceeding
read -p "Proceed with upload? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Upload cancelled${NC}"
    exit 0
fi

# Run the Python script with the parameters
echo -e "${GREEN}Starting upload...${NC}"
python3 Upload.py \
    --user-id "$USER_ID" \
    --folder-path "$FOLDER_PATH" \
    --collection "$COLLECTION" \
    --service-account "$SERVICE_ACCOUNT"

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Upload completed successfully!${NC}"
else
    echo -e "${RED}Upload failed with errors. Check the output above.${NC}"
    exit 1
fi