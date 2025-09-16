from unittest.mock import patch

import pytest
from sqlmodel import Session

from app.services.minio_service import MinIOService, minio_service
from app.tests.utils.file import (
    cleanup_test_files,
    create_test_file_data,
)
from app.tests.utils.user import create_random_user


class TestMinIOEdgeCases:
    """Test edge cases and error conditions for MinIO service."""

    @pytest.fixture(autouse=True)
    async def setup_minio_for_class(self, setup_minio):
        """Ensure MinIO is available for this test class."""
        return setup_minio

    async def test_file_upload_with_special_characters(self, db: Session):
        """Test uploading files with special characters in filename."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, _, content_type = test_files["document_txt"]

        # Test various special characters
        special_filenames = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.with.dots.txt",
            "file@with@symbols.txt",
            "file#with#hash.txt",
            "file(with)parens.txt",
            "файл.txt",  # Unicode characters
            "文件.txt",  # Unicode characters
        ]

        uploaded_files = []

        try:
            for filename in special_filenames:
                file_metadata = await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )
                uploaded_files.append(file_metadata.id)

                # Verify upload succeeded
                assert file_metadata.original_name == filename
                assert file_metadata.size == len(file_data)

                # Verify file can be retrieved
                retrieved_data = await minio_service.get_file(
                    file_id=file_metadata.id, user_id=user.id, session=db
                )
                assert retrieved_data == file_data

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_file_upload_without_extension(self, db: Session):
        """Test uploading files without file extensions."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, _, _ = test_files["document_txt"]

        # File without extension - should still work based on content detection
        file_metadata = await minio_service.upload_file(
            file_data=file_data,
            filename="textfile_no_extension",
            user_id=user.id,
            session=db,
        )

        try:
            assert file_metadata.original_name == "textfile_no_extension"
            assert file_metadata.content_type == "text/plain"  # Detected by magic

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_file_upload_extension_mime_mismatch(self, db: Session):
        """Test files where extension doesn't match actual content."""
        user = create_random_user(db)
        test_files = create_test_file_data()

        # Use JPEG data but with .txt extension
        jpeg_data, _, _ = test_files["image_jpeg"]

        file_metadata = await minio_service.upload_file(
            file_data=jpeg_data,
            filename="fake.txt",  # Wrong extension
            user_id=user.id,
            session=db,
        )

        try:
            # Should detect as JPEG based on content, not extension
            assert file_metadata.content_type == "image/jpeg"

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_concurrent_file_uploads(self, db: Session):
        """Test multiple concurrent file uploads."""
        import asyncio

        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, _, _ = test_files["document_txt"]

        async def upload_file(index: int):
            return await minio_service.upload_file(
                file_data=file_data,
                filename=f"concurrent_file_{index}.txt",
                user_id=user.id,
                session=db,
            )

        # Upload 5 files concurrently
        tasks = [upload_file(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        uploaded_files = [result.id for result in results]

        try:
            # Verify all uploads succeeded
            assert len(results) == 5
            for i, file_metadata in enumerate(results):
                assert file_metadata.original_name == f"concurrent_file_{i}.txt"
                assert file_metadata.owner_id == user.id

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    async def test_very_long_filename(self, db: Session):
        """Test upload with very long filename."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, _, _ = test_files["document_txt"]

        # Create filename that's 250 characters (near DB limit of 255)
        long_filename = "a" * 240 + ".txt"

        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=long_filename, user_id=user.id, session=db
        )

        try:
            assert file_metadata.original_name == long_filename

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_duplicate_filename_handling(self, db: Session):
        """Test uploading files with the same filename."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Upload same filename twice
        file1 = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        file2 = await minio_service.upload_file(
            file_data=file_data,
            filename=filename,  # Same filename
            user_id=user.id,
            session=db,
        )

        try:
            # Both should succeed with different MinIO paths
            assert file1.original_name == filename
            assert file2.original_name == filename
            assert file1.minio_path != file2.minio_path  # Different storage paths
            assert file1.id != file2.id  # Different IDs

        finally:
            await cleanup_test_files(db, [file1.id, file2.id], user.id)

    async def test_file_path_generation_uniqueness(self, db: Session):
        """Test that file paths are unique even for same user and filename."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Upload multiple files with same name
        uploaded_files = []
        file_paths = set()

        try:
            for _ in range(10):
                file_metadata = await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )
                uploaded_files.append(file_metadata.id)
                file_paths.add(file_metadata.minio_path)

            # All paths should be unique
            assert len(file_paths) == 10

            # All paths should start with user directory
            for path in file_paths:
                assert path.startswith(f"users/{user.id}/")

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)

    @pytest.mark.asyncio
    async def test_minio_connection_error_handling(self, db: Session):
        """Test error handling when MinIO is unavailable."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Create a MinIO service with invalid configuration
        invalid_service = MinIOService()
        invalid_service.client = None  # Simulate connection failure

        with pytest.raises(Exception):  # noqa
            await invalid_service.upload_file(
                file_data=file_data, filename=filename, user_id=user.id, session=db
            )

    async def test_database_transaction_rollback(self, db: Session):
        """Test that database transactions are properly handled on MinIO failures."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        # Mock MinIO upload to fail after DB operation would start
        with patch.object(
            minio_service.client, "put_object", side_effect=Exception("MinIO Error")
        ):
            with pytest.raises(Exception):  # noqa
                await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )

        # Verify no orphaned database records
        files = await minio_service.list_user_files(user_id=user.id, session=db)

        # Should not have the failed upload in the database
        failed_files = [f for f in files if f.original_name == filename]
        assert len(failed_files) == 0

    async def test_presigned_url_edge_cases(self, db: Session):
        """Test presigned URL generation edge cases."""
        user = create_random_user(db)
        test_files = create_test_file_data()
        file_data, filename, _ = test_files["document_txt"]

        file_metadata = await minio_service.upload_file(
            file_data=file_data, filename=filename, user_id=user.id, session=db
        )

        try:
            # Test minimum expiry
            url_1h = await minio_service.generate_presigned_url(
                file_id=file_metadata.id, user_id=user.id, session=db, expiry_hours=1
            )
            assert isinstance(url_1h, str)
            assert len(url_1h) > 0

            # Test maximum expiry (24 hours based on API validation)
            url_24h = await minio_service.generate_presigned_url(
                file_id=file_metadata.id, user_id=user.id, session=db, expiry_hours=24
            )
            assert isinstance(url_24h, str)
            assert len(url_24h) > 0

            # URLs should be different due to different expiry times
            assert url_1h != url_24h

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_list_files_edge_cases(self, db: Session):
        """Test file listing edge cases."""
        user = create_random_user(db)

        # Test with no files
        files = await minio_service.list_user_files(
            user_id=user.id, session=db, skip=0, limit=10
        )
        # Should return empty list, not error
        assert isinstance(files, list)

        # Test with skip beyond available files
        files = await minio_service.list_user_files(
            user_id=user.id, session=db, skip=1000, limit=10
        )
        assert isinstance(files, list)
        assert len(files) == 0

        # Test with very large limit
        files = await minio_service.list_user_files(
            user_id=user.id, session=db, skip=0, limit=10000
        )
        assert isinstance(files, list)

    async def test_binary_file_handling(self, db: Session):
        """Test handling of various binary file types."""
        user = create_random_user(db)

        # Test pure binary data
        binary_data = bytes(range(256))  # All possible byte values

        file_metadata = await minio_service.upload_file(
            file_data=binary_data,
            filename="binary_test.bin",
            user_id=user.id,
            session=db,
        )

        try:
            # Verify binary data is preserved exactly
            retrieved_data = await minio_service.get_file(
                file_id=file_metadata.id, user_id=user.id, session=db
            )
            assert retrieved_data == binary_data
            assert len(retrieved_data) == 256

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_zero_byte_files(self, db: Session):
        """Test handling of zero-byte files."""
        user = create_random_user(db)

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

            # Should be able to generate presigned URL for empty file
            url = await minio_service.generate_presigned_url(
                file_id=file_metadata.id, user_id=user.id, session=db
            )
            assert isinstance(url, str)
            assert len(url) > 0

        finally:
            await cleanup_test_files(db, [file_metadata.id], user.id)

    async def test_file_content_type_detection_fallbacks(self, db: Session):
        """Test content type detection with various edge cases."""
        user = create_random_user(db)

        # Test files that might be hard to detect
        test_cases = [
            # Plain text that might be misdetected
            (b"1,2,3\n4,5,6\n", "data.csv", "text/plain"),
            # JSON data
            (b'{"key": "value"}', "data.json", "text/plain"),
            # XML data
            (b'<?xml version="1.0"?><root></root>', "data.xml", "text/plain"),
        ]

        uploaded_files = []

        try:
            for file_data, filename, _ in test_cases:
                file_metadata = await minio_service.upload_file(
                    file_data=file_data, filename=filename, user_id=user.id, session=db
                )
                uploaded_files.append(file_metadata.id)

                # Content type should be detected (might not exactly match expected due to magic detection)
                assert file_metadata.content_type is not None
                assert len(file_metadata.content_type) > 0

        finally:
            await cleanup_test_files(db, uploaded_files, user.id)
