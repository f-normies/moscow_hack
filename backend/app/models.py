import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Dict, Any

from pydantic import EmailStr
from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel, Column


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    files: list["FileMetadata"] = Relationship(
        back_populates="owner", cascade_delete=True
    )
    dicom_studies: list["DICOMStudy"] = Relationship(
        back_populates="owner", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# File management models
class FileMetadataBase(SQLModel):
    filename: str = Field(max_length=255)
    original_name: str = Field(max_length=255)
    size: int = Field(ge=0)  # Size in bytes, must be >= 0
    content_type: str = Field(max_length=100)


class FileMetadataCreate(FileMetadataBase):
    pass


class FileMetadataUpdate(SQLModel):
    original_name: str | None = Field(default=None, max_length=255)


# Database model for file metadata
class FileMetadata(FileMetadataBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    minio_path: str = Field(max_length=500)  # Path in MinIO storage
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="files")


# Properties to return via API
class FileMetadataPublic(FileMetadataBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None


class FileMetadataWithUrl(FileMetadataPublic):
    download_url: str | None = None


class FilesPublic(SQLModel):
    data: list[FileMetadataPublic]
    count: int


# DICOM Study Models
class DICOMStudyBase(SQLModel):
    study_instance_uid: str = Field(max_length=255, unique=True)
    study_date: date | None = None
    study_time: time | None = None
    study_description: str | None = Field(default=None)
    patient_id: str | None = Field(default=None, max_length=255)
    modality: str | None = Field(default=None, max_length=50)
    institution_name: str | None = Field(default=None, max_length=255)


class DICOMStudyCreate(DICOMStudyBase):
    pass


class DICOMStudy(DICOMStudyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    file_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    # Relationships
    owner: User | None = Relationship(back_populates="dicom_studies")
    series: list["DICOMSeries"] = Relationship(
        back_populates="study", cascade_delete=True
    )


class DICOMStudyPublic(DICOMStudyBase):
    id: uuid.UUID
    file_count: int
    created_at: datetime
    series: list["DICOMSeriesPublic"] = []


# DICOM Series Models
class DICOMSeriesBase(SQLModel):
    series_instance_uid: str = Field(max_length=255, unique=True)
    series_number: int | None = None
    series_description: str | None = None
    modality: str | None = Field(default=None, max_length=50)
    body_part_examined: str | None = Field(default=None, max_length=100)


class DICOMSeriesCreate(DICOMSeriesBase):
    study_id: uuid.UUID


class DICOMSeries(DICOMSeriesBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    study_id: uuid.UUID = Field(
        foreign_key="dicomstudy.id", nullable=False, ondelete="CASCADE"
    )
    image_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    study: DICOMStudy | None = Relationship(back_populates="series")
    dicom_metadata: list["DICOMMetadata"] = Relationship(
        back_populates="series", cascade_delete=True
    )


class DICOMSeriesPublic(DICOMSeriesBase):
    id: uuid.UUID
    image_count: int
    created_at: datetime


# DICOM Metadata Models
class DICOMMetadataBase(SQLModel):
    instance_number: int | None = None
    rows: int | None = None
    columns: int | None = None
    pixel_spacing: str | None = Field(default=None, max_length=100)
    slice_thickness: Decimal | None = None
    window_center: Decimal | None = None
    window_width: Decimal | None = None
    extracted_metadata: Dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class DICOMMetadataCreate(DICOMMetadataBase):
    file_id: uuid.UUID
    series_id: uuid.UUID


class DICOMMetadata(DICOMMetadataBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID = Field(
        foreign_key="filemetadata.id", nullable=False, ondelete="CASCADE"
    )
    series_id: uuid.UUID = Field(
        foreign_key="dicomseries.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    file: FileMetadata | None = Relationship()
    series: DICOMSeries | None = Relationship(back_populates="dicom_metadata")


class DICOMMetadataPublic(DICOMMetadataBase):
    id: uuid.UUID
    file_id: uuid.UUID
    created_at: datetime
