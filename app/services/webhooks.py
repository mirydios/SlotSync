import httpx
import logging
import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.webhook import Webhook

logger = logging.getLogger(__name__)

async def trigger_webhook(db: Session, user_id: str, event: str, payload: Dict[str, Any]):
    """
    Fetches all active webhooks for a user and triggers them asynchronously.
    Events: booking.created, booking.cancelled, booking.rescheduled
    """
    webhooks = db.query(Webhook).filter(
        Webhook.user_id == user_id,
        Webhook.is_active == True,
    ).all()

    if not webhooks:
        return

    data = {
        "event": event,
        "payload": payload,
    }

    async def _post(url: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=data, timeout=5.0)
                resp.raise_for_status()
                logger.info(f"Webhook {event} successfully sent to {url}")
        except Exception as e:
            logger.error(f"Failed to send webhook {event} to {url}: {e}")

    tasks = [_post(wh.url) for wh in webhooks]
    if tasks:
        # Run them in the background so it doesn't block the request
        asyncio.create_task(asyncio.gather(*tasks))

