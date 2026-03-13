{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}
"""Google Drive management routes."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from app.api.deps import GoogleDriveIngestionSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentUser
{%- endif %}
from app.schemas.gdrive import (
    GoogleDriveFileList,
    GoogleDriveFolderCreate,
    GoogleDriveFolderList,
    GoogleDriveFolderResponse,
    GoogleDriveFolderUpdate,
    GoogleDriveSyncLogList,
    GoogleDriveSyncResponse,
)

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


async def _get_user_id(current_user: CurrentUser) -> UUID:
    """Extract user ID from current user."""
    return current_user.id


{%- elif cookiecutter.use_sqlite %}


def _get_user_id(current_user: CurrentUser) -> str:
    """Extract user ID from current user."""
    return str(current_user.id)


{%- elif cookiecutter.use_mongodb %}


async def _get_user_id(current_user: CurrentUser) -> str:
    """Extract user ID from current user."""
    return str(current_user.id)


{%- endif %}

{%- if cookiecutter.use_postgresql %}


@router.post("/folders", response_model=GoogleDriveFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: GoogleDriveFolderCreate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Configure a new Google Drive folder for sync."""
    user_id = _get_user_id(current_user)
    folder = await service.create_folder(user_id, data)
    return folder


@router.get("/folders", response_model=GoogleDriveFolderList)
async def list_folders(
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all configured Google Drive folders for the current user."""
    user_id = _get_user_id(current_user)
    folders, total = await service.list_folders(user_id, skip=skip, limit=limit)
    return GoogleDriveFolderList(
        items=folders,
        total=total,
    )


@router.get("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def get_folder(
    folder_id: UUID,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Get folder details with sync status."""
    user_id = _get_user_id(current_user)
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.patch("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def update_folder(
    folder_id: UUID,
    data: GoogleDriveFolderUpdate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Update folder sync configuration."""
    user_id = _get_user_id(current_user)
    folder = await service.update_folder(folder_id, user_id, data)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Remove a Google Drive folder sync configuration."""
    user_id = _get_user_id(current_user)
    await service.delete_folder(folder_id, user_id)


@router.post("/folders/{folder_id}/sync", response_model=GoogleDriveSyncResponse)
async def trigger_sync(
    folder_id: UUID,
    background_tasks: BackgroundTasks,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    force: bool = Query(False),
):
    """Manually trigger a sync for a folder."""
    user_id = _get_user_id(current_user)
    result = await service.trigger_sync(folder_id, user_id, force)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return result


@router.get("/folders/{folder_id}/files", response_model=GoogleDriveFileList)
async def list_synced_files(
    folder_id: UUID,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all files synced from a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    files, total = await service.list_files(folder_id, skip=skip, limit=limit)
    return GoogleDriveFileList(
        items=files,
        total=total,
    )


@router.get("/folders/{folder_id}/logs", response_model=GoogleDriveSyncLogList)
async def get_sync_logs(
    folder_id: UUID,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get sync history for a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    logs, total = await service.get_sync_logs(folder_id, skip=skip, limit=limit)
    return GoogleDriveSyncLogList(
        items=logs,
        total=total,
    )


{%- elif cookiecutter.use_sqlite %}


@router.post("/folders", response_model=GoogleDriveFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: GoogleDriveFolderCreate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Configure a new Google Drive folder for sync."""
    user_id = _get_user_id(current_user)
    folder = service.create_folder(user_id, data)
    return folder


@router.get("/folders", response_model=GoogleDriveFolderList)
async def list_folders(
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all configured Google Drive folders for the current user."""
    user_id = _get_user_id(current_user)
    folders, total = service.list_folders(user_id, skip=skip, limit=limit)
    return GoogleDriveFolderList(
        items=folders,
        total=total,
    )


@router.get("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def get_folder(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Get folder details with sync status."""
    user_id = _get_user_id(current_user)
    folder = service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.patch("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def update_folder(
    folder_id: str,
    data: GoogleDriveFolderUpdate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Update folder sync configuration."""
    user_id = _get_user_id(current_user)
    folder = service.update_folder(folder_id, user_id, data)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Remove a Google Drive folder sync configuration."""
    user_id = _get_user_id(current_user)
    service.delete_folder(folder_id, user_id)


@router.post("/folders/{folder_id}/sync", response_model=GoogleDriveSyncResponse)
async def trigger_sync(
    folder_id: str,
    background_tasks: BackgroundTasks,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    force: bool = Query(False),
):
    """Manually trigger a sync for a folder."""
    user_id = _get_user_id(current_user)
    result = service.trigger_sync(folder_id, user_id, force)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return result


@router.get("/folders/{folder_id}/files", response_model=GoogleDriveFileList)
async def list_synced_files(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all files synced from a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    files, total = service.list_files(folder_id, skip=skip, limit=limit)
    return GoogleDriveFileList(
        items=files,
        total=total,
    )


@router.get("/folders/{folder_id}/logs", response_model=GoogleDriveSyncLogList)
async def get_sync_logs(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get sync history for a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    logs, total = service.get_sync_logs(folder_id, skip=skip, limit=limit)
    return GoogleDriveSyncLogList(
        items=logs,
        total=total,
    )


{%- elif cookiecutter.use_mongodb %}


@router.post("/folders", response_model=GoogleDriveFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: GoogleDriveFolderCreate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Configure a new Google Drive folder for sync."""
    user_id = _get_user_id(current_user)
    folder = await service.create_folder(user_id, data)
    return folder


@router.get("/folders", response_model=GoogleDriveFolderList)
async def list_folders(
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all configured Google Drive folders for the current user."""
    user_id = _get_user_id(current_user)
    folders, total = await service.list_folders(user_id, skip=skip, limit=limit)
    return GoogleDriveFolderList(
        items=folders,
        total=total,
    )


@router.get("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def get_folder(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Get folder details with sync status."""
    user_id = _get_user_id(current_user)
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.patch("/folders/{folder_id}", response_model=GoogleDriveFolderResponse)
async def update_folder(
    folder_id: str,
    data: GoogleDriveFolderUpdate,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Update folder sync configuration."""
    user_id = _get_user_id(current_user)
    folder = await service.update_folder(folder_id, user_id, data)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Remove a Google Drive folder sync configuration."""
    user_id = _get_user_id(current_user)
    await service.delete_folder(folder_id, user_id)


@router.post("/folders/{folder_id}/sync", response_model=GoogleDriveSyncResponse)
async def trigger_sync(
    folder_id: str,
    background_tasks: BackgroundTasks,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    force: bool = Query(False),
):
    """Manually trigger a sync for a folder."""
    user_id = _get_user_id(current_user)
    result = await service.trigger_sync(folder_id, user_id, force)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return result


@router.get("/folders/{folder_id}/files", response_model=GoogleDriveFileList)
async def list_synced_files(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all files synced from a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    files, total = await service.list_files(folder_id, skip=skip, limit=limit)
    return GoogleDriveFileList(
        items=files,
        total=total,
    )


@router.get("/folders/{folder_id}/logs", response_model=GoogleDriveSyncLogList)
async def get_sync_logs(
    folder_id: str,
    service: GoogleDriveIngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get sync history for a folder."""
    user_id = _get_user_id(current_user)
    # Verify user owns the folder first
    folder = await service.get_folder(folder_id, user_id)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    logs, total = await service.get_sync_logs(folder_id, skip=skip, limit=limit)
    return GoogleDriveSyncLogList(
        items=logs,
        total=total,
    )


{%- endif %}
{%- else %}
"""Google Drive routes - not configured."""
{%- endif %}
