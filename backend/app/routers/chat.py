"""Chat router — debug endpoint for testing the agent without Feishu.

The primary user interface is now the Feishu Bot webhook.
This endpoint remains for admin/debug testing only.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.schemas.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


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
