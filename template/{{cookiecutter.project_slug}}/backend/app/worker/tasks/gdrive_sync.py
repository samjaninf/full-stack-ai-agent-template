{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database and cookiecutter.use_milvus and (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
"""Google Drive scheduled tasks for folder synchronization.

This module provides background tasks for syncing Google Drive folders
to the RAG pipeline.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# === Celery Task ===
{% if cookiecutter.use_celery %}
from celery import shared_task


@shared_task(bind=True, max_retries=3)
def sync_gdrive_folder(
    self,
    folder_id: str,
    force_full: bool = False,
) -> dict[str, Any]:
    """Sync a specific Google Drive folder.

    Args:
        folder_id: The folder configuration ID
        force_full: Force re-sync of all files even if unchanged

    Returns:
        Dictionary with sync status and count
    """
    import asyncio
    from app.services.gdrive_ingestion import GoogleDriveIngestionService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    logger.info(f"Starting Google Drive folder sync: {folder_id}")

    try:
        # Create async engine and session
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async def run_sync():
            async with async_session() as session:
                service = GoogleDriveIngestionService(session)
                result = await service.sync_folder(
                    folder_id=folder_id,
                    force=force_full,
                )
                return {
                    "status": result.status,
                    "folder_id": str(result.folder_id),
                    "files_processed": result.files_processed,
                    "files_ingested": result.files_ingested,
                    "files_failed": result.files_failed,
                    "duration_seconds": result.duration_seconds,
                }

        return asyncio.run(run_sync())

    except Exception as exc:
        logger.error(f"Google Drive sync failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def sync_all_active_folders(self) -> dict[str, Any]:
    """Sync all active Google Drive folders.

    This task is typically scheduled to run periodically.
    """
    import asyncio
    from app.services.gdrive_ingestion import GoogleDriveIngestionService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    logger.info("Starting sync for all active Google Drive folders")

    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async def run_sync():
            async with async_session() as session:
                from app.repositories import gdrive_sync_repo

                folders = await gdrive_sync_repo.get_active_folders(session)

                total_ingested = 0
                total_failed = 0

                for folder in folders:
                    service = GoogleDriveIngestionService(session)
                    result = await service.sync_folder(
                        folder_id=folder.id,
                        force=False,
                    )
                    total_ingested += result.files_ingested
                    total_failed += result.files_failed

                return {
                    "status": "completed",
                    "folders_synced": len(folders),
                    "total_files_ingested": total_ingested,
                    "total_files_failed": total_failed,
                }

        return asyncio.run(run_sync())

    except Exception as exc:
        logger.error(f"Google Drive sync all failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


{% endif %}

# === TaskIQ Task ===
{% if cookiecutter.use_taskiq %}
from app.worker.taskiq_app import broker


@broker.task
async def sync_gdrive_folder_taskiq(
    folder_id: str,
    force_full: bool = False,
) -> dict[str, Any]:
    """Sync a specific Google Drive folder (TaskIQ version).

    Args:
        folder_id: The folder configuration ID
        force_full: Force re-sync of all files even if unchanged

    Returns:
        Dictionary with sync status
    """
    from app.services.gdrive_ingestion import GoogleDriveIngestionService

    logger.info(f"TaskIQ: Starting Google Drive folder sync: {folder_id}")

    service = GoogleDriveIngestionService()
    result = await service.sync_folder(
        folder_id=folder_id,
        force=force_full,
    )

    return {
        "status": result.status,
        "folder_id": str(result.folder_id),
        "files_processed": result.files_processed,
        "files_ingested": result.files_ingested,
        "files_failed": result.files_failed,
        "duration_seconds": result.duration_seconds,
    }


@broker.task
async def sync_all_active_folders_taskiq() -> dict[str, Any]:
    """Sync all active Google Drive folders (TaskIQ version)."""
    from app.services.gdrive_ingestion import GoogleDriveIngestionService
    from app.repositories import gdrive_sync_repo

    logger.info("TaskIQ: Starting sync for all active folders")

    folders = await gdrive_sync_repo.get_active_folders()

    total_ingested = 0
    total_failed = 0

    service = GoogleDriveIngestionService()

    for folder in folders:
        result = await service.sync_folder(
            folder_id=str(folder.id),
            force=False,
        )
        total_ingested += result.files_ingested
        total_failed += result.files_failed

    return {
        "status": "completed",
        "folders_synced": len(folders),
        "total_files_ingested": total_ingested,
        "total_files_failed": total_failed,
    }


{% endif %}

# === ARQ Task ===
{% if cookiecutter.use_arq %}
async def sync_gdrive_folder_arq(
    ctx: dict[str, Any],
    folder_id: str,
    force_full: bool = False,
) -> dict[str, Any]:
    """Sync a specific Google Drive folder (ARQ version).

    Args:
        ctx: ARQ context dictionary
        folder_id: The folder configuration ID
        force_full: Force re-sync of all files even if unchanged

    Returns:
        Dictionary with sync status
    """
    from app.services.gdrive_ingestion import GoogleDriveIngestionService

    logger.info(f"ARQ: Starting Google Drive folder sync: {folder_id}")

    service = GoogleDriveIngestionService()
    result = await service.sync_folder(
        folder_id=folder_id,
        force=force_full,
    )

    return {
        "status": result.status,
        "folder_id": str(result.folder_id),
        "files_processed": result.files_processed,
        "files_ingested": result.files_ingested,
        "files_failed": result.files_failed,
        "duration_seconds": result.duration_seconds,
        "job_id": ctx.get("job_id"),
    }


async def sync_all_active_folders_arq(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sync all active Google Drive folders (ARQ version)."""
    from app.services.gdrive_ingestion import GoogleDriveIngestionService
    from app.repositories import gdrive_sync_repo

    logger.info("ARQ: Starting sync for all active folders")

    folders = await gdrive_sync_repo.get_active_folders()

    total_ingested = 0
    total_failed = 0

    service = GoogleDriveIngestionService()

    for folder in folders:
        result = await service.sync_folder(
            folder_id=str(folder.id),
            force=False,
        )
        total_ingested += result.files_ingested
        total_failed += result.files_failed

    return {
        "status": "completed",
        "folders_synced": len(folders),
        "total_files_ingested": total_ingested,
        "total_files_failed": total_failed,
        "job_id": ctx.get("job_id"),
    }


{% endif %}
{%- else %}
"""Google Drive sync tasks - not configured.

Enable Google Drive ingestion, database, Milvus, and a task system
(Celery/TaskIQ/ARQ) to use these tasks.
"""
{%- endif %}
