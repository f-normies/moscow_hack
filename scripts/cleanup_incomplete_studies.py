#!/usr/bin/env python3
"""
Cleanup incomplete DICOM studies that have no metadata records.

These can occur when:
- Study was uploaded but files exceeded size limits
- Metadata extraction failed
- Upload was interrupted
"""

import argparse
import requests


def cleanup_incomplete_studies(base_url: str, email: str, password: str):
    """Find and delete studies with no DICOM metadata"""

    # Authenticate
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all studies
    response = requests.get(f"{base_url}/api/v1/dicom/studies", headers=headers)
    response.raise_for_status()
    studies = response.json()

    print(f"Found {len(studies)} studies")

    incomplete = []
    for study in studies:
        # Check if study has series with images
        if not study.get('series') or all(s.get('image_count', 0) == 0 for s in study['series']):
            incomplete.append(study)
            print(f"  ⚠ Incomplete study: {study['id']} - {study.get('study_instance_uid', 'unknown')}")

    if not incomplete:
        print("✓ No incomplete studies found")
        return

    print(f"\nFound {len(incomplete)} incomplete studies")
    confirm = input("Delete them? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Aborted")
        return

    for study in incomplete:
        try:
            response = requests.delete(
                f"{base_url}/api/v1/dicom/studies/{study['id']}",
                headers=headers
            )
            response.raise_for_status()
            print(f"✓ Deleted study {study['id']}")
        except Exception as e:
            print(f"✗ Failed to delete {study['id']}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup incomplete DICOM studies")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--email", default="admin@webapp.com", help="Admin email")
    parser.add_argument("--password", default="GYSgmXnhFR3p7-4x-2D21A", help="Admin password")

    args = parser.parse_args()
    cleanup_incomplete_studies(args.url, args.email, args.password)
