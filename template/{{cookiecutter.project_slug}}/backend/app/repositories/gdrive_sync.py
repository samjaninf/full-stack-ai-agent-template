{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql %}
"""Google Drive sync repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.gdrive_sync import GoogleDriveFile, GoogleDriveFolder, GoogleDriveSyncLog
from app.schemas.gdrive import GoogleDriveFolderUpdate


async def get_folder(db: AsyncSession, folder_id: UUID, user_id: UUID | None = None) -> GoogleDriveFolder | None:
    """Get folder by ID for a specific user. If user_id is None, return folder without user filter (for background tasks)."""
    query = select(GoogleDriveFolder).where(GoogleDriveFolder.id == folder_id)
    if user_id is not None:
        query = query.where(GoogleDriveFolder.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_folder_list(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[GoogleDriveFolder], int]:
    """Get list of folders for a user with pagination."""
    query = (
        select(GoogleDriveFolder)
        .where(GoogleDriveFolder.user_id == user_id)
        .order_by(GoogleDriveFolder.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_active_folders(db: AsyncSession) -> list[GoogleDriveFolder]:
    """Get all active folders (for background tasks - no user filter)."""
    result = await db.execute(
        select(GoogleDriveFolder).where(GoogleDriveFolder.is_active.is_(True))
    )
    return list(result.scalars().all())


async def create_folder(
    db: AsyncSession,
    user_id: UUID,
    folder_id: str,
    folder_name: str,
    collection_name: str,
    sync_interval_minutes: int = 60,
) -> GoogleDriveFolder:
    """Create a new folder configuration for a user."""
    folder = GoogleDriveFolder(
        user_id=user_id,
        folder_id=folder_id,
        folder_name=folder_name,
        collection_name=collection_name,
        sync_interval_minutes=sync_interval_minutes,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder


async def update_folder(
    db: AsyncSession,
    folder: GoogleDriveFolder,
    data: GoogleDriveFolderUpdate,
) -> GoogleDriveFolder:
    """Update a folder configuration."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(folder, field, value)
    await db.flush()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder: GoogleDriveFolder) -> None:
    """Delete a folder and all related data."""
    await db.delete(folder)
    await db.flush()


async def get_file_by_gdrive_id(
    db: AsyncSession,
    folder_id: UUID,
    file_id: str,
) -> GoogleDriveFile | None:
    """Get a file by its Google Drive ID."""
    result = await db.execute(
        select(GoogleDriveFile).where(
            GoogleDriveFile.folder_id == folder_id,
            GoogleDriveFile.file_id == file_id,
        )
    )
    return result.scalar_one_or_none()


async def get_files_by_folder(
    db: AsyncSession,
    folder_id: UUID,
) -> list[GoogleDriveFile]:
    """Get all files for a folder."""
    result = await db.execute(
        select(GoogleDriveFile).where(GoogleDriveFile.folder_id == folder_id)
    )
    return list(result.scalars().all())


