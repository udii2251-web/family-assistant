"""FastAPI router for Feishu webhook endpoints."""

import json
import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["feishu"])


@router.post("/webhook")
async def feishu_webhook(request: Request):
    """Main webhook endpoint for all Feishu events.

    Handles:
    1. URL verification challenge — Feishu app setup sends a JSON
       with "challenge" key; we respond with the same challenge value.
    2. im.message.receive_v1 events — user sent a message to the bot.
    3. card.action.trigger events — user clicked a button on a card.

    The event_handler is stored in request.app.state and initialized
    in the main.py lifespan.
    """
    body = await request.body()
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in webhook body")
        return {"status": "error", "message": "invalid JSON"}

    # 1. URL verification challenge (Feishu app setup)
    if "challenge" in body_json:
        logger.info("Received URL verification challenge")
        return {"challenge": body_json["challenge"]}

    # 2. Parse event type
    header = body_json.get("header", {})
    event_type = header.get("event_type", "")
    event_data = body_json.get("event", {})

    # Get the event_handler from app state
    event_handler = getattr(request.app.state, "event_handler", None)
    if not event_handler:
        logger.warning("No event_handler in app state, skipping event")
        return {"status": "ok"}

    # 3. Route to appropriate handler
    if event_type == "im.message.receive_v1":
        await event_handler.handle_message_received(event_data)
    elif event_type == "card.action.trigger":
        # Card action payload structure is different — the whole body is the event
        await event_handler.handle_card_action(body_json)
    else:
        logger.debug(f"Unhandled event type: {event_type}")

    return {"status": "ok"}
