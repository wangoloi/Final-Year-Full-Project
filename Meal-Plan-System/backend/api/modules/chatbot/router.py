"""Chatbot routes - thin layer."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.modules.chatbot.service import generate_reply
from api.modules.chatbot import session_service
from api.core.exceptions import ValidationError, to_http_exception

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

FALLBACK = "I'm here to help with nutrition and diabetes. Try: 'What foods are good for diabetes?'"


class ChatbotInput(BaseModel):
    message: str
    session_id: int = Field(..., description="Chat session id from POST /api/chatbot/sessions")


class SessionOut(BaseModel):
    id: int
    title: str | None
    created_at: str | None
    updated_at: str | None


@router.post("/sessions", response_model=SessionOut)
def create_chat_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new empty conversation."""
    s = session_service.create_session(db, user.id)
    return SessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at.isoformat() + "Z" if s.created_at else None,
        updated_at=s.updated_at.isoformat() + "Z" if s.updated_at else None,
    )


@router.get("/sessions", response_model=list[SessionOut])
def list_chat_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent chat sessions (newest first)."""
    rows = session_service.list_sessions(db, user.id)
    return [
        SessionOut(
            id=r.id,
            title=r.title,
            created_at=r.created_at.isoformat() + "Z" if r.created_at else None,
            updated_at=r.updated_at.isoformat() + "Z" if r.updated_at else None,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Load messages for a session."""
    data = session_service.list_session_messages(db, user.id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": data}


@router.delete("/sessions/{session_id}", status_code=204)
def delete_chat_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a session and all its messages."""
    if not session_service.delete_session(db, user.id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return None


@router.post("/message")
def chatbot_message(
    data: ChatbotInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message within a session."""
    if not (data.message or "").strip():
        raise to_http_exception(ValidationError("Message is required"))

    try:
        response = generate_reply(db, user.id, data.message.strip(), data.session_id)
        return {"response": response, "session_id": data.session_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return {"response": FALLBACK, "error": str(e), "session_id": data.session_id}
