import uuid

import pytest
from sqlmodel import Session

from app.services.minio_service import minio_service
from app.tests.utils.file import (
    cleanup_test_files,
    create_invalid_file_data,
    create_large_file_data,
    create_test_file_data,
    get_allowed_file_types_by_category,
)
from app.tests.utils.user import create_random_user


class TestMinIOService:
    """Test MinIO service functionality with real MinIO instance."""

    @pytest.fixture(autouse=True)
    async def setup_minio_for_class(self, setup_minio):
        """Ensure MinIO is available for this test class."""
        return setup_minio

    async def test_health_check(self):
        """Test MinIO service health check."""
        health = await minio_service.health_check()

        assert health["status"] == "healthy"
        assert health["bucket_exists"] is True
        assert "endpoint" in health
        assert "bucket_count" in health

    async def test_upload_and_retrieve_file(self, db: Session):
        """Test basic file upload and retrieval cycle."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, expected_content_type = test_files["document_txt"]

        # Upload file
        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        # Verify upload response
        assert file_metadata.original_name == filename
        assert file_metadata.size == len(file_data)
        assert file_metadata.content_type == expected_content_type
        assert file_metadata.owner_id == user.id
        assert file_metadata.minio_path.startswith(f"users/{user.id}/")

        # Retrieve file
        retrieved_data = await minio_service.get_file(
            file_id=file_metadata.id, user_id=user.id, session=db
        )

        # Verify retrieved data matches original
        assert retrieved_data == file_data

        # Cleanup
        await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_upload_all_supported_file_types(self, db: Session):
        """Test uploading all supported file types."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        uploaded_files = []

        try:
            for _, (
                file_data,
                filename,
                _,
            ) in test_files.items():
                # Upload file
                file_metadata = await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )
                uploaded_files.append(file_metadata.id)

                # Verify file metadata
                assert file_metadata.original_name == filename
                assert file_metadata.size == len(file_data)
                assert file_metadata.owner_id == user.id

                # Verify file can be retrieved
                retrieved_data = await minio_service.get_file(
                    file_id=file_metadata.id, user_id=user.id, session=db
                )
                assert retrieved_data == file_data

        finally:
            # Cleanup all uploaded files
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_file_type_validation_allowed(self, db: Session):
        """Test that allowed file types are accepted."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        allowed_types = get_allowed_file_types_by_category()

        # Test a few key file types from different categories
        test_cases = [
            ("image_jpeg", "image"),
            ("document_pdf", "document"),
            ("audio_mp3", "audio"),
            ("model_obj", "other"),
        ]

        uploaded_files = []

        try:
            for file_key, _ in test_cases:
                file_data, filename, expected_content_type = test_files[file_key]

                # Upload should succeed
                file_metadata = await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )
                uploaded_files.append(file_metadata.id)

                # Verify content type is in some allowed category (magic detection may vary)
                all_allowed_types = []
                for cat_types in allowed_types.values():
                    all_allowed_types.extend(cat_types)
                assert file_metadata.content_type in all_allowed_types

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_file_type_validation_rejected(self, db: Session):
        """Test that disallowed file types are rejected."""
        user = create_random_user(db)
        invalid_files = create_invalid_file_data()

        for _, (file_data, filename) in invalid_files.items():
            with pytest.raises(ValueError, match="File type not allowed"):
                await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )

    async def test_file_size_limit_enforcement(self, db: Session):
        """Test that file size limits are enforced."""
        user = create_random_user(db)

        # Create a file larger than the general limit (100MB)
        large_file_data = create_large_file_data(101)  # 101MB

        with pytest.raises(ValueError, match="File too large"):
            await minio_service.upload_file(
                file_data=large_file_data,
                filename="large_file.txt",
                user_id=user.id,
                session=db,
            )

    async def test_generate_presigned_url(self, db: Session):
        """Test presigned URL generation."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Upload file
        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        try:
            # Generate presigned URL
            url = await minio_service.generate_presigned_url(
                file_id=file_metadata.id, user_id=user.id, session=db, expiry_hours=1
            )

            # Verify URL is a valid string and contains expected elements
            assert isinstance(url, str)
            assert len(url) > 0
            assert "http" in url.lower()

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_delete_file(self, db: Session):
        """Test file deletion from both MinIO and database."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Upload file
        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        # Verify file exists
        retrieved_data = await minio_service.get_file(
            file_id=file_metadata.id, user_id=user.id, session=db
        )
        assert retrieved_data == file_data

        # Delete file
        await minio_service.delete_file(
            file_id=file_metadata.id, user_id=user.id, session=db
        )

        # Verify file no longer exists
        with pytest.raises(ValueError, match="File not found"):
            await minio_service.get_file(
                file_id=file_metadata.id, user_id=user.id, session=db
            )

    async def test_list_user_files(self, db: Session):
        """Test listing files for a user."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        uploaded_files = []

        try:
            # Upload multiple files
            for i, (_, (file_data, filename, _)) in enumerate(
                list(test_files.items())[:3]
            ):
                unique_filename = f"{i}_{filename}"
                file_metadata = await minio_service.upload_file(
                    file_data=file_data,
                    filename=unique_filename,
                    user_id=user.id,
                    session=db,
                )
                uploaded_files.append(file_metadata.id)

            # List files
            files = await minio_service.list_user_files(
                user_id=user.id, session=db, skip=0, limit=10
            )

            # Verify we get the uploaded files
            assert len(files) >= 3
            file_ids = [f.id for f in files]
            for uploaded_id in uploaded_files:
                assert uploaded_id in file_ids

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_list_user_files_pagination(self, db: Session):
        """Test file listing pagination."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        uploaded_files = []

        try:
            # Upload 5 files
            for i in range(5):
                file_data, filename, _ = test_files["document_txt"]
                unique_filename = f"paginate_{i}_{filename}"
                file_metadata = await minio_service.upload_file(
                    file_data=file_data,
                    filename=unique_filename,
                    user_id=user.id,
                    session=db,
                )
                uploaded_files.append(file_metadata.id)

            # Test pagination
            first_page = await minio_service.list_user_files(
                user_id=user.id, session=db, skip=0, limit=3
            )

            second_page = await minio_service.list_user_files(
                user_id=user.id, session=db, skip=3, limit=3
            )

            # Verify pagination works
            assert len(first_page) == 3
            assert len(second_page) >= 2  # At least the remaining 2 files

            # Verify no overlap
            first_page_ids = {f.id for f in first_page}
            second_page_ids = {f.id for f in second_page}
            assert len(first_page_ids.intersection(second_page_ids)) == 0

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_user_permission_isolation(self, db: Session):
        """Test that users can only access their own files."""
        user1 = create_random_user(db)
        user2 = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # User 1 uploads file
        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user1.id, session=db
        )

        try:
            # User 2 should not be able to access user 1's file
            with pytest.raises(ValueError, match="Unauthorized access to file"):
                await minio_service.get_file(
                    file_id=file_metadata.id, user_id=user2.id, session=db
                )

            with pytest.raises(ValueError, match="Unauthorized access to file"):
                await minio_service.generate_presigned_url(
                    file_id=file_metadata.id, user_id=user2.id, session=db
                )

            with pytest.raises(ValueError, match="Unauthorized access to file"):
                await minio_service.delete_file(
                    file_id=file_metadata.id, user_id=user2.id, session=db
                )

        finally:
            await cleanup_test_files(db, [file_metadata.id], user1.id)

    async def test_get_file_info(self, db: Session):
        """Test getting file metadata."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, expected_content_type = test_files["image_jpeg"]

        # Upload file
        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        try:
            # Get file info
            retrieved_metadata = await minio_service.get_file_info(
                file_id=file_metadata.id, user_id=user.id, session=db
            )

            # Verify metadata matches
            assert retrieved_metadata.id == file_metadata.id
            assert retrieved_metadata.original_name == filename
            assert retrieved_metadata.size == len(file_data)
            assert retrieved_metadata.content_type == expected_content_type
            assert retrieved_metadata.owner_id == user.id

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_file_not_found_errors(self, db: Session):
        """Test proper error handling for non-existent files."""
        user = create_random_user(db)
        non_existent_id = uuid.uuid4()

        # Test all methods that should raise "File not found"
        with pytest.raises(ValueError, match="File not found"):
            await minio_service.get_file(
                file_id=non_existent_id, user_id=user.id, session=db
            )

        with pytest.raises(ValueError, match="File not found"):
            await minio_service.get_file_info(
                file_id=non_existent_id, user_id=user.id, session=db
            )

        with pytest.raises(ValueError, match="File not found"):
            await minio_service.generate_presigned_url(
                file_id=non_existent_id, user_id=user.id, session=db
            )

        with pytest.raises(ValueError, match="File not found"):
            await minio_service.delete_file(
                file_id=non_existent_id, user_id=user.id, session=db
            )

    async def test_empty_file_upload(self, db: Session):
        """Test uploading empty files."""
        user = create_random_user(db)

        # Empty file should be allowed
        file_metadata = await minio_service.upload_file(
            file_data=b"", filename="empty.txt", user_id=user.id, session=db
        )

        try:
            assert file_metadata.size == 0

            # Should be able to retrieve empty file
            retrieved_data = await minio_service.get_file(
                file_id=file_metadata.id, user_id=user.id, session=db
            )
            assert retrieved_data == b""

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)
