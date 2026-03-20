"""RAG API routes for collection management, search, document upload, and deletion."""

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession, IngestionSvc, RetrievalSvc, VectorStoreSvc
from app.db.models.rag_document import RAGDocument
from app.schemas.rag import (
    RAGCollectionInfo,
    RAGCollectionList,
    RAGDocumentItem,
    RAGDocumentList,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
):
    """List all available collections in the vector store."""
    names = await vector_store.list_collections()
    return RAGCollectionList(items=names)


@router.post("/collections/{name}", status_code=status.HTTP_201_CREATED)
async def create_collection(
    name: str,
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
):
    """Create and initialize a new collection."""
    await vector_store._ensure_collection(name)
    return {"message": f"Collection '{name}' created successfully."}


@router.delete("/collections/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
):
    """Drop an entire collection and all its vectors."""
    await vector_store.delete_collection(name)


@router.get("/collections/{name}/info", response_model=RAGCollectionInfo)
async def get_collection_info(
    name: str,
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
):
    """Retrieve stats for a specific collection."""
    return await vector_store.get_collection_info(name)


@router.get("/collections/{name}/documents", response_model=RAGDocumentList)
async def list_documents(
    name: str,
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
):
    """List all documents in a specific collection."""
    documents = await vector_store.get_documents(name)
    return RAGDocumentList(
        items=[
            RAGDocumentItem(
                document_id=doc.document_id,
                filename=doc.filename,
                filesize=doc.filesize,
                filetype=doc.filetype,
                chunk_count=doc.chunk_count,
                additional_info=doc.additional_info,
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
    current_user: CurrentUser,
    use_reranker: bool = Query(False, description="Whether to use reranking (if configured)"),
):
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
    "/collections/{name}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    name: str,
    document_id: str,
    ingestion_service: IngestionSvc,
    current_user: CurrentUser,
):
    """Delete a specific document by its ID from a collection."""
    success = await ingestion_service.remove_document(name, document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post("/collections/{name}/ingest")
async def ingest_file(
    name: str,
    file: UploadFile = File(...),
    db: DBSession = None,
    ingestion_service: IngestionSvc = None,
    vector_store: VectorStoreSvc = None,
    current_user: CurrentUser = None,
    replace: bool = Query(False, description="Replace existing document with same source path"),
):
    """Upload and ingest a file into a collection. Tracks status in DB."""
    ALLOWED = {".pdf", ".docx", ".txt", ".md"}
    MAX_SIZE = 50 * 1024 * 1024

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported.")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50MB.")

    # Save original file to storage for later viewing
    from app.services.file_storage import get_file_storage
    storage = get_file_storage()
    storage_path = await storage.save(f"rag/{name}", filename, data)

    # Create RAGDocument record with status=processing
    rag_doc = RAGDocument(
        user_id=current_user.id,
        collection_name=name,
        filename=filename,
        filesize=len(data),
        filetype=ext.lstrip("."),
        storage_path=storage_path,
        status="processing",
    )
    db.add(rag_doc)
    await db.flush()
    await db.commit()
    await db.refresh(rag_doc)
    doc_id = rag_doc.id

    # Ensure collection exists
    await vector_store._ensure_collection(name)

    # Save to temp file and ingest
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        result = await ingestion_service.ingest_file(
            filepath=tmp_path, collection_name=name, replace=replace, source_path=filename,
        )
        # Update status to done
        rag_doc_upd = await db.get(RAGDocument, doc_id)
        if rag_doc_upd:
            rag_doc_upd.status = "done"
            rag_doc_upd.vector_document_id = result.document_id
            rag_doc_upd.completed_at = datetime.now(UTC)
            await db.commit()

        return {
            "id": str(doc_id),
            "status": "done",
            "document_id": result.document_id,
            "filename": filename,
            "collection": name,
            "message": result.message or "Ingested successfully",
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        # Update status to error
        rag_doc_upd = await db.get(RAGDocument, doc_id)
        if rag_doc_upd:
            rag_doc_upd.status = "error"
            rag_doc_upd.error_message = str(e)
            rag_doc_upd.completed_at = datetime.now(UTC)
            await db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/documents")
async def list_rag_documents(
    db: DBSession = None,
    current_user: CurrentUser = None,
    collection_name: str | None = Query(None),
):
    """List all tracked RAG documents, optionally filtered by collection."""
    query = select(RAGDocument).where(RAGDocument.user_id == current_user.id)
    if collection_name:
        query = query.where(RAGDocument.collection_name == collection_name)
    query = query.order_by(RAGDocument.created_at.desc())
    result = await db.execute(query)
    docs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(d.id),
                "collection_name": d.collection_name,
                "filename": d.filename,
                "filesize": d.filesize,
                "filetype": d.filetype,
                "status": d.status,
                "error_message": d.error_message,
                "vector_document_id": d.vector_document_id,
                "chunk_count": d.chunk_count,
                "has_file": bool(d.storage_path),
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "completed_at": d.completed_at.isoformat() if d.completed_at else None,
            }
            for d in docs
        ],
        "total": len(docs),
    }


@router.get("/documents/{doc_id}/download")
async def download_rag_document(
    doc_id: str,
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """Download the original file of an ingested document."""
    from fastapi.responses import Response
    from app.services.file_storage import get_file_storage

    rag_doc = await db.get(RAGDocument, UUID(doc_id))
    if not rag_doc or rag_doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if not rag_doc.storage_path:
        raise HTTPException(status_code=404, detail="Original file not available")

    storage = get_file_storage()
    try:
        data = await storage.load(rag_doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime_map = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain", "md": "text/markdown"}
    mime = mime_map.get(rag_doc.filetype, "application/octet-stream")

    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{rag_doc.filename}"'},
    )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rag_document(
    doc_id: str,
    db: DBSession = None,
    ingestion_service: IngestionSvc = None,
    current_user: CurrentUser = None,
):
    """Delete a document from SQL, vector store, and file storage."""
    from app.services.file_storage import get_file_storage

    rag_doc = await db.get(RAGDocument, UUID(doc_id))
    if not rag_doc or rag_doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Delete from vector store
    if rag_doc.vector_document_id:
        try:
            await ingestion_service.remove_document(rag_doc.collection_name, rag_doc.vector_document_id)
        except Exception as e:
            logger.warning(f"Failed to delete from vector store: {e}")

    # 2. Delete file from storage
    if rag_doc.storage_path:
        try:
            storage = get_file_storage()
            await storage.delete(rag_doc.storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")

    # 3. Delete from SQL
    await db.delete(rag_doc)
    await db.commit()


@router.post("/documents/{doc_id}/retry")
async def retry_ingestion(
    doc_id: str,
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """Retry a failed document ingestion."""
    rag_doc = await db.get(RAGDocument, UUID(doc_id))
    if not rag_doc or rag_doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if rag_doc.status != "error":
        raise HTTPException(status_code=400, detail="Only failed documents can be retried")

    # Reset status
    rag_doc.status = "processing"
    rag_doc.error_message = None
    rag_doc.completed_at = None
    await db.commit()

    return {"id": str(rag_doc.id), "status": "processing", "message": "Retry queued"}
