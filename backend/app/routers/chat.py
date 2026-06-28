"""Chat router — REST API and WebSocket endpoints for Web frontend interaction.

This module provides:
1. REST API for simple request/response interactions
2. WebSocket for real-time bidirectional communication
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.shared.database import get_db, SessionLocal
from app.schemas.schemas import ChatRequest, ChatResponse
from app.adapters.web_adapter import convert_universal_to_web, convert_text_to_web

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# --- REST API Endpoints ---

@router.post("/", response_model=ChatResponse)
def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    """Debug endpoint — please use Feishu Bot for normal interactions.

    For testing, you can call this endpoint directly, but it uses
    the old agent logic. The Feishu webhook is the proper entry point.
    """
    # Fallback: use the old agent logic for backward compat during transition
    from app.services.agent import chat
    result = chat(db, req.message)
    return ChatResponse(reply=result["reply"], actions=result["actions"])


@router.post("/web")
async def send_message_web(req: ChatRequest):
    """Web frontend chat endpoint.

    This endpoint uses the new orchestrator-based architecture
    and returns Web-compatible card JSON.
    """
    try:
        # Import orchestrator components
        from app.services.orchestrator import Orchestrator
        from app.services.session import SessionManager

        # Get orchestrator and session manager (for now, create new instances)
        # In production, these should be managed globally
        orchestrator = Orchestrator()
        session_manager = SessionManager()

        # Use a default open_id for web users (can be enhanced with auth later)
        open_id = "web_user_default"

        # Get or create session
        session = session_manager.get_or_create(open_id)

        # Add user message to session history
        session_manager.add_message(open_id, "user", req.message)

        # Call orchestrator
        response = await orchestrator.handle_message(open_id, req.message, session)

        # Convert response to web format
        response_type = response.get("type", "text")
        response_content = response.get("content", "")

        if response_type == "card":
            # response_content can be:
            # - UniversalCard instance: Convert directly
            # - dict: Reconstruct UniversalCard (backward compat)
            if isinstance(response_content, dict):
                # Legacy/reconstructed case
                from app.services.universal_card import UniversalCard, CardType, AlertLevel
                card = UniversalCard(
                    card_type=CardType(response_content.get("card_type", "simple_text")),
                    title=response_content.get("title", ""),
                    timestamp=response_content.get("timestamp", ""),
                    content=response_content.get("content", {}),
                    alert_level=AlertLevel(response_content.get("alert_level", "info")),
                    buttons=[],
                    metadata=response_content.get("metadata", {}),
                )
                web_card = convert_universal_to_web(card)
            else:
                # UniversalCard instance
                web_card = convert_universal_to_web(response_content)
        else:
            # response_content is a text string
            web_card = convert_text_to_web(str(response_content))

        # Add assistant response to session history
        session_manager.add_message(open_id, "assistant", str(response_content)[:200])

        return {
            "success": True,
            "data": web_card,
        }

    except Exception as e:
        logger.error(f"Error in web chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/action")
async def handle_web_action(action_data: Dict[str, Any]):
    """Handle web frontend card actions (button clicks).

    Args:
        action_data: {
            "action": "mark_done",
            "alert_id": "123"
        }

    Returns:
        Updated card JSON
    """
    try:
        action_type = action_data.get("action", "")

        if action_type == "mark_done":
            alert_id_str = action_data.get("alert_id", "")

            if not alert_id_str or alert_id_str == "0":
                # Manual purchase confirmation (no alert_id)
                return {
                    "success": True,
                    "data": convert_text_to_web("已由家人确认补货完成。", "已补货"),
                }

            alert_id = int(alert_id_str)

            # Update alert status in database
            db = SessionLocal()
            try:
                from app.modules.inventory.models import RestockAlert

                alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()

                if alert:
                    alert.status = "done"
                    db.commit()
                    logger.info(f"Alert {alert_id} marked as done via web")

                    return {
                        "success": True,
                        "data": convert_text_to_web(
                            f"{alert.message or '补货提醒'}\n\n已由家人确认补货完成。",
                            "已补货"
                        ),
                    }
                else:
                    logger.warning(f"Alert {alert_id} not found")
                    return {
                        "success": True,
                        "data": convert_text_to_web("已由家人确认补货完成。", "已补货"),
                    }
            finally:
                db.close()

        else:
            logger.warning(f"Unknown web action: {action_type}")
            raise HTTPException(status_code=400, detail=f"Unknown action: {action_type}")

    except Exception as e:
        logger.error(f"Error handling web action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- WebSocket Support ---

class ConnectionManager:
    """Manage WebSocket connections for real-time chat."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "default"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}")

    def disconnect(self, user_id: str = "default"):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: {user_id}")

    async def send_message(self, message: Dict[str, Any], user_id: str = "default"):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        for user_id, websocket in self.active_connections.items():
            await websocket.send_json(message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat.

    Protocol:
    - Client sends: {"type": "message", "content": "user message"}
    - Server sends: {"type": "card", "data": {...}} or {"type": "text", "data": "..."}

    Example usage:
        ws = WebSocket("ws://localhost:8000/chat/ws/user123")
        await ws.send_json({"type": "message", "content": "帮我查一下洗衣液的库存"})
        response = await ws.recv_json()
    """
    await manager.connect(websocket, user_id)

    try:
        # Import orchestrator components
        from app.services.orchestrator import Orchestrator
        from app.services.session import SessionManager

        orchestrator = Orchestrator()
        session_manager = SessionManager()

        # Get or create session for this user
        session = session_manager.get_or_create(user_id)

        while True:
            # Receive message from client
            data = await websocket.receive_json()

            if data.get("type") == "message":
                user_message = data.get("content", "").strip()

                if not user_message:
                    continue

                logger.info(f"WebSocket message from {user_id}: {user_message}")

                # Add user message to session history
                session_manager.add_message(user_id, "user", user_message)

                try:
                    # Call orchestrator
                    response = await orchestrator.handle_message(user_id, user_message, session)

                    # Convert response to web format
                    response_type = response.get("type", "text")
                    response_content = response.get("content", "")

                    if response_type == "card":
                        # response_content can be:
                        # - UniversalCard instance: Convert directly
                        # - dict: Reconstruct UniversalCard (backward compat)
                        if isinstance(response_content, dict):
                            from app.services.universal_card import UniversalCard, CardType, AlertLevel
                            card = UniversalCard(
                                card_type=CardType(response_content.get("card_type", "simple_text")),
                                title=response_content.get("title", ""),
                                timestamp=response_content.get("timestamp", ""),
                                content=response_content.get("content", {}),
                                alert_level=AlertLevel(response_content.get("alert_level", "info")),
                                buttons=[],
                                metadata=response_content.get("metadata", {}),
                            )
                            web_card = convert_universal_to_web(card)
                        else:
                            # UniversalCard instance
                            web_card = convert_universal_to_web(response_content)
                        await manager.send_message({
                            "type": "card",
                            "data": web_card,
                        }, user_id)
                    else:
                        # response_content is a text string
                        await manager.send_message({
                            "type": "text",
                            "data": str(response_content),
                        }, user_id)

                    # Add assistant response to session history
                    session_manager.add_message(user_id, "assistant", str(response_content)[:200])

                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                    await manager.send_message({
                        "type": "error",
                        "data": f"处理消息时出错: {str(e)}",
                    }, user_id)

            elif data.get("type") == "action":
                # Handle card actions
                action_data = data.get("data", {})
                action_type = action_data.get("action", "")

                if action_type == "mark_done":
                    alert_id_str = action_data.get("alert_id", "")

                    if not alert_id_str or alert_id_str == "0":
                        await manager.send_message({
                            "type": "card",
                            "data": convert_text_to_web("已由家人确认补货完成。", "已补货"),
                        }, user_id)
                        continue

                    alert_id = int(alert_id_str)

                    # Update alert status in database
                    db = SessionLocal()
                    try:
                        from app.modules.inventory.models import RestockAlert

                        alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()

                        if alert:
                            alert.status = "done"
                            db.commit()
                            logger.info(f"Alert {alert_id} marked as done via WebSocket")

                            await manager.send_message({
                                "type": "card",
                                "data": convert_text_to_web(
                                    f"{alert.message or '补货提醒'}\n\n已由家人确认补货完成。",
                                    "已补货"
                                ),
                            }, user_id)
                        else:
                            await manager.send_message({
                                "type": "card",
                                "data": convert_text_to_web("已由家人确认补货完成。", "已补货"),
                            }, user_id)
                    finally:
                        db.close()

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"WebSocket disconnected: {user_id}")

    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}", exc_info=True)
        manager.disconnect(user_id)


@router.get("/ws/health")
def websocket_health():
    """Health check endpoint for WebSocket service."""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
    }