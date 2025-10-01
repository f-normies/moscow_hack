"""
Database models for inference worker.
These are minimal copies of backend models needed for Celery tasks.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel, Column


class InferenceModel(SQLModel, table=True):
    """Inference model - minimal version for worker"""
    model_config = {"protected_namespaces": ()}  # Allow model_ prefix

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    model_type: str = Field(max_length=50)  # "multitalent", "nnunet"
    onnx_path: str = Field(max_length=500)
    config_path: str = Field(max_length=500)
    modality: str = Field(max_length=50)  # "CT", "MRI", "PET"
    description: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InferenceJob(SQLModel, table=True):
    """Inference job - minimal version for worker"""
    model_config = {"protected_namespaces": ()}  # Allow model_ prefix

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    study_id: uuid.UUID
    series_id: uuid.UUID | None = None
    model_id: uuid.UUID
    status: str = Field(max_length=50)  # pending, running, completed, failed, cancelled
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    error_message: str | None = None
    parameters: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    result_path: str | None = Field(default=None, max_length=500)
    metrics: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class SegmentationResult(SQLModel, table=True):
    """Segmentation result - minimal version for worker"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID
    output_format: str = Field(max_length=50)  # "nifti", "dicom-seg"
    file_path: str = Field(max_length=500)
    classes: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    result_metadata: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FileMetadata(SQLModel, table=True):
    """File metadata - minimal version for worker"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str = Field(max_length=255)
    original_name: str = Field(max_length=255)
    size: int = Field(ge=0)
    content_type: str = Field(max_length=100)
    minio_path: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    owner_id: uuid.UUID


class DICOMSeries(SQLModel, table=True):
    """DICOM series - minimal version for worker"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    study_id: uuid.UUID
    series_instance_uid: str = Field(max_length=255, unique=True)
    series_number: int | None = None
    series_description: str | None = None
    modality: str | None = Field(default=None, max_length=50)
    body_part_examined: str | None = Field(default=None, max_length=100)
    image_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DICOMMetadata(SQLModel, table=True):
    """DICOM metadata - minimal version for worker"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID
    series_id: uuid.UUID
    instance_number: int | None = None
    rows: int | None = None
    columns: int | None = None
    pixel_spacing: str | None = Field(default=None, max_length=100)
    slice_thickness: Decimal | None = None
    window_center: Decimal | None = None
    window_width: Decimal | None = None
    extracted_metadata: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
