import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    FileMetadata,
    FileMetadataPublic,
    FileMetadataWithUrl,
    FilesPublic,
    Message,
)
from app.services.minio_service import minio_service

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check() -> dict:
    """
    Check MinIO service health
    """
    try:
        health_status = await minio_service.health_check()
        return health_status

    except Exception:
        raise HTTPException(status_code=503, detail="MinIO service unavailable")


@router.post("/upload", response_model=FileMetadataPublic)
async def upload_file(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> FileMetadata:
    """
    Upload a file to MinIO storage
    """
    if not file.filename or file.filename == "":
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        # Read file data
        file_data = await file.read()

        # Upload file using MinIO service
        file_metadata = await minio_service.upload_file(
            file_data=file_data,
            filename=file.filename,
            user_id=current_user.id,
            session=session,
        )

        return file_metadata

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.get("/", response_model=FilesPublic)
async def list_files(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> FilesPublic:
    """
    Retrieve files for the current user
    """
    try:
        files = await minio_service.list_user_files(
            user_id=current_user.id, session=session, skip=skip, limit=limit
        )

        return FilesPublic(data=files, count=len(files))

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve files")


@router.get("/{file_id}", response_model=FileMetadataPublic)
async def get_file_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
) -> FileMetadata:
    """
    Get file metadata by ID
    """
    try:
        file_metadata = await minio_service.get_file_info(
            file_id=file_id, user_id=current_user.id, session=session
        )

        return file_metadata

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve file info")


@router.get("/{file_id}/download-url", response_model=FileMetadataWithUrl)
async def get_download_url(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    expiry_hours: int = 1,
) -> FileMetadataWithUrl:
    """
    Generate a presigned download URL for a file
    """
    if expiry_hours < 1 or expiry_hours > 24:
        raise HTTPException(
            status_code=400, detail="Expiry hours must be between 1 and 24"
        )

    try:
        # Get file metadata
        file_metadata = await minio_service.get_file_info(
            file_id=file_id, user_id=current_user.id, session=session
        )

        # Generate presigned URL
        download_url = await minio_service.generate_presigned_url(
            file_id=file_id,
            user_id=current_user.id,
            session=session,
            expiry_hours=expiry_hours,
        )

        # Convert to response model with download URL
        return FileMetadataWithUrl(
            **file_metadata.model_dump(), download_url=download_url
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.delete("/{file_id}", response_model=Message)
async def delete_file(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
) -> Message:
    """
    Delete a file from storage and database
    """
    try:
        await minio_service.delete_file(
            file_id=file_id, user_id=current_user.id, session=session
        )

        return Message(message="File deleted successfully")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete file")
