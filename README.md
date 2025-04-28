# gSplat-Training-Pipeline

# Gaussian Splatting Processing Pipeline

## Overview

This project provides an automated pipeline for processing 3D model data using Gaussian Splatting technology. The pipeline handles downloading data from Firebase, converting it to the appropriate format, processing it using a Docker container with the Gaussian Splatting algorithm, and uploading the results back to Firebase.

## Pipeline Steps

The pipeline consists of the following sequential steps:

1. **Download Data**: Fetches user data from Firebase Firestore
2. **Convert Data**: Transforms the downloaded data into a format suitable for Gaussian Splatting
3. **Copy to Docker**: Transfers the converted data to a running Docker container
4. **Run Training**: Executes the Gaussian Splatting algorithm on the data
5. **Upload Results**: Sends the generated 3D models back to Firebase for user access

## Requirements

- Python 3.x
- Docker
- NVIDIA GPU with compatible drivers
- NVIDIA Container Toolkit (nvidia-docker2)
- Firebase Admin SDK
- Service account credentials for Firebase

## Docker Environment Setup

### Building the Docker Image

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/Anttwo/SuGaR.git
   cd SuGaR
   ```

2. Build the Docker image using the provided Dockerfile:
   ```bash
   sudo docker build -t sugar .
   ```
   This process may take some time as it installs all the necessary dependencies and compiles the CUDA extensions.

### Running the Docker Container

To run the Docker container with GPU support and X11 forwarding:

```bash
sudo docker run -it --gpus all --env="DISPLAY" --env="QT_X11_NO_MITSHM=1" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /local/path/to/dataset:/app/data \
  sugar
```

Replace `/local/path/to/dataset` with the actual path to your dataset on the host machine. This will be mounted to `/app/data` inside the container.

### Running the Training

Once inside the container, execute the training using the provided script:

```bash
/app/run_with_xvfb.sh python train_full_pipeline.py \
  -s /app/path/to/dataset/on/docker \
  -r dn_consistency \
  --refinement_time short \
  --export_obj True
```

Parameters:
- `-s`: Path to the dataset inside the Docker container
- `-r`: Refinement method (here using "dn_consistency")
- `--refinement_time`: Duration of refinement (options: short, medium, long)
- `--export_obj`: Whether to export the model as OBJ files

## Configuration

The service account key file should be placed at:
```
/home/h702839428/Desktop/Full_Project/FIRE/Service/gauss-mobile-firebase-adminsdk-fbsvc-56f4460390.json
```

The Gaussian Splatting conversion script is expected at:
```
/home/h702839428/Desktop/Full_Project/Gauss_Project/gaussian-splatting/convert.py
```

## Usage

### Running the Complete Pipeline

To run the entire pipeline for a specific user:

```bash
bash run_pipeline.sh USER_ID
```

This will execute all steps in sequence, using a state file to track progress.

### Running Individual Steps

Each step can also be run independently:

#### Step 1: Download Data

```bash
python download_data.py --user-id USER_ID --output-path OUTPUT_DIR --service-account SERVICE_ACCOUNT_PATH
```

#### Step 2: Convert Data

```bash
python convert_data.py --user-id USER_ID --input-path INPUT_DIR --convert-script-path CONVERT_SCRIPT_DIR --state-file STATE_FILE
```

#### Step 3: Copy to Docker

```bash
python copy_to_docker.py --user-id USER_ID --input-path INPUT_DIR --container CONTAINER_NAME --container-path CONTAINER_PATH --state-file STATE_FILE
```

#### Step 4: Run Training

```bash
python run_training.py --user-id USER_ID --container CONTAINER_NAME --container-path CONTAINER_PATH --env-name CONDA_ENV --state-file STATE_FILE
```

#### Step 5: Upload Results

```bash
python upload_results.py --user-id USER_ID --container CONTAINER_NAME --service-account SERVICE_ACCOUNT_PATH --state-file STATE_FILE
```

## Troubleshooting

### NVIDIA GPU Issues
- Ensure NVIDIA drivers are properly installed: `nvidia-smi`
- Check that NVIDIA Container Toolkit is installed: `dpkg -l | grep nvidia-container-toolkit`
- Verify that Docker can access GPUs: `sudo docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi`

### X11 Forwarding Issues
- If you encounter display issues, ensure that X11 is properly configured with: `xhost +local:docker`
- For headless servers, ensure the Xvfb script is working: `/app/run_with_xvfb.sh echo "Display test"`

## State Management

The pipeline maintains state between steps using a JSON file, created at:
```
/home/h702839428/Desktop/Full_Project/FIRE/dedicated_SENDTO/USER_ID/pipeline_state.json
```

This allows the pipeline to be restarted from any point if a step fails.

## Output

The pipeline generates 3D models in the following formats:
- PLY files (raw point cloud data)
- OBJ files (3D mesh with textures)

These files are uploaded to Firebase Storage and linked in Firestore for user access through the application.

## File Structure

- `run_pipeline.sh`: Main script to run the entire pipeline
- `download_data.py`: Script for downloading user data from Firebase
- `convert_data.py`: Script for converting data to the proper format
- `copy_to_docker.py`: Script for transferring data to the Docker container
- `run_training.py`: Script for running the Gaussian Splatting algorithm
- `upload_results.py`: Script for uploading results to Firebase

## Conda Environment

The training process uses a conda environment within the Docker container. By default, it searches for environments named "gaussian" or "sugar".

## Firebase Integration

The pipeline integrates with Firebase in the following ways:
- Downloads user data from Firestore collections
- Uploads processed 3D models to Firebase Storage
- Creates references in Firestore collections:
  - `plyFiles`: Contains references to uploaded model files
  - `users/{userID}/modelProcessing`: Contains processing status information

## Error Handling

Each step includes error handling and colorized terminal output for clear status indication. If any step fails, the pipeline will abort with an appropriate error message.
