"""RAG API routes for collection management, search, document upload, and deletion."""

import asyncio
import logging
import os
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import (
    CurrentAdmin,
    CurrentUser,
    IngestionSvc,
    RAGDocumentSvc,
    RAGSyncSvc,
    RetrievalSvc,
    SyncSourceSvc,
    VectorStoreSvc,
)
from app.core.config import settings as app_settings
from app.core.exceptions import NotFoundError
from app.rag.config import get_supported_formats
from app.schemas.rag import (
    RAGCollectionInfo,
    RAGCollectionList,
    RAGDocumentList,
    RAGIngestResponse,
    RAGMessageResponse,
    RAGRetryResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
    RAGSyncLogList,
    RAGSyncRequest,
    RAGSyncResponse,
    RAGTrackedDocumentList,
)
from app.schemas.sync_source import (
    ConnectorList,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
    SyncSourceUpdate,
)
from app.services.file_storage import get_file_storage
from app.worker.tasks.rag_tasks import (
    ingest_document_task,
    sync_collection_task,
    sync_single_source_task,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/supported-formats")
async def get_supported_formats_endpoint() -> Any:
    """Return file formats supported by the current PDF parser configuration."""
    parser_name = getattr(app_settings, "PDF_PARSER", "pymupdf")
    return {"parser": parser_name, "formats": sorted(get_supported_formats(parser_name))}


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
    vector_store: VectorStoreSvc,
    _: CurrentAdmin,
) -> Any:
    """List all available collections in the vector store."""
    names = await vector_store.list_collections()
    return RAGCollectionList(items=names)


@router.post(
    "/collections/{name}", status_code=status.HTTP_201_CREATED, response_model=RAGMessageResponse
)
async def create_collection(
    name: str,
    vector_store: VectorStoreSvc,
    _: CurrentAdmin,
) -> Any:
    """Create and initialize a new collection."""
    try:
        await vector_store.create_collection(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGMessageResponse(message=f"Collection '{name}' created successfully.")


@router.delete("/collections/{name}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
    rag_doc_svc: RAGDocumentSvc,
    _: CurrentAdmin,
) -> None:
    """Drop an entire collection — vectors and all SQL document records."""
    await vector_store.delete_collection(name)
    await rag_doc_svc.delete_by_collection(name)


@router.get("/collections/{name}/info", response_model=RAGCollectionInfo)
async def get_collection_info(
    name: str,
    vector_store: VectorStoreSvc,
    _: CurrentAdmin,
) -> Any:
    """Retrieve stats for a specific collection."""
    return await vector_store.get_collection_info(name)


@router.get("/collections/{name}/documents", response_model=RAGDocumentList)
async def list_documents(
    name: str,
    vector_store: VectorStoreSvc,
    _: CurrentAdmin,
) -> Any:
    """List all documents in a specific collection."""
    return await vector_store.get_document_list(name)


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
    current_user: CurrentUser,
    use_reranker: bool = Query(False, description="Whether to use reranking (if configured)"),
) -> Any:
    """Search for relevant document chunks. Supports multi-collection search."""
    if request.collection_names and len(request.collection_names) > 1:
        results = await retrieval_service.retrieve_multi(
            query=request.query,
            collection_names=request.collection_names,
            limit=request.limit,
            min_score=request.min_score,
            use_reranker=use_reranker,
        )
    else:
        collection = (
            request.collection_names[0] if request.collection_names else request.collection_name
        )
        results = await retrieval_service.retrieve(
            query=request.query,
            collection_name=collection,
            limit=request.limit,
            min_score=request.min_score,
            filter=request.filter or "",
            use_reranker=use_reranker,
        )
    api_results = [RAGSearchResult(**hit.model_dump()) for hit in results]
    return RAGSearchResponse(results=api_results)


