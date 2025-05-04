#!/bin/bash

# run_pipeline.sh - Run the entire Gaussian Splatting pipeline
# Usage: ./run_pipeline.sh USER_ID [CONTAINER_NAME]

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_DIR="${PROJECT_ROOT}/python"

# Display colorful output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for user ID argument
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: User ID is required as the first parameter${NC}"
    echo "Usage: ./run_pipeline.sh USER_ID [CONTAINER_NAME]"
    exit 1
fi

USER_ID="$1"
echo -e "${BLUE}Starting pipeline for user ID: ${USER_ID}${NC}"

# Check if a container name was provided as the second argument
CONTAINER_NAME=""
if [ $# -ge 2 ]; then
    CONTAINER_NAME="$2"
    echo -e "${YELLOW}Using specified container: ${CONTAINER_NAME}${NC}"
else
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
        echo "Please specify one container as the second parameter:"
        echo "Usage: ./run_pipeline.sh USER_ID CONTAINER_NAME"
        exit 1
    fi

    # Get the container name from the ID
    CONTAINER_NAME=$(docker inspect --format='{{.Name}}' $CONTAINER_ID | sed 's/\///')
    echo -e "${GREEN}Found running container: $CONTAINER_NAME${NC}"
fi

# Make sure python directory exists
if [ ! -d "$PYTHON_DIR" ]; then
    echo -e "${RED}Error: Python directory not found at ${PYTHON_DIR}${NC}"
    echo -e "${YELLOW}Creating Python directory structure...${NC}"
    mkdir -p "$PYTHON_DIR"
    
    # Check if path_utils.py exists in the current directory and copy it
    if [ -f "$SCRIPT_DIR/path_utils.py" ]; then
        cp "$SCRIPT_DIR/path_utils.py" "$PYTHON_DIR/"
        echo -e "${GREEN}Copied path_utils.py to Python directory${NC}"
    else
        echo -e "${RED}Error: path_utils.py not found. Please ensure it exists.${NC}"
        exit 1
    fi
fi

# Set up data directory for this user
USER_DATA_DIR="${PROJECT_ROOT}/data/${USER_ID}"
STATE_FILE="${USER_DATA_DIR}/pipeline_state.json"
mkdir -p "${USER_DATA_DIR}"

# First check if path_utils.py exists
if [ ! -f "$PYTHON_DIR/path_utils.py" ]; then
    echo -e "${RED}Error: path_utils.py not found at ${PYTHON_DIR}/path_utils.py${NC}"
    echo -e "${YELLOW}Please ensure path_utils.py is in the Python directory${NC}"
    exit 1
fi

# Step 1: Download data from Firestore
echo -e "\n${BLUE}======= Step 1: Downloading Data from Firestore =======${NC}"
python3 "${PYTHON_DIR}/download_data.py" --user-id "${USER_ID}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 1 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 2: Convert data
echo -e "\n${BLUE}======= Step 2: Converting Data =======${NC}"
python3 "${PYTHON_DIR}/convert_data.py" --user-id "${USER_ID}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 2 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 3: Copy to Docker
echo -e "\n${BLUE}======= Step 3: Copying Data to Docker =======${NC}"
python3 "${PYTHON_DIR}/copy_to_docker.py" --user-id "${USER_ID}" --container "${CONTAINER_NAME}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 3 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 4: Run training
echo -e "\n${BLUE}======= Step 4: Running Training =======${NC}"
python3 "${PYTHON_DIR}/run_training.py" --user-id "${USER_ID}" --container "${CONTAINER_NAME}" --state-file "${STATE_FILE}"
if [ $? -ne 0 ]; then
    echo -e "${RED}Step 4 failed! Pipeline aborted.${NC}"
    exit 1
fi

# Step 5: Upload results
echo -e "\n${BLUE}======= Step 5: Uploading Results to Firebase =======${NC}"
python3 "${PYTHON_DIR}/upload_results.py" --user-id "${USER_ID}" --container "${CONTAINER_NAME}" --state-file "${STATE_FILE}"
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

echo -e "${YELLOW}Note: Temporary files will be cleaned up automatically.${NC}"

exit 0