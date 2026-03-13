{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""Google Drive sync database models using SQLModel (PostgreSQL async)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class SyncStatus(StrEnum):
    """Sync status enum."""
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"
    SKIPPED = "skipped"


class FolderSyncStatus(StrEnum):
    """Folder sync status enum."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class GoogleDriveFolder(TimestampMixin, SQLModel, table=True):
    """Configuration for a Google Drive folder to sync."""

    __tablename__ = "gdrive_folders"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
        description="Owner user ID",
    )
    folder_id: str = Field(max_length=255, description="Google Drive folder ID")
    folder_name: str = Field(max_length=512, description="Display name")
    collection_name: str = Field(max_length=255, description="Target Milvus collection")
    is_active: bool = Field(default=True)
    sync_interval_minutes: int = Field(default=60)
    last_sync_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    last_sync_status: str | None = Field(
        default=None, sa_column=Column(String(50), nullable=True)
    )

    # Relationship to files
    files: list["GoogleDriveFile"] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sync_logs: list["GoogleDriveSyncLog"] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class GoogleDriveFile(SQLModel, table=True):
    """Track individual files from Google Drive."""

    __tablename__ = "gdrive_files"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    folder_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("gdrive_folders.id"), nullable=False),
    )
    file_id: str = Field(max_length=255, description="Google Drive file ID")
    filename: str = Field(max_length=512)
    mime_type: str = Field(max_length=100)
    file_size: int | None = Field(default=None)
    checksum: str | None = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    milvus_document_id: str | None = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    last_synced_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    ingestion_status: str = Field(
        default="pending", sa_column=Column(String(50), nullable=False)
    )
    error_message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # Relationship
    folder: "GoogleDriveFolder" = Relationship(back_populates="files")


class GoogleDriveSyncLog(SQLModel, table=True):
    """Log of sync operations."""

    __tablename__ = "gdrive_sync_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    folder_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("gdrive_folders.id"), nullable=False),
    )
    started_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    status: str = Field(max_length=50)
    files_processed: int = Field(default=0)
    files_ingested: int = Field(default=0)
    files_failed: int = Field(default=0)
    error_message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # Relationship
    folder: "GoogleDriveFolder" = Relationship(back_populates="sync_logs")


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""Google Drive sync database models using SQLModel (SQLite sync)."""

import json
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class SyncStatus(StrEnum):
    """Sync status enum."""
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"
    SKIPPED = "skipped"


class FolderSyncStatus(StrEnum):
    """Folder sync status enum."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class GoogleDriveFolder(TimestampMixin, SQLModel, table=True):
    """Configuration for a Google Drive folder to sync."""

    __tablename__ = "gdrive_folders"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    user_id: str = Field(
        sa_column=Column(String(36), ForeignKey("users.id"), nullable=False),
        description="Owner user ID",
    )
    folder_id: str = Field(max_length=255)
    folder_name: str = Field(max_length=512)
    collection_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    sync_interval_minutes: int = Field(default=60)
    last_sync_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    last_sync_status: str | None = Field(
        default=None, sa_column=Column(String(50), nullable=True)
    )

    files: list["GoogleDriveFile"] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sync_logs: list["GoogleDriveSyncLog"] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class GoogleDriveFile(SQLModel, table=True):
    """Track individual files from Google Drive."""

    __tablename__ = "gdrive_files"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    folder_id: str = Field(
        sa_column=Column(String(36), ForeignKey("gdrive_folders.id"), nullable=False),
    )
    file_id: str = Field(max_length=255)
    filename: str = Field(max_length=512)
    mime_type: str = Field(max_length=100)
    file_size: int | None = Field(default=None)
    checksum: str | None = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    milvus_document_id: str | None = Field(
        default=None, sa_column=Column(String(255), nullable=True)
    )
    last_synced_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    ingestion_status: str = Field(default="pending", sa_column=Column(String(50), nullable=False))
    error_message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    folder: "GoogleDriveFolder" = Relationship(back_populates="files")


class GoogleDriveSyncLog(SQLModel, table=True):
    """Log of sync operations."""

    __tablename__ = "gdrive_sync_logs"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    folder_id: str = Field(
        sa_column=Column(String(36), ForeignKey("gdrive_folders.id"), nullable=False),
    )
    started_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    status: str = Field(max_length=50, sa_column=Column(String(50), nullable=False))
    files_processed: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    files_ingested: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    files_failed: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    error_message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    folder: "GoogleDriveFolder" = Relationship(back_populates="sync_logs")


{%- elif cookiecutter.use_mongodb %}
"""Google Drive sync document models (MongoDB)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from beanie import Document, Link
from pydantic import Field


class SyncStatus(StrEnum):
    """Sync status enum."""
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"
    SKIPPED = "skipped"


class FolderSyncStatus(StrEnum):
    """Folder sync status enum."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class GoogleDriveFolder(Document):
    """Configuration for a Google Drive folder to sync."""

    user_id: str
    folder_id: str
    folder_name: str
    collection_name: str
    is_active: bool = True
    sync_interval_minutes: int = 60
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "gdrive_folders"
        indexes = ["folder_id", "is_active", "user_id"]


class GoogleDriveFile(Document):
    """Track individual files from Google Drive."""

    folder_id: str
    file_id: str
    filename: str
    mime_type: str
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    milvus_document_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    ingestion_status: str = "pending"
    error_message: Optional[str] = None

    class Settings:
        name = "gdrive_files"
        indexes = ["file_id", "folder_id"]


class GoogleDriveSyncLog(Document):
    """Log of sync operations."""

    folder_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    files_processed: int = 0
    files_ingested: int = 0
    files_failed: int = 0
    error_message: Optional[str] = None

    class Settings:
        name = "gdrive_sync_logs"
        indexes = ["folder_id", "started_at"]


{%- endif %}
