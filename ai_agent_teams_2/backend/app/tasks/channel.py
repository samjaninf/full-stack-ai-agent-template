"""Background task handlers for channel event processing."""

import logging
from typing import Any

from app.channels.router import ChannelMessageRouter
from app.db.session import get_db_context

logger = logging.getLogger(__name__)


async def process_channel_event(incoming: Any) -> None:
    """Process a channel message event in the background."""
    channel_router = ChannelMessageRouter()
    try:
        async with get_db_context() as db:
            await channel_router.route(incoming, db)
    except Exception:
        logger.exception("Error processing channel event")
