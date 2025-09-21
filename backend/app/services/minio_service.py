import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from typing import Any

import magic
from minio import Minio
from minio.error import S3Error
from sqlmodel import Session

from app.core.config import settings
from app.models import FileMetadata

logger = logging.getLogger(__name__)


def handle_minio_errors(func):
    """Decorator to handle MinIO errors consistently"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except S3Error as e:
            logger.error(f"\tMinIO error in {func.__name__}: {e}")
            raise ValueError(f"Storage operation failed: {e}")
        except Exception as e:
            logger.error(f"\tUnexpected error in {func.__name__}: {e}")
            raise

    return wrapper


class MinIOService:
    """Service for handling file operations with MinIO"""

    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME

    async def initialize(self) -> None:
        """Initialize MinIO service and create bucket if it doesn't exist"""
        try:
            # Check if bucket exists, create if not
            if not await self._bucket_exists():
                await self._create_bucket()
                logger.info(f"\tCreated MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"\tMinIO bucket exists: {self.bucket_name}")
        except Exception as e:
            logger.error(f"\tFailed to initialize MinIO service: {e}")
            raise

    async def _bucket_exists(self) -> bool:
        """Check if bucket exists"""

        def _check():
            return self.client.bucket_exists(self.bucket_name)

        return await asyncio.to_thread(_check)

    async def _create_bucket(self) -> None:
        """Create bucket"""

        def _create():
            return self.client.make_bucket(self.bucket_name)

        await asyncio.to_thread(_create)

    def _validate_file_type(self, file_data: bytes, filename: str) -> str:
        """Validate file type and return MIME type"""
        # Get MIME type from file content
        mime_type = magic.from_buffer(file_data, mime=True)

        # Check if MIME type is allowed
        if mime_type not in settings.ALLOWED_FILE_TYPES:
            # For some file types, magic might not detect correctly, try by extension
            file_ext = filename.lower().split(".")[-1] if "." in filename else ""

            # Map common extensions to MIME types for files that might not be detected correctly
            ext_mime_map = {
                "obj": "model/obj",
                "stl": "model/stl",
                "ply": "model/ply",
                "fbx": "application/x-fbx",
                "dae": "application/x-collada",
                "3ds": "application/x-3ds",
                "blend": "application/x-blender",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "rtf": "application/rtf",
            }

            if file_ext in ext_mime_map:
                mime_type = ext_mime_map[file_ext]
                if mime_type in settings.ALLOWED_FILE_TYPES:
                    return mime_type

            raise ValueError(f"File type not allowed: {mime_type}")

        return mime_type

    def _generate_file_path(self, user_id: uuid.UUID, filename: str) -> str:
        """Generate unique file path for storage"""
        file_uuid = str(uuid.uuid4())
        file_ext = filename.split(".")[-1] if "." in filename else ""
        safe_filename = f"{file_uuid}.{file_ext}" if file_ext else file_uuid
        return f"users/{user_id}/{safe_filename}"

    @handle_minio_errors
    async def upload_file(
        self, file_data: bytes, filename: str, user_id: uuid.UUID, session: Session
    ) -> FileMetadata:
        """Upload file to MinIO and save metadata to database"""

        # Validate file size
        if len(file_data) > settings.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
            )

        # Validate file type
        content_type = self._validate_file_type(file_data, filename)

        # Generate unique file path
        file_path = self._generate_file_path(user_id, filename)

        # Upload to MinIO
        def _upload():
            return self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )

        await asyncio.to_thread(_upload)

        # Save metadata to database
        file_metadata = FileMetadata(
            filename=file_path.split("/")[-1],  # UUID-based filename
            original_name=filename,
            size=len(file_data),
            content_type=content_type,
            minio_path=file_path,
            owner_id=user_id,
            created_at=datetime.utcnow(),
        )

        session.add(file_metadata)
        session.commit()
        session.refresh(file_metadata)

        logger.info(f"\tFile uploaded successfully: {file_path} for user {user_id}")
        return file_metadata

    @handle_minio_errors
    async def get_file(
        self, file_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> bytes:
        """Get file data from MinIO"""

        # Get file metadata from database
        file_metadata = session.get(FileMetadata, file_id)
        if not file_metadata:
            raise ValueError("File not found")

        # Check user permission
        if file_metadata.owner_id != user_id:
            raise ValueError("Unauthorized access to file")

        # Get file from MinIO
        def _get():
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=file_metadata.minio_path
            )
            return response.read()

        file_data = await asyncio.to_thread(_get)
        logger.info(f"\tFile retrieved successfully: {file_metadata.minio_path}")
        return file_data

    @handle_minio_errors
    async def generate_presigned_url(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        session: Session,
        expiry_hours: int = 1,
    ) -> str:
        """Generate presigned URL for secure file access"""

        # Get file metadata from database
        file_metadata = session.get(FileMetadata, file_id)
        if not file_metadata:
            raise ValueError("File not found")

        # Check user permission
        if file_metadata.owner_id != user_id:
            raise ValueError("Unauthorized access to file")

        # Generate presigned URL
        def _generate_url():
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=file_metadata.minio_path,
                expires=timedelta(hours=expiry_hours),
            )

        url = await asyncio.to_thread(_generate_url)
        logger.info(f"\tPresigned URL generated for file: {file_metadata.minio_path}")
        return url

    @handle_minio_errors
    async def delete_file(
        self, file_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> None:
        """Delete file from MinIO and database"""

        # Get file metadata from database
        file_metadata = session.get(FileMetadata, file_id)
        if not file_metadata:
            raise ValueError("File not found")

        # Check user permission
        if file_metadata.owner_id != user_id:
            raise ValueError("Unauthorized access to file")

        # Delete from MinIO
        def _delete():
            return self.client.remove_object(
                bucket_name=self.bucket_name, object_name=file_metadata.minio_path
            )

        await asyncio.to_thread(_delete)

        # Delete from database
        session.delete(file_metadata)
        session.commit()

        logger.info(f"\tFile deleted successfully: {file_metadata.minio_path}")

    @handle_minio_errors
    async def delete_file_from_storage(self, minio_path: str) -> None:
        """Delete file from MinIO storage only (without database operations)"""

        # Delete from MinIO
        def _delete():
            return self.client.remove_object(
                bucket_name=self.bucket_name, object_name=minio_path
            )

        await asyncio.to_thread(_delete)
        logger.info(f"\tFile deleted from storage: {minio_path}")

    async def list_user_files(
        self, user_id: uuid.UUID, session: Session, skip: int = 0, limit: int = 100
    ) -> list[FileMetadata]:
        """List files for a specific user"""

        files = (
            session.query(FileMetadata)
            .filter(FileMetadata.owner_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

        return files

    async def get_file_info(
        self, file_id: uuid.UUID, user_id: uuid.UUID, session: Session
    ) -> FileMetadata:
        """Get file metadata"""

        file_metadata = session.get(FileMetadata, file_id)
        if not file_metadata:
            raise ValueError("File not found")

        # Check user permission
        if file_metadata.owner_id != user_id:
            raise ValueError("Unauthorized access to file")

        return file_metadata

    async def health_check(self) -> dict[str, Any]:
        """Check MinIO service health"""
        try:
            # Try to list buckets as a health check
            def _health_check():
                buckets = self.client.list_buckets()
                return len(list(buckets))

            bucket_count = await asyncio.to_thread(_health_check)

            return {
                "status": "healthy",
                "bucket_exists": await self._bucket_exists(),
                "bucket_count": bucket_count,
                "endpoint": settings.MINIO_ENDPOINT,
            }
        except Exception as e:
            logger.error(f"\tMinIO health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": settings.MINIO_ENDPOINT,
            }


# Global instance
minio_service = MinIOService()
