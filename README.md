# gSplat-Training-Pipeline
## Gaussian Splatting Processing Pipeline

<p align="center">
  <img src="https://img.shields.io/badge/AWARD-Second%20Place%20Winner%20of%20Hofstra'sf%20Spring%202025%20CSE%20Senior%20Capstone%20Competition-silver" alt="Award Badge">
</p>

### 🏆 Recognition

This project was awarded **Second Place** in the **Hofstra's Spring 2025 Computer Science & Engineering Senior Capstone Competition**. We're honored to have our work recognized for its innovation in applying Gaussian Splatting technology to create an efficient 3D reconstruction pipeline.

### Overview

This project provides an automated pipeline for processing 3D model data using Gaussian Splatting technology with SuGaR (Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction and High-Quality Mesh Extraction). The pipeline handles downloading data from Firebase, converting it to the appropriate format, processing it using a Docker container with the Gaussian Splatting algorithm, and uploading the results back to Firebase.
## Gaussian Splatting Processing Pipeline

### Overview

This project provides an automated pipeline for processing 3D model data using Gaussian Splatting technology with SuGaR (Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction and High-Quality Mesh Extraction). The pipeline handles downloading data from Firebase, converting it to the appropriate format, processing it using a Docker container with the Gaussian Splatting algorithm, and uploading the results back to Firebase.

The pipeline supports a mobile application built with Flutter that allows users to upload images, which are then processed through the pipeline to generate 3D models.

### Pipeline Steps

The pipeline consists of the following sequential steps:

1. **Download Data**: Fetches user data from Firebase Firestore and Storage
2. **Convert Data**: Transforms the downloaded data into a format suitable for Gaussian Splatting using the `convert.py` script
3. **Copy to Docker**: Transfers the converted data to a running Docker container
4. **Run Training**: Executes the SuGaR algorithm on the data
5. **Upload Results**: Sends the generated 3D models (.ply and .obj files) back to Firebase for user access

### Requirements

- Python 3.x
- Docker
- NVIDIA GPU with compatible drivers
- NVIDIA Container Toolkit (nvidia-docker2)
- Firebase Admin SDK
- Service account credentials for Firebase
- Conda environment (for SuGaR pipeline)

### Architecture

The pipeline uses a stateful design with JSON state files to track progress between steps:
- **Persistent Pipeline Directory**: `/tmp/gs_pipeline_data` stores user-specific pipeline data
- **State Management**: Each user has a `pipeline_state.json` file tracking pipeline progress
- **Automatic Cleanup**: Temporary directories are automatically cleaned up after pipeline completion

### Docker Environment Setup

#### Setting Up SuGaR and Required Files

1. Clone the SuGaR repository and navigate to the project directory:
   ```bash
   git clone https://github.com/Anttwo/SuGaR.git
   cd SuGaR
   ```

2. Place the provided Dockerfile and environment.yml files into the cloned SuGaR directory:
   ```bash
   # Copy the provided Dockerfile and environment.yml to the SuGaR directory
   cp /path/to/provided/Dockerfile /path/to/SuGaR/
   cp /path/to/provided/environment.yml /path/to/SuGaR/
   ```

3. Build the Docker image using the provided Dockerfile:
   ```bash
   sudo docker build -t sugar .
   ```
   *This process may take some time as it installs all the necessary dependencies and compiles the CUDA extensions.*

#### Running the Docker Container

To run the Docker container with GPU support and X11 forwarding:

```bash
sudo docker run -it --gpus all --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /local/path/to/dataset:/app/data \
  sugar
```

Replace `/local/path/to/dataset` with the actual path to your dataset on the host machine. This will be mounted to `/app/data` inside the container.

### Configuration

#### Environment Variables
You can set these environment variables to override default paths:
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/service-account.json"
export FIREBASE_BUCKET_NAME="your-bucket-name"
```

#### Firebase Configuration

The service account key file should be placed at standard locations checked by `path_utils.py`:
- `/path/to/project/FIRE/Service/`
- `{PROJECT_ROOT}/Service/`
- Auto-detected based on script location

The project uses:
- **Firebase Storage**: For user data and results (`{PROJECT_ID}.firebasestorage.app`)
- **Firestore Collections**:
  - `users/{userId}/Gauss/input/contents/` - Uploaded images
  - `plyFiles` - References to generated 3D models
  - `Summary` - Processing status tracking

#### Default Paths

The Gaussian Splatting conversion script is expected at:
- `{PROJECT_ROOT}/gaussian-splatting/`
- Auto-detected relative to project structure

### Usage

#### Quick Start: Run Complete Pipeline

To run the entire pipeline for a specific user:
```bash
bash run_pipeline.sh USER_ID [CONTAINER_NAME]
```

The container name is optional. If not specified, the script will:
- Auto-detect running Docker containers
- Prompt for selection if multiple containers are running

#### Firebase Listener (Automatic Processing)

Start the Firebase listener to automatically process new uploads:
```bash
python firebase_listener.py
```

Configuration:
- SERVICE_ACCOUNT_PATH: Path to Firebase service account JSON
- POLL_INTERVAL: Polling interval in seconds (default: 20)
- PROCESSED_DOCS_PATH: File to track processed documents (default: `/tmp/processed_doc_ids.txt`)
- COLLECTION_PATH: Firestore collection to monitor (default: "Summary")
- RUN_PIPELINE_SCRIPT: Path to pipeline script

This script:
- Monitors the `Summary` collection for new entries
- Triggers the pipeline when new data is detected
- Tracks processed documents to avoid duplicates

#### Running Individual Steps

Each step can be run independently:

##### Step 1: Download Data
```bash
python download_data.py --user-id USER_ID \
  [--output-dir OUTPUT_DIR] \
  [--service-account SERVICE_ACCOUNT_PATH] \
  [--bucket-name BUCKET_NAME]
