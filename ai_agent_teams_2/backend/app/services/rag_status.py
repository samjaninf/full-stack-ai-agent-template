"""RAG status streaming — Redis pub/sub fan-out for SSE clients."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from fastapi.sse import ServerSentEvent

from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGStatusService:
    """Streams RAG ingestion status events from Redis pub/sub."""

    CHANNEL = "rag_status"

    def _redis_url(self) -> str:
        return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

    async def publish_status(self, *, document_id: str, status: str, filename: str) -> None:
        """Publish a status event to the ``rag_status`` channel for SSE subscribers.

        Pub/sub failures are logged but do not propagate — status notifications are a
        soft side-effect; ingestion progress should not fail on a Redis hiccup.
        """
        try:
            client = aioredis.from_url(self._redis_url())  # type: ignore[no-untyped-call]
            try:
                await client.publish(
                    self.CHANNEL,
                    json.dumps(
                        {"document_id": document_id, "status": status, "filename": filename}
                    ),
                )
            finally:
                await client.aclose()
        except Exception as exc:
            logger.warning("rag_status_publish_failed: %s", exc)

    async def stream_events(self) -> AsyncIterator[ServerSentEvent]:
        """Yield ``ServerSentEvent`` items as they arrive on the ``rag_status`` channel.

        The Redis client is created per-stream (one connection per subscriber). Cleanup is
        guaranteed via ``finally`` even if the consumer disconnects mid-stream.
        """
        client = aioredis.from_url(self._redis_url())  # type: ignore[no-untyped-call]
        pubsub = client.pubsub()
        await pubsub.subscribe(self.CHANNEL)
        event_id = 0

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = message["data"]
                data = payload.decode() if isinstance(payload, bytes) else payload
                event_id += 1
                yield ServerSentEvent(raw_data=data, event="status", id=str(event_id))
        except asyncio.CancelledError:
            # Client disconnected — propagate cancellation cleanly
            raise
        except Exception as exc:
            logger.warning("RAG SSE stream error: %s", exc)
        finally:
            try:
                await pubsub.unsubscribe(self.CHANNEL)
                await client.aclose()
            except Exception as exc:
                logger.debug("RAG SSE cleanup error: %s", exc)
