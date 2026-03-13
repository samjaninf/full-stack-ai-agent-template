{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database and cookiecutter.use_milvus %}
{%- if cookiecutter.use_postgresql %}
"""Google Drive ingestion service (PostgreSQL async).

This service orchestrates the synchronization of files from Google Drive
to the RAG pipeline.
"""

import hashlib
import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.gdrive_sync import (
    GoogleDriveFile as DBGoogleDriveFile,
    GoogleDriveFolder as DBGoogleDriveFolder,
    GoogleDriveSyncLog,
)
from app.rag.gdrive_client import GoogleDriveClient, GoogleDriveFile as GDriveFile
from app.rag.ingestion import IngestionService
from app.repositories import gdrive_sync_repo

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a folder sync operation."""

    folder_id: uuid.UUID
    status: str  # success, partial, failed
    files_processed: int
    files_ingested: int
    files_failed: int
    duration_seconds: float
    error_message: str | None


@dataclass
class FileSyncResult:
    """Result of a single file sync."""

    file_id: str
    status: str  # ingested, skipped, failed
    document_id: str | None
    error_message: str | None


class GoogleDriveIngestionService:
    """Orchestrates Google Drive file sync to RAG pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        gdrive_client: GoogleDriveClient | None = None,
        ingestion_service: IngestionService | None = None,
    ):
        """Initialize the service.

        Args:
            db: Database session
            gdrive_client: Optional Google Drive client (will create if not provided)
            ingestion_service: Optional ingestion service (will create if not provided)
        """
        self.db = db
        self.gdrive_client = gdrive_client or GoogleDriveClient()
        self._ingestion_service = ingestion_service

    async def _get_ingestion_service(self) -> IngestionService:
        """Get or create the ingestion service."""
        if self._ingestion_service is None:
            from app.rag.config import RAGSettings
            from app.rag.vectorstore import MilvusVectorStore
            from app.rag.embeddings import EmbeddingService
            from app.rag.documents import DocumentProcessor

            settings = RAGSettings()
            embed_service = EmbeddingService(settings)
            vector_store = MilvusVectorStore(settings, embed_service)
            processor = DocumentProcessor(settings)
            self._ingestion_service = IngestionService(processor, vector_store)

        return self._ingestion_service

    async def sync_folder(
        self,
        folder_id: uuid.UUID,
        force: bool = False,
    ) -> SyncResult:
        """Sync all files from a Google Drive folder.

        Args:
            folder_id: The folder configuration ID
            force: Force re-sync of all files even if unchanged

        Returns:
            SyncResult with sync statistics
        """
        start_time = datetime.now(UTC)

        # Get folder config
        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, None)  # Background task - no user filter
        if not folder:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder not found",
            )

        if not folder.is_active:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder sync is disabled",
            )

        # Create sync log
        sync_log = GoogleDriveSyncLog(
            folder_id=folder_id,
            started_at=start_time,
            status="running",
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # List files from Google Drive
            gdrive_files = await self.gdrive_client.list_files_in_folder(
                folder.folder_id,
                page_size=100,
            )

            files_processed = 0
            files_ingested = 0
            files_failed = 0

            ingestion_service = await self._get_ingestion_service()

            for gfile in gdrive_files:
                if not gfile.is_supported:
                    logger.info(f"Skipping unsupported file: {gfile.name}")
                    continue

                files_processed += 1

                result = await self._sync_single_file(
                    folder, gfile, ingestion_service, force
                )

                if result.status == "ingested":
                    files_ingested += 1
                elif result.status == "failed":
                    files_failed += 1

            # Update folder sync status
            duration = (datetime.now(UTC) - start_time).total_seconds()

            if files_failed > 0 and files_ingested > 0:
                folder.last_sync_status = "partial"
            elif files_failed > 0:
                folder.last_sync_status = "failed"
            else:
                folder.last_sync_status = "success"

            folder.last_sync_at = datetime.now(UTC)

            # Update sync log
            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = "completed" if files_failed == 0 else "partial"
            sync_log.files_processed = files_processed
            sync_log.files_ingested = files_ingested
            sync_log.files_failed = files_failed

            await self.db.commit()

            return SyncResult(
                folder_id=folder_id,
                status=sync_log.status,
                files_processed=files_processed,
                files_ingested=files_ingested,
                files_failed=files_failed,
                duration_seconds=duration,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Folder sync failed: {e}")
            await self.db.rollback()

            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            await self.db.commit()

            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message=str(e),
            )

    async def _sync_single_file(
        self,
        folder: DBGoogleDriveFolder,
        gfile: GDriveFile,
        ingestion_service: IngestionService,
        force: bool = False,
    ) -> FileSyncResult:
        """Sync a single file from Google Drive.

        Args:
            folder: The folder configuration
            gfile: The Google Drive file
            ingestion_service: The ingestion service to use
            force: Force re-sync even if unchanged

        Returns:
            FileSyncResult with sync status
        """
        try:
            # Check if file already exists in DB
            db_file = await gdrive_sync_repo.get_file_by_gdrive_id(
                self.db, folder.id, gfile.id
            )

            if db_file and not force:
                # Check if file has changed
                if db_file.last_synced_at and db_file.checksum:
                    # File hasn't changed, skip
                    return FileSyncResult(
                        file_id=gfile.id,
                        status="skipped",
                        document_id=db_file.milvus_document_id,
                        error_message=None,
                    )

            # Download file content
            content, mime_type = await self.gdrive_client.download_file(gfile.id)

            # Calculate checksum using SHA-256 (more secure than MD5)
            checksum = hashlib.sha256(content).hexdigest()

            # Check if checksum matches
            if db_file and db_file.checksum == checksum and not force:
                return FileSyncResult(
                    file_id=gfile.id,
                    status="skipped",
                    document_id=db_file.milvus_document_id,
                    error_message=None,
                )

            # Save to temp file
            temp_dir = Path(tempfile.gettempdir()) / "gdrive_uploads"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"{gfile.id}_{gfile.name}"

            try:
                temp_path.write_bytes(content)

                # Ingest to RAG
                result = await ingestion_service.ingest_file(
                    filepath=temp_path,
                    collection_name=folder.collection_name,
                )

                # Update or create database record
                now = datetime.now(UTC)

                if db_file:
                    db_file.filename = gfile.name
                    db_file.mime_type = gfile.mime_type
                    db_file.file_size = gfile.size
                    db_file.checksum = checksum
                    db_file.milvus_document_id = result.document_id
                    db_file.last_synced_at = now
                    db_file.ingestion_status = (
                        "ingested" if result.status == "done" else "failed"
                    )
                    db_file.error_message = result.error_message
                else:
                    new_file = DBGoogleDriveFile(
                        folder_id=folder.id,
                        file_id=gfile.id,
                        filename=gfile.name,
                        mime_type=gfile.mime_type,
                        file_size=gfile.size,
                        checksum=checksum,
                        milvus_document_id=result.document_id,
                        last_synced_at=now,
                        ingestion_status=(
                            "ingested" if result.status == "done" else "failed"
                        ),
                        error_message=result.error_message,
                    )
                    self.db.add(new_file)

                await self.db.flush()

                return FileSyncResult(
                    file_id=gfile.id,
                    status="ingested" if result.status == "done" else "failed",
                    document_id=result.document_id,
                    error_message=result.error_message,
                )

            finally:
                # Cleanup temp file
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"Failed to sync file {gfile.name}: {e}")

            # Update or create error record
            db_file = await gdrive_sync_repo.get_file_by_gdrive_id(
                self.db, folder.id, gfile.id
            )

            if db_file:
                db_file.ingestion_status = "failed"
                db_file.error_message = str(e)
                await self.db.flush()
            else:
                new_file = DBGoogleDriveFile(
                    folder_id=folder.id,
                    file_id=gfile.id,
                    filename=gfile.name,
                    mime_type=gfile.mime_type,
                    file_size=gfile.size,
                    ingestion_status="failed",
                    error_message=str(e),
                )
                self.db.add(new_file)
                await self.db.flush()

            return FileSyncResult(
                file_id=gfile.id,
                status="failed",
                document_id=None,
                error_message=str(e),
            )

    async def delete_orphaned_documents(
        self,
        folder_id: uuid.UUID,
    ) -> int:
        """Remove documents from Milvus that no longer exist in Drive.

        Args:
            folder_id: The folder configuration ID

        Returns:
            Number of documents deleted
        """
        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, None)  # Background task - no user filter
        if not folder:
            return 0

        # Get current Google Drive files
        gdrive_files = await self.gdrive_client.list_files_in_folder(folder.folder_id)
        gdrive_file_ids = {f.id for f in gdrive_files}

        # Get tracked files
        tracked_files = await gdrive_sync_repo.get_files_by_folder(self.db, folder_id)

        deleted_count = 0
        ingestion_service = await self._get_ingestion_service()

        for tracked_file in tracked_files:
            if tracked_file.file_id not in gdrive_file_ids:
                # File no longer exists in Drive, remove from Milvus
                if tracked_file.milvus_document_id:
                    success = await ingestion_service.remove_document(
                        collection_name=folder.collection_name,
                        document_id=tracked_file.milvus_document_id,
                    )
                    if success:
                        tracked_file.ingestion_status = "skipped"
                        tracked_file.milvus_document_id = None
                        deleted_count += 1

        await self.db.flush()
        return deleted_count

    # === Folder CRUD Operations ===

    async def create_folder(
        self,
        user_id: uuid.UUID,
        data: "GoogleDriveFolderCreate",
    ) -> "GoogleDriveFolderResponse":
        """Create a new folder sync configuration.

        Args:
            user_id: The ID of the user creating the folder
            data: Folder creation data

        Returns:
            Created folder response
        """
        from app.schemas.gdrive import GoogleDriveFolderCreate, GoogleDriveFolderResponse

        folder = await gdrive_sync_repo.create_folder(
            self.db,
            user_id=user_id,
            folder_id=data.folder_id,
            folder_name=data.folder_name,
            collection_name=data.collection_name,
            sync_interval_minutes=data.sync_interval_minutes,
        )
        await self.db.commit()
        await self.db.refresh(folder)
        return GoogleDriveFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            folder_id=folder.folder_id,
            folder_name=folder.folder_name,
            collection_name=folder.collection_name,
            is_active=folder.is_active,
            sync_interval_minutes=folder.sync_interval_minutes,
            last_sync_at=folder.last_sync_at,
            last_sync_status=folder.last_sync_status,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )

    async def list_folders(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list["GoogleDriveFolderResponse"], int]:
        """List all configured folders for a user.

        Args:
            user_id: The ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (folders list, total count)
        """
        from app.schemas.gdrive import GoogleDriveFolderResponse

        folders, total = await gdrive_sync_repo.get_folder_list(
            self.db, user_id=user_id, skip=skip, limit=limit
        )
        return (
            [
                GoogleDriveFolderResponse(
                    id=f.id,
                    user_id=f.user_id,
                    folder_id=f.folder_id,
                    folder_name=f.folder_name,
                    collection_name=f.collection_name,
                    is_active=f.is_active,
                    sync_interval_minutes=f.sync_interval_minutes,
                    last_sync_at=f.last_sync_at,
                    last_sync_status=f.last_sync_status,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                )
                for f in folders
            ],
            total,
        )

    async def get_folder(self, folder_id: uuid.UUID, user_id: uuid.UUID) -> "GoogleDriveFolderResponse | None":
        """Get folder by ID for a specific user.

        Args:
            folder_id: Folder ID
            user_id: User ID for authorization

        Returns:
            Folder response or None if not found
        """
        from app.schemas.gdrive import GoogleDriveFolderResponse

        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, user_id)
        if not folder:
            return None
        return GoogleDriveFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            folder_id=folder.folder_id,
            folder_name=folder.folder_name,
            collection_name=folder.collection_name,
            is_active=folder.is_active,
            sync_interval_minutes=folder.sync_interval_minutes,
            last_sync_at=folder.last_sync_at,
            last_sync_status=folder.last_sync_status,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )

    async def update_folder(
        self,
        folder_id: uuid.UUID,
        user_id: uuid.UUID,
        data: "GoogleDriveFolderUpdate",
    ) -> "GoogleDriveFolderResponse | None":
        """Update folder configuration.

        Args:
            folder_id: Folder ID
            user_id: User ID for authorization
            data: Update data

        Returns:
            Updated folder response or None if not found
        """
        from app.schemas.gdrive import GoogleDriveFolderResponse, GoogleDriveFolderUpdate

        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, user_id)
        if not folder:
            return None

        folder = await gdrive_sync_repo.update_folder(self.db, folder, data)
        await self.db.commit()
        await self.db.refresh(folder)

        return GoogleDriveFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            folder_id=folder.folder_id,
            folder_name=folder.folder_name,
            collection_name=folder.collection_name,
            is_active=folder.is_active,
            sync_interval_minutes=folder.sync_interval_minutes,
            last_sync_at=folder.last_sync_at,
            last_sync_status=folder.last_sync_status,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )

    async def delete_folder(self, folder_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a folder configuration.

        Args:
            folder_id: Folder ID
            user_id: User ID for authorization
        """
        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, user_id)
        if not folder:
            return
        await gdrive_sync_repo.delete_folder(self.db, folder)
        await self.db.commit()

    async def list_files(
        self,
        folder_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list["GoogleDriveFileResponse"], int]:
        """List all files synced from a folder.

        Args:
            folder_id: Folder ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (files list, total count)
        """
        from app.schemas.gdrive import GoogleDriveFileResponse

        # TODO: Use database-level pagination instead of fetching all and slicing in Python
        # This is inefficient for large datasets - update repository to support pagination
        files = await gdrive_sync_repo.get_files_by_folder(self.db, folder_id)
        total = len(files)
        files = files[skip : skip + limit]

        return (
            [
                GoogleDriveFileResponse(
                    id=f.id,
                    file_id=f.file_id,
                    filename=f.filename,
                    mime_type=f.mime_type,
                    file_size=f.file_size,
                    checksum=f.checksum,
                    milvus_document_id=f.milvus_document_id,
                    last_synced_at=f.last_synced_at,
                    ingestion_status=f.ingestion_status,
                    error_message=f.error_message,
                )
                for f in files
            ],
            total,
        )

    async def get_sync_logs(
        self,
        folder_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list["GoogleDriveSyncLogResponse"], int]:
        """Get sync history for a folder.

        Args:
            folder_id: Folder ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (logs list, total count)
        """
        from app.schemas.gdrive import GoogleDriveSyncLogResponse

        logs = await gdrive_sync_repo.get_sync_logs(self.db, folder_id, skip, limit)
        total = len(logs)

        return (
            [
                GoogleDriveSyncLogResponse(
                    id=l.id,
                    folder_id=l.folder_id,
                    started_at=l.started_at,
                    completed_at=l.completed_at,
                    status=l.status,
                    files_processed=l.files_processed,
                    files_ingested=l.files_ingested,
                    files_failed=l.files_failed,
                    error_message=l.error_message,
                )
                for l in logs
            ],
            total,
        )

    async def trigger_sync(
        self,
        folder_id: uuid.UUID,
        user_id: uuid.UUID,
        force: bool = False,
    ) -> "GoogleDriveSyncResponse | None":
        """Trigger a sync for a folder.

        Args:
            folder_id: Folder ID
            user_id: User ID for authorization
            force: Force re-sync of all files

        Returns:
            Sync response or None if folder not found
        """
        from datetime import UTC
        from app.schemas.gdrive import GoogleDriveSyncResponse

        # Verify user owns the folder
        folder = await gdrive_sync_repo.get_folder(self.db, folder_id, user_id)
        if not folder:
            return None

        result = await self.sync_folder(folder_id, force=force)
        return GoogleDriveSyncResponse(
            folder_id=result.folder_id,
            status=result.status,
            files_processed=result.files_processed,
            files_ingested=result.files_ingested,
            files_failed=result.files_failed,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=result.duration_seconds,
            error_message=result.error_message,
        )


{%- elif cookiecutter.use_sqlite %}
"""Google Drive ingestion service (SQLite sync).

This service orchestrates the synchronization of files from Google Drive
to the RAG pipeline.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.db.models.gdrive_sync import (
    GoogleDriveFile as DBGoogleDriveFile,
    GoogleDriveFolder as DBGoogleDriveFolder,
    GoogleDriveSyncLog,
)
from app.rag.gdrive_client import GoogleDriveClient, GoogleDriveFile as GDriveFile
from app.rag.ingestion import IngestionService
from app.repositories import gdrive_sync_repo

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a folder sync operation."""

    folder_id: str
    status: str
    files_processed: int
    files_ingested: int
    files_failed: int
    duration_seconds: float
    error_message: str | None


@dataclass
class FileSyncResult:
    """Result of a single file sync."""

    file_id: str
    status: str
    document_id: str | None
    error_message: str | None


class GoogleDriveIngestionService:
    """Orchestrates Google Drive file sync to RAG pipeline."""

    def __init__(
        self,
        db: DBSession,
        gdrive_client: GoogleDriveClient | None = None,
        ingestion_service: IngestionService | None = None,
    ):
        """Initialize the service."""
        self.db = db
        self.gdrive_client = gdrive_client or GoogleDriveClient()
        self._ingestion_service = ingestion_service

    def _get_ingestion_service(self) -> IngestionService:
        """Get or create the ingestion service."""
        if self._ingestion_service is None:
            from app.rag.config import RAGSettings
            from app.rag.vectorstore import MilvusVectorStore
            from app.rag.embeddings import EmbeddingService
            from app.rag.documents import DocumentProcessor

            settings = RAGSettings()
            embed_service = EmbeddingService(settings)
            vector_store = MilvusVectorStore(settings, embed_service)
            processor = DocumentProcessor(settings)
            self._ingestion_service = IngestionService(processor, vector_store)

        return self._ingestion_service

    def sync_folder(
        self,
        folder_id: str,
        force: bool = False,
    ) -> SyncResult:
        """Sync all files from a Google Drive folder."""
        import asyncio

        start_time = datetime.now(UTC)

        folder = gdrive_sync_repo.get_folder(self.db, folder_id, None)  # Background task - no user filter
        if not folder:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder not found",
            )

        if not folder.is_active:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder sync is disabled",
            )

        sync_log = GoogleDriveSyncLog(
            folder_id=folder_id,
            started_at=start_time,
            status="running",
        )
        self.db.add(sync_log)
        self.db.flush()

        try:
            # Run async code
            gdrive_files = asyncio.run(
                self.gdrive_client.list_files_in_folder(folder.folder_id)
            )

            files_processed = 0
            files_ingested = 0
            files_failed = 0

            ingestion_service = self._get_ingestion_service()

            for gfile in gdrive_files:
                if not gfile.is_supported:
                    continue

                files_processed += 1
                result = self._sync_single_file(folder, gfile, ingestion_service, force)

                if result.status == "ingested":
                    files_ingested += 1
                elif result.status == "failed":
                    files_failed += 1

            duration = (datetime.now(UTC) - start_time).total_seconds()

            if files_failed > 0 and files_ingested > 0:
                folder.last_sync_status = "partial"
            elif files_failed > 0:
                folder.last_sync_status = "failed"
            else:
                folder.last_sync_status = "success"

            folder.last_sync_at = datetime.now(UTC)

            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = "completed" if files_failed == 0 else "partial"
            sync_log.files_processed = files_processed
            sync_log.files_ingested = files_ingested
            sync_log.files_failed = files_failed

            self.db.commit()

            return SyncResult(
                folder_id=folder_id,
                status=sync_log.status,
                files_processed=files_processed,
                files_ingested=files_ingested,
                files_failed=files_failed,
                duration_seconds=duration,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Folder sync failed: {e}")
            self.db.rollback()

            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            self.db.commit()

            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message=str(e),
            )

    def _sync_single_file(
        self,
        folder: DBGoogleDriveFolder,
        gfile: GDriveFile,
        ingestion_service: IngestionService,
        force: bool = False,
    ) -> FileSyncResult:
        """Sync a single file from Google Drive."""
        import asyncio

        try:
            content, mime_type = asyncio.run(
                self.gdrive_client.download_file(gfile.id)
            )

            # Calculate checksum using SHA-256 (more secure than MD5)
            checksum = hashlib.sha256(content).hexdigest()

            temp_dir = Path(tempfile.gettempdir()) / "gdrive_uploads"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"{gfile.id}_{gfile.name}"

            try:
                temp_path.write_bytes(content)
                result = asyncio.run(
                    ingestion_service.ingest_file(
                        filepath=temp_path,
                        collection_name=folder.collection_name,
                    )
                )

                now = datetime.now(UTC)
                db_file = gdrive_sync_repo.get_file_by_gdrive_id(
                    self.db, folder.id, gfile.id
                )

                if db_file:
                    db_file.filename = gfile.name
                    db_file.mime_type = gfile.mime_type
                    db_file.file_size = gfile.size
                    db_file.checksum = checksum
                    db_file.milvus_document_id = result.document_id
                    db_file.last_synced_at = now
                    db_file.ingestion_status = (
                        "ingested" if result.status == "done" else "failed"
                    )
                else:
                    new_file = DBGoogleDriveFile(
                        folder_id=folder.id,
                        file_id=gfile.id,
                        filename=gfile.name,
                        mime_type=gfile.mime_type,
                        file_size=gfile.size,
                        checksum=checksum,
                        milvus_document_id=result.document_id,
                        last_synced_at=now,
                        ingestion_status=(
                            "ingested" if result.status == "done" else "failed"
                        ),
                    )
                    self.db.add(new_file)

                self.db.flush()

                return FileSyncResult(
                    file_id=gfile.id,
                    status="ingested" if result.status == "done" else "failed",
                    document_id=result.document_id,
                    error_message=result.error_message,
                )

            finally:
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"Failed to sync file {gfile.name}: {e}")
            return FileSyncResult(
                file_id=gfile.id,
                status="failed",
                document_id=None,
                error_message=str(e),
            )


{%- elif cookiecutter.use_mongodb %}
"""Google Drive ingestion service (MongoDB).

This service orchestrates the synchronization of files from Google Drive
to the RAG pipeline.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.db.models.gdrive_sync import GoogleDriveFile, GoogleDriveFolder, GoogleDriveSyncLog
from app.rag.gdrive_client import GoogleDriveClient, GoogleDriveFile as GDriveFile
from app.rag.ingestion import IngestionService
from app.repositories import gdrive_sync_repo

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a folder sync operation."""

    folder_id: str
    status: str
    files_processed: int
    files_ingested: int
    files_failed: int
    duration_seconds: float
    error_message: str | None


@dataclass
class FileSyncResult:
    """Result of a single file sync."""

    file_id: str
    status: str
    document_id: str | None
    error_message: str | None


class GoogleDriveIngestionService:
    """Orchestrates Google Drive file sync to RAG pipeline."""

    def __init__(
        self,
        gdrive_client: GoogleDriveClient | None = None,
        ingestion_service: IngestionService | None = None,
    ):
        """Initialize the service."""
        self.gdrive_client = gdrive_client or GoogleDriveClient()
        self._ingestion_service = ingestion_service

    def _get_ingestion_service(self) -> IngestionService:
        """Get or create the ingestion service."""
        if self._ingestion_service is None:
            from app.rag.config import RAGSettings
            from app.rag.vectorstore import MilvusVectorStore
            from app.rag.embeddings import EmbeddingService
            from app.rag.documents import DocumentProcessor

            settings = RAGSettings()
            embed_service = EmbeddingService(settings)
            vector_store = MilvusVectorStore(settings, embed_service)
            processor = DocumentProcessor(settings)
            self._ingestion_service = IngestionService(processor, vector_store)

        return self._ingestion_service

    async def sync_folder(
        self,
        folder_id: str,
        force: bool = False,
    ) -> SyncResult:
        """Sync all files from a Google Drive folder."""
        import asyncio

        start_time = datetime.now(UTC)

        folder = await gdrive_sync_repo.get_folder(folder_id, None)  # Background task - no user filter
        if not folder:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder not found",
            )

        if not folder.is_active:
            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message="Folder sync is disabled",
            )

        sync_log = GoogleDriveSyncLog(
            folder_id=folder_id,
            started_at=start_time,
            status="running",
        )
        await sync_log.create()

        try:
            gdrive_files = await self.gdrive_client.list_files_in_folder(
                folder.folder_id
            )

            files_processed = 0
            files_ingested = 0
            files_failed = 0

            ingestion_service = self._get_ingestion_service()

            for gfile in gdrive_files:
                if not gfile.is_supported:
                    continue

                files_processed += 1
                result = await self._sync_single_file(
                    folder, gfile, ingestion_service, force
                )

                if result.status == "ingested":
                    files_ingested += 1
                elif result.status == "failed":
                    files_failed += 1

            duration = (datetime.now(UTC) - start_time).total_seconds()

            status = "completed" if files_failed == 0 else "partial"
            if files_failed > 0 and files_ingested == 0:
                status = "failed"

            await gdrive_sync_repo.update_folder(
                folder_id,
                {
                    "last_sync_status": status,
                    "last_sync_at": datetime.now(UTC),
                }
            )

            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = status
            sync_log.files_processed = files_processed
            sync_log.files_ingested = files_ingested
            sync_log.files_failed = files_failed
            await sync_log.save()

            return SyncResult(
                folder_id=folder_id,
                status=status,
                files_processed=files_processed,
                files_ingested=files_ingested,
                files_failed=files_failed,
                duration_seconds=duration,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Folder sync failed: {e}")

            sync_log.completed_at = datetime.now(UTC)
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            await sync_log.save()

            return SyncResult(
                folder_id=folder_id,
                status="failed",
                files_processed=0,
                files_ingested=0,
                files_failed=0,
                duration_seconds=0,
                error_message=str(e),
            )

    async def _sync_single_file(
        self,
        folder: GoogleDriveFolder,
        gfile: GDriveFile,
        ingestion_service: IngestionService,
        force: bool = False,
    ) -> FileSyncResult:
        """Sync a single file from Google Drive."""
        try:
            content, mime_type = await self.gdrive_client.download_file(gfile.id)

            checksum = hashlib.md5(content).hexdigest()

            temp_dir = Path(tempfile.gettempdir()) / "gdrive_uploads"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"{gfile.id}_{gfile.name}"

            try:
                temp_path.write_bytes(content)

                result = await ingestion_service.ingest_file(
                    filepath=temp_path,
                    collection_name=folder.collection_name,
                )

                now = datetime.now(UTC)

                # Update or create file record
                await gdrive_sync_repo.upsert_file(
                    folder_id=str(folder.id),
                    file_id=gfile.id,
                    data={
                        "filename": gfile.name,
                        "mime_type": gfile.mime_type,
                        "file_size": gfile.size,
                        "checksum": checksum,
                        "milvus_document_id": result.document_id,
                        "last_synced_at": now,
                        "ingestion_status": (
                            "ingested" if result.status == "done" else "failed"
                        ),
                    }
                )

                return FileSyncResult(
                    file_id=gfile.id,
                    status="ingested" if result.status == "done" else "failed",
                    document_id=result.document_id,
                    error_message=result.error_message,
                )

            finally:
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"Failed to sync file {gfile.name}: {e}")
            return FileSyncResult(
                file_id=gfile.id,
                status="failed",
                document_id=None,
                error_message=str(e),
            )


{%- endif %}
{%- else %}
"""Google Drive ingestion service - not configured."""
{%- endif %}
