{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}
"""Google Drive API schemas."""

from datetime import datetime
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from pydantic import BaseModel, Field


class GoogleDriveFolderCreate(BaseModel):
    """Request to create a new folder sync config."""

    folder_id: str = Field(..., description="Google Drive folder ID")
    folder_name: str = Field(..., min_length=1, max_length=512)
    collection_name: str = Field(..., min_length=1, max_length=255)
    sync_interval_minutes: int = Field(default=60, ge=15, le=1440)
    is_active: bool = Field(default=True)


class GoogleDriveFolderUpdate(BaseModel):
    """Update folder sync config."""

    folder_name: str | None = Field(None, min_length=1, max_length=512)
    collection_name: str | None = Field(None, min_length=1, max_length=255)
    sync_interval_minutes: int | None = Field(None, ge=15, le=1440)
    is_active: bool | None = None


class GoogleDriveFolderResponse(BaseModel):
    """Folder sync config response."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
    user_id: UUID
{%- else %}
    id: str
    user_id: str
{%- endif %}
    folder_id: str
    folder_name: str
    collection_name: str
    is_active: bool
    sync_interval_minutes: int
    last_sync_at: datetime | None
    last_sync_status: str | None
    created_at: datetime
    updated_at: datetime | None


class GoogleDriveFileResponse(BaseModel):
    """Synced file information."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
{%- else %}
    id: str
{%- endif %}
    file_id: str
    filename: str
    mime_type: str
    file_size: int | None
    checksum: str | None
    milvus_document_id: str | None
    last_synced_at: datetime | None
    ingestion_status: str
    error_message: str | None


class GoogleDriveSyncLogResponse(BaseModel):
    """Sync log response."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
    folder_id: UUID
{%- else %}
    id: str
    folder_id: str
{%- endif %}
    started_at: datetime
    completed_at: datetime | None
    status: str
    files_processed: int
    files_ingested: int
    files_failed: int
    error_message: str | None


class GoogleDriveSyncResponse(BaseModel):
    """Sync operation response."""

{%- if cookiecutter.use_postgresql %}
    folder_id: UUID
{%- else %}
    folder_id: str
{%- endif %}
    status: str
    files_processed: int
    files_ingested: int
    files_failed: int
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float
    error_message: str | None


class GoogleDriveFolderList(BaseModel):
    """Response for list of folders."""

    items: list[GoogleDriveFolderResponse]
    total: int


class GoogleDriveFileList(BaseModel):
    """Response for list of files."""

    items: list[GoogleDriveFileResponse]
    total: int


class GoogleDriveSyncLogList(BaseModel):
    """Response for list of sync logs."""

    items: list[GoogleDriveSyncLogResponse]
    total: int
{%- else %}
"""Google Drive schemas - not configured."""
{%- endif %}
