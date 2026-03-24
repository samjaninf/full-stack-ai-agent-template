{%- if cookiecutter.enable_rag %}
"""RAG tool for agent knowledge base search."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.rag.retrieval import BaseRetrievalService

_retrieval_service: "BaseRetrievalService | None" = None


def _get_retrieval_service() -> "BaseRetrievalService":
    """Get or create retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is not None:
        return _retrieval_service
    # Import here to avoid circular imports at module load time
    from app.core.config import settings
    from app.rag.retrieval import RetrievalService
{%- if cookiecutter.use_milvus %}
    from app.rag.vectorstore import MilvusVectorStore
{%- elif cookiecutter.use_qdrant %}
    from app.rag.vectorstore import QdrantVectorStore
{%- elif cookiecutter.use_chromadb %}
    from app.rag.vectorstore import ChromaVectorStore
{%- elif cookiecutter.use_pgvector %}
    from app.rag.vectorstore import PgVectorStore
{%- endif %}
    from app.rag.embeddings import EmbeddingService

    rag_settings = settings.rag
    embedding_service = EmbeddingService(rag_settings)
{%- if cookiecutter.use_milvus %}
    vector_store = MilvusVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_qdrant %}
    vector_store = QdrantVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_chromadb %}
    vector_store = ChromaVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_pgvector %}
    vector_store = PgVectorStore(rag_settings, embedding_service)
{%- endif %}
    _retrieval_service = RetrievalService(vector_store, rag_settings)
    return _retrieval_service


def get_retrieval_service() -> "BaseRetrievalService":
    """Get the RetrievalService singleton."""
    return _get_retrieval_service()


async def search_knowledge_base(
    query: str,
    collection: str | None = None,
    collections: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        collection: Name of a single collection. If None, uses RAG_DEFAULT_COLLECTION env var.
        collections: List of collection names for cross-collection search (overrides collection).
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including citations.
    """
    import os
    from typing import Any

    service: Any = get_retrieval_service()

    default_collection = os.environ.get("RAG_DEFAULT_COLLECTION", "all")
    target_collection = collection or default_collection

    if collections and len(collections) > 1:
        results = await service.retrieve_multi(
            query=query,
            collection_names=collections,
            limit=top_k,
        )
    elif target_collection == "all":
        try:
            all_collections = await service.store.list_collections()
            if not all_collections:
                return "No collections found in the knowledge base."
            if len(all_collections) == 1:
                results = await service.retrieve(query=query, collection_name=all_collections[0], limit=top_k)
            else:
                results = await service.retrieve_multi(query=query, collection_names=all_collections, limit=top_k)
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return f"Error accessing knowledge base: {e}"
    else:
        results = await service.retrieve(
            query=query,
            collection_name=target_collection,
            limit=top_k,
        )

    if not results:
        return "No relevant documents found in the knowledge base."

    # Format results with citations for source attribution
    formatted_results = []
    for i, result in enumerate(results, start=1):
        source = result.metadata.get("filename", "unknown")
        page = result.metadata.get("page_num", "")
        chunk = result.metadata.get("chunk_num", "")
        col = result.metadata.get("collection", "")
        page_info = f", page {page}" if page else ""
        chunk_info = f", chunk {chunk}" if chunk else ""
        col_info = f" [{col}]" if col else ""

        formatted_results.append(
            f"[{i}] Source: {source}{page_info}{chunk_info}{col_info} (score: {result.score:.3f})\n"
            f"{result.content}"
        )

    return (
        "Search results (cite sources using [1], [2], etc. in your response):\n\n"
        + "\n\n".join(formatted_results)
    )


def _run_async_search(query: str, collection: str, top_k: int) -> str:
    """Run async search in a dedicated event loop within a thread.

    This creates a fresh event loop for each call, avoiding event loop
    conflicts with the main thread or other async contexts.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            search_knowledge_base(query, collection, top_k=top_k)
        )
    finally:
        loop.close()


def search_knowledge_base_sync(
    query: str,
    collection: str = "documents",
    top_k: int = 5,
) -> str:
    """Synchronous wrapper for search_knowledge_base.

    Use this function in CrewAI agents where async tools need to run
    in a synchronous context.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "default").
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results.
    """
    logger.debug(
        "search_knowledge_base_sync called: query=%s, collection=%s, top_k=%s",
        query,
        collection,
        top_k,
    )
    try:
        # Use ThreadPoolExecutor with a dedicated event loop
        # This avoids "Event loop is closed" errors when asyncio.run()
        # is called multiple times or from within an async context
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_async_search, query, collection, top_k
            )
            result = future.result()
        logger.debug("search_knowledge_base_sync completed successfully")
        return result
    except Exception as e:
        logger.error(
            "search_knowledge_base_sync failed: %s",
            str(e),
            exc_info=True,
        )
        raise

{%- if cookiecutter.use_crewai %}
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class SearchDocumentsInput(BaseModel):
    query: str = Field(..., description="Query string for searching the knowledge base")
    collection: str = Field(default="documents", description="Collection to search")
    top_k: int = Field(default=5, description="Number of top results to return")

class SearchKnowledgeBase(BaseTool):
    """Search the knowledge base and return formatted results.
    """
    name: str = "search_documents"
    description: str = (
        "Search the knowledge base for relevant documents. "
        "Return formatted excerpts with scores and sources."
    )
    args_schema: type[BaseModel] = SearchDocumentsInput

    def _run(self, query: str, collection: str = "documents", top_k: int = 5) -> str:
        # Use sync wrapper for CrewAI
        return search_knowledge_base_sync(query, collection, top_k)

    async def _arun(self, query: str, collection: str = "documents", top_k: int = 5) -> str:
        # Async version
        return await search_knowledge_base(query, collection, top_k)

{%- else %}
__all__ = ["search_knowledge_base", "search_knowledge_base_sync"]
{%- endif %}

{%- else %}
"""RAG tool - not configured."""
{%- endif %}
