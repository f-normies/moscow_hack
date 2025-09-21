import uuid
import logging
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    DICOMStudy, DICOMStudyPublic, DICOMSeries, DICOMSeriesPublic,
    DICOMMetadata, DICOMMetadataPublic, Message
)
from app.services.dicom_service import dicom_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=DICOMStudyPublic)
async def upload_dicom_zip(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> DICOMStudy:
    """
    Upload DICOM ZIP archive for processing
    """
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="File must be a ZIP archive"
        )

    try:
        # Read ZIP file data
        zip_data = await file.read()

        logger.info(f"Processing DICOM ZIP upload: {file.filename} ({len(zip_data)} bytes)")

        # Process DICOM ZIP
        study = await dicom_service.process_dicom_zip(
            zip_data=zip_data,
            filename=file.filename,
            user_id=current_user.id,
            session=session
        )

        logger.info(f"Successfully processed DICOM ZIP: {study.id}")
        return study

    except ValueError as e:
        logger.warning(f"DICOM upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DICOM upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process DICOM ZIP")


@router.get("/studies", response_model=List[DICOMStudyPublic])
async def list_dicom_studies(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> List[DICOMStudy]:
    """
    List DICOM studies for current user
    """
    try:
        studies = await dicom_service.list_user_studies(
            user_id=current_user.id,
            session=session,
            skip=skip,
            limit=limit
        )

        logger.info(f"Retrieved {len(studies)} DICOM studies for user {current_user.id}")
        return studies

    except Exception as e:
        logger.error(f"Error listing DICOM studies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve studies")


@router.get("/studies/{study_id}", response_model=DICOMStudyPublic)
async def get_dicom_study(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    study_id: uuid.UUID,
) -> DICOMStudy:
    """
    Get DICOM study details with series
    """
    try:
        study = await dicom_service.get_study_with_series(
            study_id=study_id,
            user_id=current_user.id,
            session=session
        )

        if not study:
            raise HTTPException(status_code=404, detail="Study not found")

        logger.info(f"Retrieved DICOM study: {study_id}")
        return study

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DICOM study: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve study")


@router.get("/metadata/{file_id}", response_model=DICOMMetadataPublic)
async def get_dicom_metadata(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
) -> DICOMMetadata:
    """
    Get detailed DICOM metadata for a file
    """
    try:
        # Verify file ownership through FileMetadata and get DICOM metadata
        from app.models import FileMetadata

        metadata = session.exec(
            select(DICOMMetadata)
            .join(FileMetadata)
            .where(
                DICOMMetadata.file_id == file_id,
                FileMetadata.owner_id == current_user.id
            )
        ).first()

        if not metadata:
            raise HTTPException(status_code=404, detail="DICOM metadata not found")

        logger.info(f"Retrieved DICOM metadata for file: {file_id}")
        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DICOM metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metadata")


@router.get("/series/{series_id}/metadata", response_model=List[DICOMMetadataPublic])
async def get_series_metadata(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    series_id: uuid.UUID,
) -> List[DICOMMetadata]:
    """
    Get all DICOM metadata for files in a series
    """
    try:
        # First verify the series belongs to the user
        series = session.exec(
            select(DICOMSeries)
            .join(DICOMStudy)
            .where(
                DICOMSeries.id == series_id,
                DICOMStudy.owner_id == current_user.id
            )
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Series not found")

        # Get all metadata for the series
        metadata_list = session.exec(
            select(DICOMMetadata)
            .where(DICOMMetadata.series_id == series_id)
            .order_by(DICOMMetadata.instance_number)
        ).all()

        logger.info(f"Retrieved {len(metadata_list)} DICOM metadata records for series: {series_id}")
        return list(metadata_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving series metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve series metadata")


@router.delete("/studies/{study_id}", response_model=Message)
async def delete_dicom_study(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    study_id: uuid.UUID,
) -> Message:
    """
    Delete DICOM study and all associated files
    """
    try:
        await dicom_service.delete_study(
            study_id=study_id,
            user_id=current_user.id,
            session=session
        )

        logger.info(f"Deleted DICOM study: {study_id}")
        return Message(message="DICOM study deleted successfully")

    except ValueError as e:
        logger.warning(f"DICOM study deletion error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting DICOM study: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete study")


@router.get("/health", response_model=dict)
async def dicom_health_check() -> dict:
    """
    Check DICOM service health
    """
    try:
        # Test pydicom import
        import pydicom

        # Test database connection through a simple query
        return {
            "status": "healthy",
            "pydicom_version": pydicom.__version__,
            "service": "DICOMProcessingService"
        }

    except Exception as e:
        logger.error(f"DICOM health check failed: {e}")
        raise HTTPException(status_code=503, detail="DICOM service unavailable")