"""RAG ingestion & sync tasks — processes documents asynchronously."""

import asyncio
import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from celery import shared_task

from app.db.session import get_worker_db_context
from app.repositories import sync_source_repo
from app.services.rag.config import DocumentExtensions
from app.services.rag.connectors import CONNECTOR_REGISTRY
from app.services.rag.ingestion import IngestionService
from app.services.rag_document import RAGDocumentService
from app.services.rag_status import RAGStatusService
from app.services.rag_sync import RAGSyncService
from app.services.sync_source import SyncSourceService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)  # type: ignore
def ingest_document_task(
    self: Any,
    rag_document_id: str,
    collection_name: str,
    filepath: str,
    source_path: str,
    replace: bool = False,
) -> dict[str, Any]:
    """Process a document: parse, chunk, embed, store in vector DB."""
    logger.info(f"Starting ingestion: {source_path} -> {collection_name}")
    try:
        return asyncio.run(
            _run_ingestion(rag_document_id, collection_name, filepath, source_path, replace)
        )
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        asyncio.run(_mark_ingestion_failed(rag_document_id, str(exc)))
        raise self.retry(exc=exc, countdown=30) from exc


@shared_task(bind=True, max_retries=1, soft_time_limit=600, time_limit=720)  # type: ignore
def sync_collection_task(
    self: Any,
    sync_log_id: str,
    source: str,
    collection_name: str,
    mode: str,
    path: str,
) -> dict[str, Any]:
    """Sync a collection from a local directory."""
    logger.info(f"Starting sync: {source} -> {collection_name} (mode={mode})")
    try:
        return asyncio.run(_run_local_sync(sync_log_id, source, collection_name, mode, path))
    except Exception as exc:
        logger.error(f"Sync failed: {exc}")
        asyncio.run(_mark_sync_failed(sync_log_id, str(exc)))
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(bind=True, max_retries=2, soft_time_limit=600, time_limit=720)  # type: ignore
def sync_single_source_task(
    self: Any,
    source_id: str,
    sync_log_id: str | None = None,
) -> dict[str, Any]:
    """Sync a single connector source. If ``sync_log_id`` is provided, reuse existing log."""
    logger.info(f"Starting source sync: {source_id}")
    try:
        return asyncio.run(_run_source_sync(source_id, sync_log_id=sync_log_id))
    except Exception as exc:
        logger.error(f"Source sync failed: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task  # type: ignore
def check_scheduled_syncs() -> None:
    """Periodic task: find sources due for sync and dispatch individual tasks."""
    asyncio.run(_dispatch_due_syncs())


async def _dispatch_due_syncs() -> None:
    async with get_worker_db_context() as db:
        sources = await sync_source_repo.get_due_for_sync(db)
    for source in sources:
        sync_single_source_task.delay(str(source.id))
    logger.info("scheduled_sync_dispatched", extra={"count": len(sources)})


async def _run_ingestion(
    rag_document_id: str,
    collection_name: str,
    filepath: str,
    source_path: str,
    replace: bool,
) -> dict[str, Any]:
    ingestion_service = IngestionService.from_settings()

    try:
        result = await ingestion_service.ingest_file(
            filepath=Path(filepath),
            collection_name=collection_name,
            replace=replace,
            source_path=source_path,
        )
    except Exception as exc:
        await _mark_ingestion_failed(rag_document_id, str(exc))
        raise

    async with get_worker_db_context() as db:
        await RAGDocumentService(db).complete_ingestion(
            rag_document_id, vector_document_id=result.document_id
        )
    await RAGStatusService().publish_status(
        document_id=rag_document_id, status="done", filename=source_path
    )
    logger.info(f"Ingestion complete: {source_path}")
    return {"status": "done", "document_id": result.document_id, "filename": source_path}


async def _run_local_sync(
    sync_log_id: str,
    source: str,
    collection_name: str,
    mode: str,
    path: str,
) -> dict[str, Any]:
    ingestion_service = IngestionService.from_settings()

    target_path = Path(path).resolve()
    if not target_path.exists():
        await _mark_sync_failed(sync_log_id, f"Path not found: {path}")
        return {"status": "error", "message": f"Path not found: {path}"}

    files = (
        [target_path]
        if target_path.is_file()
        else [f for f in target_path.rglob("*") if f.is_file() and not f.name.startswith(".")]
    )
    allowed = {ext.value for ext in DocumentExtensions}
    files = [f for f in files if f.suffix.lower() in allowed]

    ingested = updated = skipped = failed = 0

    for filepath in files:
        if await _sync_was_cancelled(sync_log_id):
            logger.info(f"Sync {sync_log_id} cancelled by user")
            return {
                "status": "cancelled",
                "ingested": ingested,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
            }

        if mode in ("new_only", "update_only") and await _should_skip(
            ingestion_service, mode, collection_name, filepath
        ):
            skipped += 1
            continue

        try:
            result = await ingestion_service.ingest_file(
                filepath=filepath, collection_name=collection_name, replace=True
            )
            if result.status.value == "done":
                if result.message and "replaced" in result.message:
                    updated += 1
                else:
                    ingested += 1
                async with get_worker_db_context() as db:
                    rag_doc_svc = RAGDocumentService(db)
                    doc = await rag_doc_svc.create_document(
                        collection_name=collection_name,
                        filename=filepath.name,
                        filesize=filepath.stat().st_size,
                        filetype=filepath.suffix.lstrip(".").lower(),
                    )
                    await rag_doc_svc.complete_ingestion(
                        str(doc.id), vector_document_id=result.document_id
                    )
            else:
                failed += 1
        except Exception as exc:
            logger.warning(f"Sync file error {filepath.name}: {exc}")
            failed += 1

    async with get_worker_db_context() as db:
        await RAGSyncService(db).complete_sync(
            sync_log_id,
            status="done" if failed == 0 else "error",
            total_files=len(files),
            ingested=ingested,
            updated=updated,
            skipped=skipped,
            failed=failed,
        )

    return {
        "status": "done",
        "ingested": ingested,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }


async def _sync_was_cancelled(sync_log_id: str) -> bool:
    async with get_worker_db_context() as db:
        sync_log = await RAGSyncService(db).get_sync_log(sync_log_id)
    return sync_log.status == "cancelled"


async def _should_skip(
    ingestion_service: IngestionService,
    mode: str,
    collection_name: str,
    filepath: Path,
) -> bool:
    """Decide whether a file should be skipped under ``new_only``/``update_only`` modes.

    Existence is checked via the ingestion service; identical content (same SHA-256)
    is treated as a no-op to keep periodic syncs idempotent.
    """
    source_path = str(filepath.resolve())
    existing_id = await ingestion_service.find_existing(collection_name, source_path)

    if mode == "new_only":
        if not existing_id:
            return False
        return await _content_unchanged(ingestion_service, collection_name, filepath, source_path)

    # mode == "update_only"
    if not existing_id:
        return True
    return await _content_unchanged(ingestion_service, collection_name, filepath, source_path)


async def _content_unchanged(
    ingestion_service: IngestionService,
    collection_name: str,
    filepath: Path,
    source_path: str,
) -> bool:
    file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
    existing_hash = await ingestion_service.get_existing_hash(collection_name, source_path)
    return bool(existing_hash) and existing_hash == file_hash


async def _mark_ingestion_failed(rag_document_id: str, error_message: str) -> None:
    try:
        async with get_worker_db_context() as db:
            await RAGDocumentService(db).fail_ingestion(
                rag_document_id, error_message=error_message
            )
    except Exception as exc:
        logger.warning(f"Failed to mark ingestion as failed: {exc}")


async def _mark_sync_failed(sync_log_id: str, error_message: str) -> None:
    try:
        async with get_worker_db_context() as db:
            await RAGSyncService(db).complete_sync(
                sync_log_id, status="error", error_message=error_message
            )
    except Exception as exc:
        logger.warning(f"Failed to mark sync as failed: {exc}")


async def _run_source_sync(source_id: str, sync_log_id: str | None = None) -> dict[str, Any]:
    """Core sync logic for connector-based sources (Google Drive, S3, etc.).

    Fetches files from a remote connector, downloads them to a temporary directory, and
    ingests each into the vector store.
    """
    async with get_worker_db_context() as db:
        source_svc = SyncSourceService(db)
        source = await source_svc.get_source(source_id)
        connector_cls = CONNECTOR_REGISTRY.get(source.connector_type)
        if not connector_cls:
            await source_svc.update_after_sync(
                source_id, "error", f"Unknown connector: {source.connector_type}"
            )
            return {"status": "error", "message": f"Unknown connector: {source.connector_type}"}

        config = source.config if isinstance(source.config, dict) else json.loads(source.config)
        collection_name = source.collection_name
        sync_mode = source.sync_mode

        # Reuse the SyncLog from the API trigger; otherwise the scheduler creates one
        if sync_log_id:
            log_id = sync_log_id
        else:
            log = await source_svc.trigger_sync(source_id)
            log_id = str(log.id)

    connector = connector_cls()
    ingestion_svc = IngestionService.from_settings()
    ingested = skipped = failed = total = 0

    try:
        files = await connector.list_files(config)
        total = len(files)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for remote_file in files:
                try:
                    local_path = await connector.download_file(remote_file, Path(tmp_dir))
                    await ingestion_svc.ingest_file(
                        filepath=local_path,
                        collection_name=collection_name,
                        replace=(sync_mode == "full"),
                        source_path=remote_file.source_path,
                    )
                    ingested += 1
                except Exception as exc:
                    logger.warning(f"Failed to sync {remote_file.name}: {exc}")
                    failed += 1
    except Exception as exc:
        logger.error(f"Source sync failed for {source_id}: {exc}")
        failed = max(failed, 1)

    async with get_worker_db_context() as db:
        sync_svc = RAGSyncService(db)
        source_svc = SyncSourceService(db)
        try:
            await sync_svc.complete_sync(
                log_id,
                status="done" if not failed else "error",
                total_files=total,
                ingested=ingested,
                skipped=skipped,
                failed=failed,
            )
            await source_svc.update_after_sync(
                source_id,
                status="done" if not failed else "error",
                error=f"{failed} files failed" if failed else None,
            )
        except Exception:
            logger.error(f"Failed to update sync status for source {source_id}")

    logger.info(
        "source_sync_complete",
        extra={
            "source_id": source_id,
            "total": total,
            "ingested": ingested,
            "skipped": skipped,
            "failed": failed,
        },
    )
    return {
        "status": "done" if not failed else "error",
        "total": total,
        "ingested": ingested,
        "skipped": skipped,
        "failed": failed,
    }
