#!/usr/bin/env python3
"""
Bulk Inference Script for Medical Image Segmentation

Uploads DICOM studies from ./data/studies and runs inference on them.

Usage:
    python scripts/bulk_inference.py --email user@example.com --password secret

Features:
    - Authenticates with backend API
    - Uploads all ZIP files from data/studies/
    - Submits inference jobs for each study
    - Monitors job progress
    - Downloads results when complete
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BulkInferenceClient:
    """Client for bulk DICOM inference processing"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        email: str = None,
        password: str = None
    ):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None

        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def authenticate(self) -> bool:
        """Authenticate with backend and get access token"""
        logger.info(f"Authenticating as {self.email}...")

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/login/access-token",
                data={
                    "username": self.email,
                    "password": self.password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            logger.info("✓ Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Authentication failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        if not self.access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def upload_dicom_zip(self, zip_path: Path) -> Optional[Dict]:
        """Upload DICOM ZIP file and return study details"""
        logger.info(f"Uploading {zip_path.name}...")

        try:
            with open(zip_path, 'rb') as f:
                files = {'file': (zip_path.name, f, 'application/zip')}
                response = self.session.post(
                    f"{self.base_url}/api/v1/dicom/upload",
                    headers=self._get_headers(),
                    files=files,
                    timeout=300  # 5 minute timeout for large files
                )
                response.raise_for_status()

            study = response.json()
            logger.info(f"✓ Uploaded study: {study['id']} - {study.get('study_description', 'No description')}")
            return study

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Upload failed for {zip_path.name}: {e}")
            return None

    def get_available_models(self) -> List[Dict]:
        """Get list of available inference models"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/inference/models",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to fetch models: {e}")
            return []

    def submit_inference(
        self,
        study_id: str,
        model_id: str,
        series_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Submit inference job for a study"""
        logger.info(f"Submitting inference job for study {study_id}...")

        payload = {
            "study_id": study_id,
            "model_id": model_id
        }
        if series_id:
            payload["series_id"] = series_id

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/inference/submit",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()

            job = response.json()
            logger.info(f"✓ Inference job submitted: {job['id']}")
            return job

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Inference submission failed: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of inference job"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/inference/jobs/{job_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to get job status: {e}")
            return None

    def wait_for_job(self, job_id: str, timeout: int = 3600, poll_interval: int = 5) -> Optional[Dict]:
        """Wait for job to complete and return final status"""
        logger.info(f"Waiting for job {job_id} to complete...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job_status(job_id)

            if not job:
                logger.error("Failed to get job status")
                return None

            status = job['status']
            progress = job.get('progress', 0.0)

            if status == 'completed':
                logger.info(f"✓ Job {job_id} completed successfully!")
                return job
            elif status == 'failed':
                error = job.get('error_message', 'Unknown error')
                logger.error(f"✗ Job {job_id} failed: {error}")
                return job
            elif status == 'cancelled':
                logger.warning(f"⚠ Job {job_id} was cancelled")
                return job
            else:
                logger.info(f"  Job {job_id}: {status} - {progress*100:.1f}% complete")
                time.sleep(poll_interval)

        logger.error(f"✗ Job {job_id} timed out after {timeout}s")
        return None

    def download_result(self, job_id: str, output_dir: Path, download_ct: bool = True):
        """Download segmentation and optionally CT results"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download segmentation
        try:
            logger.info(f"Downloading segmentation for job {job_id}...")
            response = self.session.get(
                f"{self.base_url}/api/v1/inference/jobs/{job_id}/download",
                headers=self._get_headers(),
                allow_redirects=True
            )
            response.raise_for_status()

            seg_path = output_dir / f"{job_id}_segmentation.nii.gz"
            with open(seg_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"✓ Saved segmentation: {seg_path}")

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to download segmentation: {e}")

        # Download processed CT
        if download_ct:
            try:
                logger.info(f"Downloading processed CT for job {job_id}...")
                response = self.session.get(
                    f"{self.base_url}/api/v1/inference/jobs/{job_id}/download-ct",
                    headers=self._get_headers(),
                    allow_redirects=True
                )
                response.raise_for_status()

                ct_path = output_dir / f"{job_id}_ct.nii.gz"
                with open(ct_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"✓ Saved CT: {ct_path}")

            except requests.exceptions.RequestException as e:
                logger.error(f"✗ Failed to download CT: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Run bulk inference on DICOM studies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all studies in data/studies/
  python scripts/bulk_inference.py --email user@example.com --password secret

  # Use custom backend URL
  python scripts/bulk_inference.py --url http://192.168.1.100:8000 \\
      --email user@example.com --password secret

  # Specify model by name
  python scripts/bulk_inference.py --email user@example.com \\
      --password secret --model "nnUNet Lung"
        """
    )

    parser.add_argument('--url', default='http://localhost:8000',
                        help='Backend API URL (default: http://localhost:8000)')
    parser.add_argument('--email', default='admin@webapp.com',
                        help='User email for authentication')
    parser.add_argument('--password', default='GYSgmXnhFR3p7-4x-2D21A',
                        help='User password for authentication')
    parser.add_argument('--studies-dir', type=Path, default=Path('data/studies'),
                        help='Directory containing DICOM ZIP files (default: data/studies)')
    parser.add_argument('--output-dir', type=Path, default=Path('data/results'),
                        help='Directory for downloaded results (default: data/results)')
    parser.add_argument('--model', type=str, default=None,
                        help='Model name to use (default: first available model)')
    parser.add_argument('--no-download-ct', action='store_true',
                        help='Skip downloading processed CT images')

    args = parser.parse_args()

    # Initialize client
    client = BulkInferenceClient(
        base_url=args.url,
        email=args.email,
        password=args.password
    )

    # Authenticate
    if not client.authenticate():
        logger.error("Authentication failed. Exiting.")
        sys.exit(1)

    # Get available models
    models = client.get_available_models()
    if not models:
        logger.error("No models available. Exiting.")
        sys.exit(1)

    logger.info(f"Available models: {len(models)}")
    for model in models:
        logger.info(f"  - {model['name']} ({model['model_type']}, {model['modality']})")

    # Select model
    if args.model:
        selected_model = next((m for m in models if args.model.lower() in m['name'].lower()), None)
        if not selected_model:
            logger.error(f"Model '{args.model}' not found. Exiting.")
            sys.exit(1)
    else:
        selected_model = models[0]

    logger.info(f"Using model: {selected_model['name']}")

    # Find ZIP files
    studies_dir = args.studies_dir
    if not studies_dir.exists():
        logger.error(f"Studies directory not found: {studies_dir}")
        sys.exit(1)

    zip_files = list(studies_dir.glob('*.zip'))
    if not zip_files:
        logger.warning(f"No ZIP files found in {studies_dir}")
        sys.exit(0)

    logger.info(f"Found {len(zip_files)} DICOM ZIP files")

    # Process each study
    results = []
    for i, zip_file in enumerate(zip_files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {i}/{len(zip_files)}: {zip_file.name}")
        logger.info(f"{'='*60}")

        # Upload study
        study = client.upload_dicom_zip(zip_file)
        if not study:
            logger.error(f"Skipping {zip_file.name} due to upload failure")
            continue

        # Submit inference
        job = client.submit_inference(
            study_id=study['id'],
            model_id=selected_model['id']
        )
        if not job:
            logger.error(f"Skipping {zip_file.name} due to inference submission failure")
            continue

        # Wait for completion
        final_job = client.wait_for_job(job['id'])
        if final_job and final_job['status'] == 'completed':
            # Download results
            client.download_result(
                job['id'],
                args.output_dir / zip_file.stem,
                download_ct=not args.no_download_ct
            )
            results.append({
                'zip_file': zip_file.name,
                'study_id': study['id'],
                'job_id': job['id'],
                'status': 'success'
            })
        else:
            results.append({
                'zip_file': zip_file.name,
                'study_id': study.get('id', 'unknown'),
                'job_id': job.get('id', 'unknown'),
                'status': 'failed'
            })

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("PROCESSING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total studies: {len(zip_files)}")
    logger.info(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    logger.info(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")

    # Save results log
    results_log = args.output_dir / 'processing_log.json'
    results_log.parent.mkdir(parents=True, exist_ok=True)
    with open(results_log, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults log saved to: {results_log}")


if __name__ == '__main__':
    main()
