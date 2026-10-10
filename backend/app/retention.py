from sqlalchemy import delete
from .db import SessionLocal, utcnow
from .models import AuthSession, Conversation, RateBucket


def cleanup_expired(now=None):
    now = now or utcnow()
    with SessionLocal() as db:
        # FK cascades remove messages and source excerpts. Never touches documents/users.
        result = db.execute(delete(Conversation).where(Conversation.expires_at <= now))
        db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
        db.execute(delete(RateBucket).where(RateBucket.reset_at <= now))
        db.commit()
        return result.rowcount
