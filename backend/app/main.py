"""Family Steward Agent — FastAPI entry point with Feishu Bot integration."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env file before importing config (so env vars are available)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.database import init_db
from app.shared.config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_MODE, TRIGGER_ENABLED

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global event loop reference for cross-thread async calls
_event_loop = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize all components."""
    # Store the event loop for WebSocket thread to use
    global _event_loop
    _event_loop = asyncio.get_running_loop()

    # Initialize Feishu client
    from app.feishu.client import FeishuClient
    feishu_client = FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET)

    # Initialize orchestrator and session manager
    from app.shared.orchestrator import Orchestrator
    from app.shared.session import SessionManager
    orchestrator = Orchestrator()
    session_manager = SessionManager()

    # Initialize event handler (wires feishu ↔ orchestrator)
    from app.feishu.event_handler import FeishuEventHandler
    event_handler = FeishuEventHandler(feishu_client, orchestrator, session_manager)

    # Initialize Feishu dispatcher (manages event subscription)
    from app.feishu.dispatcher import FeishuDispatcher
    feishu_dispatcher = FeishuDispatcher(event_handler, event_loop=_event_loop)

    # Start Feishu connection based on configured mode
    if FEISHU_MODE == "websocket":
        feishu_dispatcher.start_websocket()
    elif FEISHU_MODE == "webhook":
        # Webhook mode — events come via HTTP POST to /feishu/webhook
        # The dispatcher is still needed for the webhook handler to use
        logger.info("Using webhook mode — events will be received via /feishu/webhook")
    else:
        logger.warning(f"Unknown FEISHU_MODE: {FEISHU_MODE}, defaulting to webhook")

    # Start trigger engine (proactive notifications)
    from app.modules.inventory.triggers import TriggerEngine
    trigger_engine = TriggerEngine(feishu_client)
    trigger_engine.register_all_triggers()
    trigger_engine.start()

    # Store references in app state for access from routers
    app.state.feishu_client = feishu_client
    app.state.orchestrator = orchestrator
    app.state.session_manager = session_manager
    app.state.event_handler = event_handler
    app.state.feishu_dispatcher = feishu_dispatcher
    app.state.trigger_engine = trigger_engine

    logger.info(f"Family Steward Agent started (mode: {FEISHU_MODE})")

    yield

    # Shutdown
    if FEISHU_MODE == "websocket":
        feishu_dispatcher.stop_websocket()
    trigger_engine.shutdown()
    logger.info("Family Steward Agent stopped")


app = FastAPI(title="Family Steward Agent", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Feishu webhook router (used in webhook mode; still mounted for both modes)
from app.feishu.webhook import router as feishu_router
app.include_router(feishu_router)

# REST API routers (keep for admin/debug access)
from app.modules.inventory.routers import (
    family_router, items_router, consumption_router,
    purchases_router, inventory_router, alerts_router
)
app.include_router(family_router)
app.include_router(items_router)
app.include_router(consumption_router)
app.include_router(purchases_router)
app.include_router(inventory_router)
app.include_router(alerts_router)

# Chat router — simplified for debug/testing without Feishu
from app.routers.chat import router as chat_router
app.include_router(chat_router)


@app.get("/")
def root():
    return {"name": "Family Steward Agent", "version": "2.0.0"}
