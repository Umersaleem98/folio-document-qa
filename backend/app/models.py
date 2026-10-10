import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import DATETIME
from .db import Base, utcnow

UTCDateTime = DateTime().with_variant(DATETIME(fsp=6), 'mysql', 'mariadb')


def uid():
    return str(uuid.uuid4())


role_permissions = Table('role_permissions', Base.metadata,
    Column('role_id', ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True))


class Permission(Base):
    __tablename__ = 'permissions'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, lazy='selectin')


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(default=0)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))
    role: Mapped[Role] = relationship(lazy='selectin')
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow)


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[object] = mapped_column(UTCDateTime, index=True)


class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    pages: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(default=0)
    lease_until: Mapped[object | None] = mapped_column(UTCDateTime)
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow)


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(120), default='Document conversation')
    document_ids: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow)
    last_activity_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[object] = mapped_column(UTCDateTime, index=True)


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow)
    sources: Mapped[list['Source']] = relationship(cascade='all, delete-orphan', lazy='selectin')


class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    message_id: Mapped[str] = mapped_column(ForeignKey('messages.id', ondelete='CASCADE'), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'))
    document_name: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(Text)


class Usage(Base):
    __tablename__ = 'usage_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    units: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow, index=True)
    __table_args__ = (Index('ix_usage_user_kind_created', 'user_id', 'kind', 'created_at'),)


class Audit(Base):
    __tablename__ = 'audit_records'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(80))
    # Deliberately no request body, chat, source excerpts, or provider output.
    created_at: Mapped[object] = mapped_column(UTCDateTime, default=utcnow, index=True)


class AppLimits(Base):
    __tablename__ = 'app_limits'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    max_upload_mb: Mapped[int] = mapped_column(default=20)
    max_documents: Mapped[int] = mapped_column(default=25)
    daily_questions: Mapped[int] = mapped_column(default=100)


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    reset_at: Mapped[object] = mapped_column(UTCDateTime, index=True)
