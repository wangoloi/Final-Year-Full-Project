"""Chat sessions: list, create, delete, load messages."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from api.models import ChatMessage, ChatSession


def create_session(db: Session, user_id: int) -> ChatSession:
    s = ChatSession(user_id=user_id, title=None)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_owned_session(db: Session, user_id: int, session_id: int) -> ChatSession | None:
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )


def list_sessions(db: Session, user_id: int, limit: int = 50) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .limit(limit)
        .all()
    )


def delete_session(db: Session, user_id: int, session_id: int) -> bool:
    s = get_owned_session(db, user_id, session_id)
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True


def list_session_messages(db: Session, user_id: int, session_id: int) -> list[dict] | None:
    if not get_owned_session(db, user_id, session_id):
        return None
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.chat_session_id == session_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return [
        {
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in rows
    ]


def touch_session(db: Session, session_id: int) -> None:
    s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not s:
        return
    s.updated_at = datetime.utcnow()
    db.commit()


def maybe_set_title_from_first_message(db: Session, session_id: int, user_message: str) -> None:
    s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not s or (s.title or "").strip():
        return
    t = user_message.strip().replace("\n", " ")
    if len(t) > 80:
        t = t[:77] + "…"
    s.title = t or "New chat"
    db.commit()
