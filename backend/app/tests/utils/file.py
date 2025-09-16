import io
import uuid

from fastapi import UploadFile
from sqlmodel import Session

from app.models import FileMetadata
from app.services.minio_service import minio_service
from app.tests.utils.user import create_random_user
from app.tests.utils.utils import random_lower_string


def create_test_file_data() -> dict[str, tuple[bytes, str, str]]:
    """Create test file data for different file types and categories.

    Returns:
        Dict mapping category to (file_data, filename, content_type)
    """
    return {
        # Image files
        "image_jpeg": (
            # Minimal valid JPEG header (1x1 pixel)
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
            b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01"
            b"\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9",
            "test_image.jpg",
            "image/jpeg",
        ),
        "image_png": (
            # Minimal valid PNG header (1x1 pixel)
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13"
            b"\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```"
            b"\x00\x00\x00\x04\x00\x01\xddZ[\xe5\x00\x00\x00\x00IEND\xaeB`\x82",
            "test_image.png",
            "image/png",
        ),
        # Document files
        "document_pdf": (
            # Minimal valid PDF
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages"
            b"/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox"
            b"[0 0 612 792]>>endobj xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n"
            b"0000000053 00000 n \n0000000125 00000 n \ntrailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n183\n%%EOF",
            "test_document.pdf",
            "application/pdf",
        ),
        "document_txt": (
            b"This is a test text file for MinIO integration testing.",
            "test_document.txt",
            "text/plain",
        ),
        # Video files
        "video_mp4": (
            # Minimal MP4 header
            b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08free"
            b"\x00\x00\x00\x28mdat\x00\x00\x00\x00",
            "test_video.mp4",
            "video/mp4",
        ),
        # Audio files
        "audio_mp3": (
            # Minimal MP3 header
            b"\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            "test_audio.mp3",
            "audio/mpeg",
        ),
        # 3D Model files (using extension-based detection)
        "model_obj": (
            b"# Test OBJ file\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n",
            "test_model.obj",
            "model/obj",  # Will be detected by extension
        ),
        "model_stl": (
            b"solid test\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\n"
            b"vertex 0 1 0\nendloop\nendfacet\nendsolid test\n",
            "test_model.stl",
            "model/stl",
        ),
    }


def create_large_file_data(size_mb: int) -> bytes:
    """Create large file data for size limit testing."""
    return b"0" * (size_mb * 1024 * 1024)


def create_invalid_file_data() -> dict[str, tuple[bytes, str]]:
    """Create invalid file data for rejection testing."""
    return {
        "executable": (
            b"\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00",  # ELF header
            "malware.exe",
        ),
        "script": (b'#!/bin/bash\necho "potentially dangerous script"', "script.sh"),
        "unknown": (
            b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
            "unknown.bin",
        ),
    }


def create_upload_file(
    file_data: bytes, filename: str, content_type: str = None
) -> UploadFile:
    """Create an UploadFile object for testing."""
    file_obj = io.BytesIO(file_data)
    return UploadFile(
        filename=filename,
        file=file_obj,
        size=len(file_data),
        headers={"content-type": content_type} if content_type else {},
    )


async def create_random_file_metadata(
    db: Session, user_id: uuid.UUID = None
) -> FileMetadata:
    """Create a random file metadata record in the database and MinIO."""
    if user_id is None:
        user = create_random_user(db)
        user_id = user.id

    # Use a small test file
    test_files = create_test_file_data()
    file_data, filename, content_type = test_files["document_txt"]

    # Add random suffix to filename to avoid conflicts
    name_parts = filename.split(".")
    if len(name_parts) > 1:
        random_filename = f"{name_parts[0]}_{random_lower_string()}.{name_parts[1]}"
    else:
        random_filename = f"{filename}_{random_lower_string()}"

    # Upload file using MinIO service
    file_metadata = await minio_service.upload_file(
        file_data=file_data, filename=random_filename, user_id=user_id, session=db
    )

    return file_metadata


async def cleanup_test_files(
    db: Session, file_ids: list[uuid.UUID], user_id: uuid.UUID
) -> None:
    """Clean up test files from MinIO and database."""
    for file_id in file_ids:
        try:
            await minio_service.delete_file(file_id, user_id, db)
        except Exception:
            # Ignore cleanup errors
            pass


def get_file_category_limits() -> dict[str, int]:
    """Get file size limits by category for testing."""
    from app.core.config import settings

    return {
        "image": settings.MAX_IMAGE_SIZE,
        "document": settings.MAX_DOCUMENT_SIZE,
        "video": settings.MAX_VIDEO_SIZE,
        "audio": settings.MAX_AUDIO_SIZE,
        "other": settings.MAX_OTHER_SIZE,
    }


def get_allowed_file_types_by_category() -> dict[str, list[str]]:
    """Get allowed file types by category for testing."""
    from app.core.config import parse_file_types, settings

    return {
        "image": parse_file_types(settings.ALLOWED_IMAGE_TYPES),
        "document": parse_file_types(settings.ALLOWED_DOCUMENT_TYPES),
        "video": parse_file_types(settings.ALLOWED_VIDEO_TYPES),
        "audio": parse_file_types(settings.ALLOWED_AUDIO_TYPES),
        "other": parse_file_types(settings.ALLOWED_OTHER_TYPES),
    }