@router.delete(
    "/collections/{name}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_document(
    name: str,
    document_id: str,
    ingestion_service: IngestionSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a specific document by its ID from a collection."""
    success = await ingestion_service.remove_document(name, document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post(
    "/collections/{name}/ingest", response_model=RAGIngestResponse, response_model_exclude_none=True
)
async def ingest_file(
    name: str,
    background_tasks: BackgroundTasks,
    rag_doc_svc: RAGDocumentSvc,
    ingestion_service: IngestionSvc,
    vector_store: VectorStoreSvc,
    _: CurrentAdmin,
    file: UploadFile = File(...),
    replace: bool = Query(False),
) -> Any:
    """Upload and ingest a file into a collection. Tracks status in DB."""
    ALLOWED = get_supported_formats(getattr(app_settings, "PDF_PARSER", "pymupdf"))
    max_size = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(sorted(ALLOWED))}",
        )

    data = await file.read()
    if len(data) > max_size:
        raise HTTPException(
            status_code=413, detail=f"File too large. Maximum {app_settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    storage = get_file_storage()
    storage_path = await storage.save(f"rag/{name}", filename, data)
    rag_doc = await rag_doc_svc.create_document(
        collection_name=name,
        filename=filename,
        filesize=len(data),
        filetype=ext.lstrip("."),
        storage_path=storage_path,
    )
    doc_id = rag_doc.id

    await vector_store.create_collection(name)

    # Save to shared media volume (accessible by both app and worker containers)
    tmp_dir = os.path.join(str(app_settings.MEDIA_DIR), "_rag_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{doc_id!s}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    # Dispatch async task
    ingest_document_task.delay(
        rag_document_id=str(doc_id),
        collection_name=name,
        filepath=tmp_path,
        source_path=filename,
        replace=replace,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "id": str(doc_id),
            "status": "processing",
            "filename": filename,
            "collection": name,
            "message": "File accepted. Processing in background.",
        },
    )


@router.get("/documents", response_model=RAGTrackedDocumentList)
async def list_rag_documents(
    rag_doc_svc: RAGDocumentSvc,
    _: CurrentAdmin,
    collection_name: str | None = Query(None),
) -> Any:
    """List tracked RAG documents."""
    return await rag_doc_svc.list_documents(collection_name)


@router.get("/documents/{doc_id}/download")
async def download_rag_document(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
    _: CurrentAdmin,
) -> Any:
    """Download the original file."""
    try:
        file_path, filename, mime_type = await rag_doc_svc.get_download_info(doc_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    return FileResponse(path=file_path, filename=filename, media_type=mime_type)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_rag_document(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
    ingestion_service: IngestionSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a document from SQL, vector store, and file storage."""

    try:
        await rag_doc_svc.delete_document(doc_id, ingestion_service)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post("/documents/{doc_id}/retry", response_model=RAGRetryResponse)
async def retry_ingestion(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
    _: CurrentAdmin,
) -> Any:
    """Retry a failed document ingestion."""

    try:
        doc = await rag_doc_svc.retry_ingestion(doc_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGRetryResponse(id=str(doc.id), status="processing", message="Retry queued")


@router.get("/sync/logs", response_model=RAGSyncLogList)
async def list_sync_logs(
    rag_sync_svc: RAGSyncSvc,
    _: CurrentAdmin,
    collection_name: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List sync operation logs."""
    return await rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)


@router.post("/sync/local", response_model=RAGSyncResponse)
async def trigger_local_sync(
    request: RAGSyncRequest,
    background_tasks: BackgroundTasks,
    rag_sync_svc: RAGSyncSvc,
    _: CurrentAdmin,
) -> Any:
    """Trigger a local directory sync via background task."""
    sync_log = await rag_sync_svc.create_sync_log(
        source="local",
        collection_name=request.collection_name,
        mode=request.mode,
    )
    sync_collection_task.delay(
        sync_log_id=str(sync_log.id),
        source="local",
        collection_name=request.collection_name,
        mode=request.mode,
        path=request.path,
    )

    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync started for '{request.collection_name}' (mode={request.mode})",
    )


@router.delete("/sync/{sync_id}", response_model=RAGMessageResponse)
async def cancel_sync(
    sync_id: str,
    rag_sync_svc: RAGSyncSvc,
    _: CurrentAdmin,
) -> Any:
    """Cancel a running sync operation."""

    try:
        await rag_sync_svc.cancel_sync(sync_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGMessageResponse(message="Sync cancelled")


@router.get("/sync/sources", response_model=SyncSourceList)
async def list_sync_sources(
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> Any:
    """List all configured sync sources."""
    return await sync_source_svc.list_sources()


@router.post("/sync/sources", response_model=SyncSourceRead, status_code=status.HTTP_201_CREATED)
async def create_sync_source(
    data: SyncSourceCreate,
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> Any:
    """Create a new sync source configuration."""

    try:
        return await sync_source_svc.create_source(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/sync/sources/{source_id}", response_model=SyncSourceRead)
async def update_sync_source(
    source_id: str,
    data: SyncSourceUpdate,
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> Any:
    """Update an existing sync source configuration."""

    try:
        return await sync_source_svc.update_source(source_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.delete(
    "/sync/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_sync_source(
    source_id: str,
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a sync source configuration."""

    try:
        await sync_source_svc.delete_source(source_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post("/sync/sources/{source_id}/trigger", response_model=RAGSyncResponse)
async def trigger_sync_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> Any:
    """Trigger a manual sync for a configured source."""

    try:
        sync_log = await sync_source_svc.trigger_sync(source_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e

    # Dispatch background task to execute the sync
    sync_single_source_task.delay(source_id, str(sync_log.id))

    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync triggered for source '{source_id}'",
    )


@router.get("/sync/connectors", response_model=ConnectorList)
async def list_connectors(
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
) -> Any:
    """List available sync connector types with their config schemas."""
    return sync_source_svc.list_connectors()


# SSE for RAG status updates (auto-reconnect via EventSource API)
@router.get("/status/stream", response_class=EventSourceResponse)
async def rag_status_stream() -> AsyncIterable[ServerSentEvent]:
    """SSE endpoint for real-time RAG ingestion status updates.

    Subscribes to Redis pub/sub channel 'rag_status' and streams events.
    Browser auto-reconnects via EventSource API.
    """
    r = aioredis.from_url(
        f"redis://{app_settings.REDIS_HOST}:{app_settings.REDIS_PORT}/{app_settings.REDIS_DB}"
    )  # type: ignore[no-untyped-call]
    pubsub = r.pubsub()
    await pubsub.subscribe("rag_status")
    event_id = 0

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = (
                    message["data"].decode()
                    if isinstance(message["data"], bytes)
                    else message["data"]
                )
                event_id += 1
                yield ServerSentEvent(raw_data=data, event="status", id=str(event_id))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"RAG SSE error: {e}")
    finally:
        try:
            await pubsub.unsubscribe("rag_status")
            await r.aclose()
        except Exception:
            pass
