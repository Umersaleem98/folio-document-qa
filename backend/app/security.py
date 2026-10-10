from datetime import timedelta
from hashlib import sha256
import secrets
import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, utcnow
from .models import AuthSession, User, RateBucket

hasher = PasswordHasher(type=Type.ID)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def verify_password(password, encoded):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get('access_token')
    if not token:
        raise HTTPException(401, 'Authentication required')
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'],
                            issuer='document-qa', audience='document-qa',
                            options={'require': ['exp', 'iat', 'sub', 'jti', 'ver']})
        user = db.get(User, claims['sub'])
        session = db.get(AuthSession, claims['jti'])
        if not user or not user.active or not session or session.user_id != user.id or session.expires_at <= utcnow() or claims['ver'] != user.token_version:
            raise ValueError('Inactive session')
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            csrf = request.cookies.get('csrf_token', '')
            if not csrf or not secrets.compare_digest(csrf, request.headers.get('X-CSRF-Token', '')):
                raise HTTPException(403, 'CSRF token required')
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401, 'Session expired or revoked')


def require(permission):
    def dependency(user: User = Depends(current_user)):
        if permission not in {p.name for p in user.role.permissions}:
            raise HTTPException(403, 'Permission denied')
        return user
    return dependency


def rate_limit(db, key, maximum, seconds=60):
    key = sha256(key.encode()).hexdigest()
    now = utcnow()
    # Dedicated transaction: durable counters across API restarts and processes.
    from .db import SessionLocal
    with SessionLocal() as counter_db:
        bucket = counter_db.scalar(select(RateBucket).where(RateBucket.key == key).with_for_update())
        if not bucket:
            try:
                counter_db.add(RateBucket(key=key, count=0, reset_at=now + timedelta(seconds=seconds)))
                counter_db.commit()
            except IntegrityError:
                counter_db.rollback()
            bucket = counter_db.scalar(select(RateBucket).where(RateBucket.key == key).with_for_update())
        if bucket.reset_at <= now:
            bucket.count = 0
            bucket.reset_at = now + timedelta(seconds=seconds)
        if bucket.count >= maximum:
            raise HTTPException(429, 'Rate limit exceeded; try again later', headers={'Retry-After': str(seconds)})
        bucket.count += 1
        counter_db.commit()