async def get_sync_logs(
    db: AsyncSession,
    folder_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[GoogleDriveSyncLog]:
    """Get sync logs for a folder."""
    result = await db.execute(
        select(GoogleDriveSyncLog)
        .where(GoogleDriveSyncLog.folder_id == folder_id)
        .order_by(GoogleDriveSyncLog.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


{%- elif cookiecutter.use_sqlite %}
"""Google Drive sync repository (SQLite sync)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.db.models.gdrive_sync import GoogleDriveFile, GoogleDriveFolder, GoogleDriveSyncLog
from app.schemas.gdrive import GoogleDriveFolderUpdate


def get_folder(db: DBSession, folder_id: str, user_id: str | None = None) -> GoogleDriveFolder | None:
    """Get folder by ID for a specific user. If user_id is None, return folder without user filter (for background tasks)."""
    query = db.query(GoogleDriveFolder).filter(GoogleDriveFolder.id == folder_id)
    if user_id is not None:
        query = query.filter(GoogleDriveFolder.user_id == user_id)
    return query.first()


def get_folder_list(
    db: DBSession,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[GoogleDriveFolder], int]:
    """Get list of folders for a user with pagination."""
    query = (
        select(GoogleDriveFolder)
        .where(GoogleDriveFolder.user_id == user_id)
        .order_by(GoogleDriveFolder.created_at.desc())
    )

    total = db.query(func.count(GoogleDriveFolder.id)).scalar() or 0

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all()), total


def get_active_folders(db: DBSession) -> list[GoogleDriveFolder]:
    """Get all active folders (for background tasks - no user filter)."""
    return (
        db.query(GoogleDriveFolder)
        .filter(GoogleDriveFolder.is_active.is_(True))
        .all()
    )


def create_folder(
    db: DBSession,
    user_id: str,
    folder_id: str,
    folder_name: str,
    collection_name: str,
    sync_interval_minutes: int = 60,
) -> GoogleDriveFolder:
    """Create a new folder configuration for a user."""
    folder = GoogleDriveFolder(
        user_id=user_id,
        folder_id=folder_id,
        folder_name=folder_name,
        collection_name=collection_name,
        sync_interval_minutes=sync_interval_minutes,
    )
    db.add(folder)
    db.flush()
    db.refresh(folder)
    return folder


def update_folder(
    db: DBSession,
    folder: GoogleDriveFolder,
    data: GoogleDriveFolderUpdate,
) -> GoogleDriveFolder:
    """Update a folder configuration."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(folder, field, value)
    db.flush()
    db.refresh(folder)
    return folder


def delete_folder(db: DBSession, folder: GoogleDriveFolder) -> None:
    """Delete a folder and all related data."""
    db.delete(folder)
    db.flush()


def get_file_by_gdrive_id(
    db: DBSession,
    folder_id: str,
    file_id: str,
) -> GoogleDriveFile | None:
    """Get a file by its Google Drive ID."""
    return (
        db.query(GoogleDriveFile)
        .filter(
            GoogleDriveFile.folder_id == folder_id,
            GoogleDriveFile.file_id == file_id,
        )
        .first()
    )


def get_files_by_folder(
    db: DBSession,
    folder_id: str,
) -> list[GoogleDriveFile]:
    """Get all files for a folder."""
    return (
        db.query(GoogleDriveFile)
        .filter(GoogleDriveFile.folder_id == folder_id)
        .all()
    )


def get_sync_logs(
    db: DBSession,
    folder_id: str,
    skip: int = 0,
    limit: int = 20,
) -> list[GoogleDriveSyncLog]:
    """Get sync logs for a folder."""
    return (
        db.query(GoogleDriveSyncLog)
        .filter(GoogleDriveSyncLog.folder_id == folder_id)
        .order_by(GoogleDriveSyncLog.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


{%- elif cookiecutter.use_mongodb %}
"""Google Drive sync repository (MongoDB)."""

from typing import Any

from app.db.models.gdrive_sync import GoogleDriveFile, GoogleDriveFolder, GoogleDriveSyncLog
from app.schemas.gdrive import GoogleDriveFolderUpdate


async def get_folder(folder_id: str, user_id: str | None = None) -> GoogleDriveFolder | None:
    """Get folder by ID for a specific user. If user_id is None, return folder without user filter (for background tasks)."""
    query = {"_id": folder_id}
    if user_id is not None:
        query["user_id"] = user_id
    return await GoogleDriveFolder.find_one(query)


async def get_folder_list(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[GoogleDriveFolder], int]:
    """Get list of folders for a user with pagination."""
    query = GoogleDriveFolder.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    folders = await query.to_list()

    total = await GoogleDriveFolder.find({"user_id": user_id}).count()

    return folders, total


async def get_active_folders() -> list[GoogleDriveFolder]:
    """Get all active folders (for background tasks - no user filter)."""
    return await GoogleDriveFolder.find({"is_active": True}).to_list()


async def create_folder(
    user_id: str,
    folder_id: str,
    folder_name: str,
    collection_name: str,
    sync_interval_minutes: int = 60,
) -> GoogleDriveFolder:
    """Create a new folder configuration for a user."""
    folder = GoogleDriveFolder(
        user_id=user_id,
        folder_id=folder_id,
        folder_name=folder_name,
        collection_name=collection_name,
        sync_interval_minutes=sync_interval_minutes,
    )
    await folder.create()
    return folder


async def update_folder(
    folder_id: str,
    user_id: str,
    data: GoogleDriveFolderUpdate,
) -> GoogleDriveFolder | None:
    """Update a folder configuration."""
    folder = await get_folder(folder_id, user_id)
    if not folder:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(folder, field, value)

    await folder.save()
    return folder


async def delete_folder(folder_id: str, user_id: str) -> None:
    """Delete a folder and all related data."""
    folder = await get_folder(folder_id, user_id)
    if folder:
        await folder.delete()

    # Also delete related files and logs
    await GoogleDriveFile.find({"folder_id": folder_id}).delete()
    await GoogleDriveSyncLog.find({"folder_id": folder_id}).delete()


async def get_file_by_gdrive_id(
    folder_id: str,
    file_id: str,
) -> GoogleDriveFile | None:
    """Get a file by its Google Drive ID."""
    return await GoogleDriveFile.find_one({
        "folder_id": folder_id,
        "file_id": file_id,
    })


async def get_files_by_folder(folder_id: str) -> list[GoogleDriveFile]:
    """Get all files for a folder."""
    return await GoogleDriveFile.find({"folder_id": folder_id}).to_list()


async def upsert_file(
    folder_id: str,
    file_id: str,
    data: dict[str, Any],
) -> GoogleDriveFile:
    """Upsert a file record."""
    existing = await get_file_by_gdrive_id(folder_id, file_id)

    if existing:
        for field, value in data.items():
            setattr(existing, field, value)
        await existing.save()
        return existing
    else:
        file = GoogleDriveFile(
            folder_id=folder_id,
            file_id=file_id,
            **data,
        )
        await file.create()
        return file


async def get_sync_logs(
    folder_id: str,
    skip: int = 0,
    limit: int = 20,
) -> list[GoogleDriveSyncLog]:
    """Get sync logs for a folder."""
    return (
        await GoogleDriveSyncLog.find({"folder_id": folder_id})
        .sort("started_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


{%- endif %}
{%- else %}
"""Google Drive sync repository - not configured."""
{%- endif %}
