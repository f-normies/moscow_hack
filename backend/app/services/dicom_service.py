import asyncio
import logging
import zipfile
import uuid
from io import BytesIO
from typing import Any, Dict, List, Tuple
from datetime import datetime, date, time
from decimal import Decimal

import pydicom
from pydicom.dataset import Dataset
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    DICOMStudy, DICOMSeries, DICOMMetadata,
    DICOMStudyCreate, DICOMSeriesCreate, DICOMMetadataCreate,
    FileMetadata, User
)
from app.services.minio_service import minio_service

logger = logging.getLogger(__name__)


class DICOMProcessingService:
    """Service for processing DICOM files from ZIP archives"""

    def __init__(self):
        self.max_zip_size = 1 * 1024 * 1024 * 1024  # 1GB
        self.max_individual_file_size = 100 * 1024 * 1024  # 100MB

    async def process_dicom_zip(
        self,
        zip_data: bytes,
        filename: str,
        user_id: uuid.UUID,
        session: Session
    ) -> DICOMStudy:
        """Process DICOM ZIP archive and extract all files"""

        # Validate ZIP size
        if len(zip_data) > self.max_zip_size:
            raise ValueError(f"ZIP file too large: {len(zip_data)} bytes")

        try:
            # Process ZIP in memory
            with zipfile.ZipFile(BytesIO(zip_data), 'r') as zip_ref:
                dicom_files = self._find_dicom_files(zip_ref)

                if not dicom_files:
                    raise ValueError("No DICOM files found in ZIP archive")

                logger.info(f"Found {len(dicom_files)} DICOM files in ZIP archive")

                # Process first file to determine study information
                first_file_data = zip_ref.read(dicom_files[0])
                first_ds = pydicom.dcmread(BytesIO(first_file_data), stop_before_pixels=True)

                # Create or get existing study
                study = await self._get_or_create_study(first_ds, user_id, session)

                # Process all DICOM files
                processed_count = 0
                for file_path in dicom_files:
                    try:
                        file_data = zip_ref.read(file_path)
                        if len(file_data) > self.max_individual_file_size:
                            logger.warning(f"Skipping large file: {file_path}")
                            continue

                        await self._process_individual_dicom(
                            file_data, file_path, study.id, user_id, session
                        )
                        processed_count += 1

                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        continue

                # Update study file count
                study.file_count = processed_count
                study.updated_at = datetime.utcnow()
                session.add(study)
                session.commit()
                session.refresh(study)

                logger.info(f"Processed {processed_count} DICOM files for study {study.id}")
                return study

        except Exception as e:
            logger.error(f"Error processing DICOM ZIP: {e}")
            raise ValueError(f"Failed to process DICOM ZIP: {e}")

    def _find_dicom_files(self, zip_ref: zipfile.ZipFile) -> List[str]:
        """Find DICOM files in ZIP archive"""
        dicom_files = []
        for file_info in zip_ref.filelist:
            if file_info.is_dir():
                continue

            filename = file_info.filename.lower()
            # Check for DICOM file extensions and patterns
            if (filename.endswith(('.dcm', '.dicom', '.dic')) or
                'dicom' in filename or
                self._is_dicom_file(zip_ref, file_info.filename)):
                dicom_files.append(file_info.filename)

        return dicom_files

    def _is_dicom_file(self, zip_ref: zipfile.ZipFile, filename: str) -> bool:
        """Check if file is DICOM by reading header"""
        try:
            with zip_ref.open(filename) as f:
                # Read first 132 bytes to check for DICOM signature
                header = f.read(132)
                return len(header) >= 132 and header[128:132] == b'DICM'
        except:
            return False

    async def _get_or_create_study(
        self,
        ds: Dataset,
        user_id: uuid.UUID,
        session: Session
    ) -> DICOMStudy:
        """Get existing study or create new one"""
        study_uid = getattr(ds, 'StudyInstanceUID', None)
        if not study_uid:
            raise ValueError("DICOM file missing StudyInstanceUID")

        # Check if study already exists
        existing_study = session.exec(
            select(DICOMStudy).where(
                DICOMStudy.study_instance_uid == study_uid,
                DICOMStudy.owner_id == user_id
            )
        ).first()

        if existing_study:
            logger.info(f"Using existing study: {study_uid}")
            return existing_study

        # Create new study
        study_data = self._extract_study_metadata(ds)
        study = DICOMStudy(
            study_instance_uid=study_uid,
            owner_id=user_id,
            **study_data
        )

        session.add(study)
        session.commit()
        session.refresh(study)
        logger.info(f"Created new study: {study_uid}")
        return study

    def _extract_study_metadata(self, ds: Dataset) -> Dict[str, Any]:
        """Extract study-level metadata from DICOM"""
        metadata = {}

        # Study information
        if hasattr(ds, 'StudyDate'):
            try:
                study_date_str = str(ds.StudyDate)
                if len(study_date_str) == 8:  # YYYYMMDD format
                    metadata['study_date'] = datetime.strptime(study_date_str, '%Y%m%d').date()
            except Exception as e:
                logger.warning(f"Error parsing study date: {e}")

        if hasattr(ds, 'StudyTime'):
            try:
                study_time_str = str(ds.StudyTime)
                # Handle various time formats
                if '.' in study_time_str:
                    study_time_str = study_time_str.split('.')[0]
                if len(study_time_str) >= 6:
                    metadata['study_time'] = datetime.strptime(study_time_str[:6], '%H%M%S').time()
            except Exception as e:
                logger.warning(f"Error parsing study time: {e}")

        # Patient and study info (anonymized)
        metadata['study_description'] = getattr(ds, 'StudyDescription', None)
        metadata['patient_id'] = getattr(ds, 'PatientID', None)
        metadata['modality'] = getattr(ds, 'Modality', None)
        metadata['institution_name'] = getattr(ds, 'InstitutionName', None)

        return metadata

    async def _process_individual_dicom(
        self,
        file_data: bytes,
        file_path: str,
        study_id: uuid.UUID,
        user_id: uuid.UUID,
        session: Session
    ) -> None:
        """Process individual DICOM file"""

        # Parse DICOM metadata
        ds = pydicom.dcmread(BytesIO(file_data), stop_before_pixels=True)

        # Get or create series
        series = await self._get_or_create_series(ds, study_id, session)

        # Generate filename for MinIO storage
        instance_uid = getattr(ds, 'SOPInstanceUID', None)
        if not instance_uid:
            instance_uid = f"unknown_{uuid.uuid4()}"

        # Clean filename for storage
        safe_filename = f"{instance_uid}.dcm"

        # Upload to MinIO with organized path structure
        file_metadata = await minio_service.upload_file(
            file_data=file_data,
            filename=safe_filename,
            user_id=user_id,
            session=session
        )

        # Update MinIO path to organized structure
        organized_path = f"dicom/{study_id}/{series.id}/{safe_filename}"
        file_metadata.minio_path = organized_path
        file_metadata.content_type = "application/dicom"
        session.add(file_metadata)

        # Create DICOM metadata record
        dicom_metadata = self._create_dicom_metadata(ds, file_metadata.id, series.id)
        session.add(dicom_metadata)

        # Update series image count
        series.image_count += 1
        session.add(series)

        session.commit()
        logger.debug(f"Processed DICOM file: {file_path}")

    async def _get_or_create_series(
        self,
        ds: Dataset,
        study_id: uuid.UUID,
        session: Session
    ) -> DICOMSeries:
        """Get existing series or create new one"""
        series_uid = getattr(ds, 'SeriesInstanceUID', None)
        if not series_uid:
            raise ValueError("DICOM file missing SeriesInstanceUID")

        # Check if series already exists
        existing_series = session.exec(
            select(DICOMSeries).where(
                DICOMSeries.series_instance_uid == series_uid,
                DICOMSeries.study_id == study_id
            )
        ).first()

        if existing_series:
            return existing_series

        # Create new series
        series_data = self._extract_series_metadata(ds)
        series = DICOMSeries(
            series_instance_uid=series_uid,
            study_id=study_id,
            **series_data
        )

        session.add(series)
        session.commit()
        session.refresh(series)
        logger.debug(f"Created new series: {series_uid}")
        return series

    def _extract_series_metadata(self, ds: Dataset) -> Dict[str, Any]:
        """Extract series-level metadata from DICOM"""
        metadata = {}

        # Series information
        if hasattr(ds, 'SeriesNumber'):
            try:
                metadata['series_number'] = int(ds.SeriesNumber)
            except Exception as e:
                logger.warning(f"Error parsing series number: {e}")

        metadata['series_description'] = getattr(ds, 'SeriesDescription', None)
        metadata['modality'] = getattr(ds, 'Modality', None)
        metadata['body_part_examined'] = getattr(ds, 'BodyPartExamined', None)

        return metadata

    def _create_dicom_metadata(
        self,
        ds: Dataset,
        file_id: uuid.UUID,
        series_id: uuid.UUID
    ) -> DICOMMetadata:
        """Create DICOM metadata record from parsed DICOM"""

        # Extract key imaging parameters
        instance_number = None
        if hasattr(ds, 'InstanceNumber'):
            try:
                instance_number = int(ds.InstanceNumber)
            except Exception as e:
                logger.warning(f"Error parsing instance number: {e}")

        # Image dimensions
        rows = getattr(ds, 'Rows', None)
        columns = getattr(ds, 'Columns', None)

        # Physical measurements
        pixel_spacing = None
        if hasattr(ds, 'PixelSpacing'):
            try:
                spacing = ds.PixelSpacing
                pixel_spacing = f"{float(spacing[0])},{float(spacing[1])}"
            except Exception as e:
                logger.warning(f"Error parsing pixel spacing: {e}")

        slice_thickness = None
        if hasattr(ds, 'SliceThickness'):
            try:
                slice_thickness = Decimal(str(ds.SliceThickness))
            except Exception as e:
                logger.warning(f"Error parsing slice thickness: {e}")

        # Display parameters
        window_center = None
        window_width = None
        if hasattr(ds, 'WindowCenter'):
            try:
                window_center = Decimal(str(ds.WindowCenter))
            except Exception as e:
                logger.warning(f"Error parsing window center: {e}")
        if hasattr(ds, 'WindowWidth'):
            try:
                window_width = Decimal(str(ds.WindowWidth))
            except Exception as e:
                logger.warning(f"Error parsing window width: {e}")

        # Full metadata as JSON (selected fields only)
        extracted_metadata = {
            'SOPInstanceUID': getattr(ds, 'SOPInstanceUID', None),
            'SOPClassUID': getattr(ds, 'SOPClassUID', None),
            'Modality': getattr(ds, 'Modality', None),
            'StudyDescription': getattr(ds, 'StudyDescription', None),
            'SeriesDescription': getattr(ds, 'SeriesDescription', None),
            'BodyPartExamined': getattr(ds, 'BodyPartExamined', None),
            'PatientPosition': getattr(ds, 'PatientPosition', None),
            'ImageType': getattr(ds, 'ImageType', None),
            'AcquisitionDate': getattr(ds, 'AcquisitionDate', None),
            'AcquisitionTime': getattr(ds, 'AcquisitionTime', None),
        }

        return DICOMMetadata(
            file_id=file_id,
            series_id=series_id,
            instance_number=instance_number,
            rows=rows,
            columns=columns,
            pixel_spacing=pixel_spacing,
            slice_thickness=slice_thickness,
            window_center=window_center,
            window_width=window_width,
            extracted_metadata=extracted_metadata
        )

    async def get_study_with_series(
        self,
        study_id: uuid.UUID,
        user_id: uuid.UUID,
        session: Session
    ) -> DICOMStudy | None:
        """Get study with all its series loaded"""
        study = session.exec(
            select(DICOMStudy).where(
                DICOMStudy.id == study_id,
                DICOMStudy.owner_id == user_id
            )
        ).first()

        if study:
            # Load series separately to avoid eager loading issues
            series = session.exec(
                select(DICOMSeries).where(DICOMSeries.study_id == study_id)
            ).all()
            study.series = list(series)

        return study

    async def list_user_studies(
        self,
        user_id: uuid.UUID,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[DICOMStudy]:
        """List DICOM studies for a user"""
        studies = session.exec(
            select(DICOMStudy)
            .where(DICOMStudy.owner_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(DICOMStudy.created_at.desc())
        ).all()

        return list(studies)

    async def delete_study(
        self,
        study_id: uuid.UUID,
        user_id: uuid.UUID,
        session: Session
    ) -> None:
        """Delete DICOM study and all associated files"""
        study = session.exec(
            select(DICOMStudy).where(
                DICOMStudy.id == study_id,
                DICOMStudy.owner_id == user_id
            )
        ).first()

        if not study:
            raise ValueError("Study not found")

        # Delete study (cascade will handle related records)
        session.delete(study)
        session.commit()
        logger.info(f"Deleted DICOM study: {study_id}")


# Global service instance
dicom_service = DICOMProcessingService()