```

This step also prunes Firebase data after download.

##### Step 2: Convert Data
```bash
python convert_data.py --user-id USER_ID \
  [--input-path INPUT_PATH] \
  [--convert-script-path CONVERT_SCRIPT_DIR] \
  [--state-file STATE_FILE]
```

##### Step 3: Copy to Docker
```bash
python copy_to_docker.py --user-id USER_ID \
  [--input-path INPUT_PATH] \
  [--container CONTAINER_NAME] \
  [--container-path CONTAINER_PATH] \
  [--state-file STATE_FILE]
```

This step creates user-specific directories in the container to prevent conflicts.

##### Step 4: Run Training
```bash
python run_training.py --user-id USER_ID \
  [--container CONTAINER_NAME] \
  [--container-path CONTAINER_PATH] \
  [--env-name CONDA_ENV] \
  [--state-file STATE_FILE]
```

The training runs with these parameters:
```bash
python train_full_pipeline.py -s {container_path} \
  -r dn_consistency \
  --high_poly True \
  --export_obj True
```

##### Step 5: Upload Results
```bash
python upload_results.py --user-id USER_ID \
  [--container CONTAINER_NAME] \
  [--service-account SERVICE_ACCOUNT_PATH] \
  [--state-file STATE_FILE] \
  [--project-id PROJECT_ID] \
  [--skip-storage]
```

### Mobile Application Integration

The Flutter mobile app (`importpic_page.dart`) provides:
- Image selection using device gallery
- Upload to Firebase Storage path: `users/{userId}/Gauss/input/`
- Automatic summary document creation to trigger pipeline processing

### Output Structure

The pipeline generates 3D models in the following locations:
- **Vanilla GS Directory**: `/app/output/vanilla_gs/{userId}`
- **Refined PLY Directory**: `/app/output/refined_ply/{userId}`
- **Refined Mesh Directory**: `/app/output/refined_mesh/{userId}`

Output formats:
- `.ply` files (raw point cloud data)
- `.obj` files (3D mesh with textures)
- `.mtl` files (material definitions)
- Texture images (.png, .jpg, .jpeg, .bmp)

### Error Handling & Troubleshooting

#### NVIDIA GPU Issues
```bash
# Check NVIDIA drivers
nvidia-smi

# Check NVIDIA Container Toolkit
dpkg -l | grep nvidia-container-toolkit

# Verify Docker GPU access
sudo docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi
```

#### X11 Forwarding Issues
```bash
# For local development
xhost +local:docker

# For headless servers (uses Xvfb)
/app/run_with_xvfb.sh echo "Display test"
```

#### Pipeline State Issues
- State files are stored at: `{PIPELINE_DATA_DIR}/user_{userId}/pipeline_state.json`
  - Default: `/tmp/gs_pipeline_data/user_{userId}/pipeline_state.json`
- Automatic cleanup on completion: Delete user directory to force fresh start
- Manual cleanup: Use `cleanup_pipeline_dirs(user_id)` function

### Advanced Configuration

#### Path Utilities
The `path_utils.py` module handles:
- Automatic path detection based on project structure
- User-specific directory management
- Temporary directory cleanup
- State file tracking
- Automatic detection of:
  - Project root directory
  - Service account path
  - Conversion script path

#### State Management
The pipeline state includes:
```json
{
  "user_id": "...",
  "download_complete": true,
  "download_path": "...",
  "convert_script_path": "...",
  "container_name": "...",
  "container_path": "...",
  "output_paths": {...},
  "step1_completed": true,
  "step2_completed": true,
  "step3_completed": true,
  "step4_completed": true,
  "step5_completed": true,
  "pipeline_completed": true
}
```

### Best Practices

1. **For Production**: Use the Firebase listener for automatic processing
2. **For Development**: Run individual steps manually for debugging
3. **Resource Management**: The pipeline automatically manages temporary files
4. **Error Recovery**: Use state files to resume from failed steps

### Contributing

To extend the pipeline:
1. Follow the existing modular structure
2. Update state management in `path_utils.py`
3. Maintain colored terminal output for clarity
4. Add appropriate error handling

### Acknowledgments

This pipeline uses:
- SuGaR (Surface-Aligned Gaussian Splatting) for 3D reconstruction
- Firebase for cloud storage and state management
- Docker for containerized processing
