#!/bin/bash

# run_pipeline.sh - Run the entire Gaussian Splatting pipeline
# Usage: ./run_pipeline.sh USER_ID

# Set paths for Python scripts folder
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_DIR="${PARENT_DIR}/python"

# Display colorful output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for user ID argument
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: User ID is required as the first parameter${NC}"
    echo "Usage: ./run_pipeline.sh USER_ID"
    exit 1
fi

USER_ID="$1"
echo -e "${BLUE}Starting pipeline for user ID: ${USER_ID}${NC}"

# Set default paths
BASE_PATH="/home/h702839428/Desktop/Full_Project/FIRE/dedicated_SENDTO"
STATE_DIR="${BASE_PATH}/${USER_ID}"
STATE_FILE="${STATE_DIR}/pipeline_state.json"
# Make sure to use the full path to the service account file
SERVICE_ACCOUNT="/home/h702839428/Desktop/Full_Project/FIRE/Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json"
CONVERT_SCRIPT_PATH="/home/h702839428/Desktop/Full_Project/Gauss_Project/gaussian-splatting"

# Create directories
mkdir -p "${STATE_DIR}"

# Check if the service account file exists
if [ ! -f "$SERVICE_ACCOUNT" ]; then
    echo -e "${RED}Error: Service account file not found at ${SERVICE_ACCOUNT}${NC}"
    echo -e "${YELLOW}Please provide the correct path to the service account file${NC}"
    exit 1
fi

# Check if a Docker container is running
CONTAINER_ID=$(docker ps -q)
if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}Error: No Docker containers running${NC}"
    exit 1
fi

# If multiple containers are running, list them and exit
if [ $(echo "$CONTAINER_ID" | wc -l) -gt 1 ]; then
    echo -e "${RED}Multiple containers are running:${NC}"
    docker ps --format "{{.ID}}\t{{.Names}}\t{{.Image}}"
    echo "This script requires exactly one container to be running."
    exit 1
fi

# Get the container name from the ID
CONTAINER_NAME=$(docker inspect --format='{{.Name}}' $CONTAINER_ID | sed 's/\///')
echo -e "${GREEN}Found running container: $CONTAINER_NAME${NC}"

# Step 1: Download data from Firestore
echo -e "\n${BLUE}======= Step 1: Downloading Data from Firestore =======${NC}"
python3 "${PYTHON_DIR}/download_data.py" --user-id "${USER_ID}" --output-path "${BASE_PATH}" --service-account "${SERVICE_ACCOUNT}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 1 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Create/update pipeline state after download
cat > "$STATE_FILE" << EOF
{
    "user_id": "${USER_ID}",
    "download_path": "${STATE_DIR}/data",
    "base_path": "${STATE_DIR}"
}
EOF

# Step 2: Convert data
echo -e "\n${BLUE}======= Step 2: Converting Data =======${NC}"
python3 "${PYTHON_DIR}/convert_data.py" --user-id "${USER_ID}" --input-path "${STATE_DIR}/data" --convert-script-path "${CONVERT_SCRIPT_PATH}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 2 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 3: Copy to Docker
echo -e "\n${BLUE}======= Step 3: Copying Data to Docker =======${NC}"
python3 "${PYTHON_DIR}/copy_to_docker.py" --container "${CONTAINER_NAME}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 3 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 4: Run training
echo -e "\n${BLUE}======= Step 4: Running Training =======${NC}"
python3 "${PYTHON_DIR}/run_training.py" --container "${CONTAINER_NAME}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 4 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 5: Upload results
echo -e "\n${BLUE}======= Step 5: Uploading Results to Firebase =======${NC}"
python3 "${PYTHON_DIR}/upload_results.py" --container "${CONTAINER_NAME}" --service-account "${SERVICE_ACCOUNT}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 5 failed! Pipeline aborted.${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 Complete pipeline executed successfully! 🎉${NC}"
echo -e "${GREEN}User: ${USER_ID}${NC}"
echo -e "${GREEN}Pipeline state file: ${STATE_FILE}${NC}"

# Display uploaded files if available
if [ -f "${STATE_FILE}" ]; then
    UPLOADED_COUNT=$(grep -o '"fileName"' "${STATE_FILE}" | wc -l)
    if [ $UPLOADED_COUNT -gt 0 ]; then
        echo -e "${GREEN}Processed $UPLOADED_COUNT files through the pipeline${NC}"
    fi
fi

exit 0