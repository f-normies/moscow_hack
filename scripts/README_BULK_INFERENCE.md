# Bulk Inference Script

Automated script for processing multiple DICOM studies through the inference pipeline.

## Setup

1. **Ensure backend is running:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.gpu.yml up -d
   ```

2. **Install Python dependencies:**
   ```bash
   pip install requests
   ```

3. **Prepare DICOM studies:**
   - Place DICOM ZIP files in `data/studies/`
   - Each ZIP should contain a complete DICOM series

4. **Ensure models are available:**
   - Models should be in `data/models/`
   - Seeded automatically on backend startup

## Usage

### Basic Usage (with defaults)
```bash
python scripts/bulk_inference.py
```
Uses default admin credentials from the script.

### Custom Authentication
```bash
python scripts/bulk_inference.py \
    --email user@example.com \
    --password your-password
```

### Advanced Options
```bash
python scripts/bulk_inference.py \
    --url http://localhost:8000 \
    --email admin@webapp.com \
    --password GYSgmXnhFR3p7-4x-2D21A \
    --studies-dir data/studies \
    --output-dir data/results \
    --model "nnUNet Lung" \
    --no-download-ct
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--url` | `http://localhost:8000` | Backend API URL |
| `--email` | `admin@webapp.com` | User email for authentication |
| `--password` | `GYSgmXnhFR3p7-4x-2D21A` | User password |
| `--studies-dir` | `data/studies` | Directory containing DICOM ZIP files |
| `--output-dir` | `data/results` | Directory for downloaded results |
| `--model` | First available | Model name (partial match supported) |
| `--no-download-ct` | False | Skip downloading processed CT images |

## Output Structure

Results are organized by study:

```
data/results/
├── study_001/
│   ├── {job_id}_segmentation.nii.gz
│   └── {job_id}_ct.nii.gz
├── study_002/
│   ├── {job_id}_segmentation.nii.gz
│   └── {job_id}_ct.nii.gz
└── processing_log.json
```

## Features

- ✅ Automatic authentication with backend
- ✅ Progress tracking for each job
- ✅ Retry logic for failed requests
- ✅ Parallel processing support (processes studies sequentially, but can run multiple script instances)
- ✅ Downloads both segmentation and aligned CT
- ✅ Comprehensive logging
- ✅ JSON log of all processed studies

## Example Workflow

1. **Prepare data:**
   ```bash
   mkdir -p data/studies
   cp /path/to/dicom/*.zip data/studies/
   ```

2. **Run bulk inference:**
   ```bash
   python scripts/bulk_inference.py
   ```

3. **Monitor progress:**
   Script will output progress for each study:
   ```
   ============================================================
   Processing 1/5: lung_study_001.zip
   ============================================================
   Uploading lung_study_001.zip...
   ✓ Uploaded study: a1b2c3d4-... - Lung CT
   Submitting inference job for study a1b2c3d4-...
   ✓ Inference job submitted: e5f6g7h8-...
   Waiting for job e5f6g7h8-... to complete...
     Job e5f6g7h8-...: running - 35.0% complete
     Job e5f6g7h8-...: running - 70.0% complete
   ✓ Job e5f6g7h8-... completed successfully!
   Downloading segmentation for job e5f6g7h8-...
   ✓ Saved segmentation: data/results/lung_study_001/e5f6g7h8-..._segmentation.nii.gz
   Downloading processed CT for job e5f6g7h8-...
   ✓ Saved CT: data/results/lung_study_001/e5f6g7h8-..._ct.nii.gz
   ```

4. **Check results:**
   ```bash
   ls data/results/
   cat data/results/processing_log.json
   ```

## Troubleshooting

### Authentication Failed
- Verify backend is running: `docker compose ps`
- Check credentials match user in database
- Ensure backend URL is correct

### Upload Failed
- Check ZIP file is valid DICOM archive
- Verify file size isn't too large (check backend MAX_FILE_SIZE)
- Ensure sufficient disk space in MinIO

### Inference Failed
- Check worker logs: `docker compose logs inference-worker-gpu`
- Verify GPU is available: `nvidia-smi`
- Check model files exist in `data/models/`

### Download Failed
- Job may still be processing (wait longer)
- Check job completed successfully
- Verify sufficient disk space for results

## Notes

- Script processes studies **sequentially** to avoid overwhelming the system
- Each job has a **1 hour timeout** (configurable in code)
- Failed studies are logged but don't stop processing
- Results are saved incrementally (safe to interrupt)
- Processing log is updated after each study

## Advanced: Parallel Processing

To process multiple studies in parallel, run multiple instances:

```bash
# Terminal 1
python scripts/bulk_inference.py --studies-dir data/studies/batch1

# Terminal 2
python scripts/bulk_inference.py --studies-dir data/studies/batch2
```
