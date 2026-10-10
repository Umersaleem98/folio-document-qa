from datetime import timedelta
from pathlib import Path
import secrets
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import ai, schemas
from .config import settings
from .db import get_db, utcnow
from .documents import extract_chunks, file_path
from .models import (AppLimits, Audit, AuthSession, Conversation, Document, Message,
                     Permission, Role, Source, Usage, User, uid)
from .security import current_user, require, rate_limit, hasher, verify_password, DUMMY_HASH

router = APIRouter(prefix='/api')


def audit(db, actor, action, target=None):
    db.add(Audit(actor_id=actor, action=action, target_id=target))


def user_json(user):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'active': user.active,
            'role_id': user.role_id, 'role': user.role.name,
            'permissions': [p.name for p in user.role.permissions]}


def iso(value):
    return value.isoformat(timespec='seconds') + 'Z'


def doc_json(doc):
    return {'id': doc.id, 'name': doc.name, 'size': doc.size, 'status': doc.status,
            'pages': doc.pages, 'error': doc.error, 'created_at': iso(doc.created_at)}


def conv_json(conv):
    return {'id': conv.id, 'title': conv.title, 'document_ids': conv.document_ids,
            'created_at': iso(conv.created_at), 'last_activity_at': iso(conv.last_activity_at),
            'expires_at': iso(conv.expires_at)}


def message_json(message):
    return {'id': message.id, 'role': message.role, 'content': message.content,
            'created_at': iso(message.created_at), 'sources': [
                {'document_id': s.document_id, 'document_name': s.document_name,
                 'page': s.page, 'excerpt': s.excerpt} for s in message.sources]}


def owned_doc(db, document_id, user):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not doc or doc.status == 'deleting':
        raise HTTPException(404, 'Document not found')
    return doc


def owned_conversation(db, conversation_id, user, lock=False):
    statement = select(Conversation).where(Conversation.id == conversation_id,
        Conversation.owner_id == user.id, Conversation.expires_at > utcnow())
    if lock:
        statement = statement.with_for_update()
    conv = db.scalar(statement)
    if not conv:
        raise HTTPException(404, 'Conversation not found or expired')
    return conv


@router.post('/auth/register', status_code=201)
def register(body: schemas.Register, request: Request, db: Session = Depends(get_db)):
    rate_limit(db, 'register:' + request.client.host, 5, 3600)
    role = db.scalar(select(Role).where(Role.name == 'user'))
    if not role:
        raise HTTPException(503, 'Run database migrations and initialization')
    user = User(email=str(body.email).lower(), name=body.name.strip(), password_hash=hasher.hash(body.password), role_id=role.id)
    db.add(user)
    try:
        db.flush()
        audit(db, user.id, 'auth.register', user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Unable to register this email')
    return {'message': 'Account created. Please sign in.'}


@router.post('/auth/login')
def login(body: schemas.Login, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(db, 'login:' + request.client.host, 10, 300)
    rate_limit(db, 'login-email:' + str(body.email).lower(), 10, 300)
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        audit(db, None, 'auth.login_failed')
        db.commit()
        raise HTTPException(401, 'Invalid credentials or inactive account')
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    expires = utcnow() + timedelta(minutes=settings.access_token_minutes)
    auth_session = AuthSession(id=uid(), user_id=user.id, expires_at=expires)
    db.add(auth_session)
    audit(db, user.id, 'auth.login')
    db.commit()
    token = jwt.encode({'sub': user.id, 'jti': auth_session.id, 'ver': user.token_version,
        'exp': int(expires.replace(tzinfo=__import__('datetime').timezone.utc).timestamp()),
        'iat': int(utcnow().replace(tzinfo=__import__('datetime').timezone.utc).timestamp()),
        'iss': 'document-qa', 'aud': 'document-qa'}, settings.jwt_secret, algorithm='HS256')
    response.set_cookie('access_token', token, httponly=True, secure=settings.cookie_secure,
        samesite='strict', max_age=settings.access_token_minutes * 60, path='/api')
    response.set_cookie('csrf_token', secrets.token_urlsafe(32), httponly=False,
        secure=settings.cookie_secure, samesite='strict', max_age=settings.access_token_minutes * 60, path='/')
    return user_json(user)


@router.post('/auth/logout', status_code=204)
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    claims = jwt.decode(request.cookies['access_token'], settings.jwt_secret, algorithms=['HS256'], issuer='document-qa', audience='document-qa')
    db.execute(delete(AuthSession).where(AuthSession.id == claims['jti']))
    audit(db, user.id, 'auth.logout')
    db.commit()
    response.delete_cookie('access_token', path='/api')
    response.delete_cookie('csrf_token', path='/')


@router.get('/auth/me')
def me(user: User = Depends(current_user)):
    return user_json(user)


@router.get('/auth/session')
def session_status(request: Request, response: Response, db: Session = Depends(get_db)):
    """A logged-out browser is a normal session state, not an API error."""
    response.headers['Cache-Control'] = 'no-store'
    try:
        user = current_user(request, db)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        response.delete_cookie('access_token', path='/api')
        response.delete_cookie('csrf_token', path='/')
        return {'user': None}
    return {'user': user_json(user)}


@router.patch('/profile')
def profile(body: schemas.Profile, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = body.name.strip()
    db.commit()
    return user_json(user)


@router.post('/profile/password', status_code=204)
def password(body: schemas.PasswordChange, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, 'Current password is incorrect')
    user.password_hash = hasher.hash(body.new_password)
    user.token_version += 1
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    audit(db, user.id, 'auth.password_changed')
    db.commit()
    response.delete_cookie('access_token', path='/api')
    response.delete_cookie('csrf_token', path='/')


@router.get('/limits')
def limits(user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AppLimits, 1)
    return {'max_upload_mb': row.max_upload_mb, 'max_documents': row.max_documents,
            'daily_questions': row.daily_questions, 'chat_retention_hours': 24}


@router.get('/ai/status')
def ai_status(user: User = Depends(current_user)):
    return ai.service_status()


@router.get('/documents')
def documents(user: User = Depends(require('documents.manage')), db: Session = Depends(get_db)):
    return [doc_json(d) for d in db.scalars(select(Document).where(Document.owner_id == user.id,
        Document.status != 'deleting').order_by(Document.created_at.desc()))]


@router.post('/documents', status_code=202)
def upload(file: UploadFile = File(...), user: User = Depends(require('documents.manage')), db: Session = Depends(get_db)):
    rate_limit(db, 'upload:' + user.id, 10, 600)
    # Lock owner row to serialize concurrent uploads against the quota.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    limits = db.get(AppLimits, 1)
    count = db.scalar(select(func.count()).select_from(Document).where(Document.owner_id == user.id))
    if count >= limits.max_documents:
        raise HTTPException(422, 'Document quota reached')
    filename = (file.filename or '').replace('\\', '/').split('/')[-1]
    if not filename.lower().endswith('.pdf') or file.content_type not in {'application/pdf', 'application/octet-stream'}:
        raise HTTPException(415, 'Only PDF files are accepted')
    document = Document(id=uid(), owner_id=user.id, name=filename[:255], size=0, status='queued')
    path = file_path(document.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as output:
            while chunk := file.file.read(64 * 1024):
                document.size += len(chunk)
                if document.size > limits.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, 'PDF exceeds upload size limit')
                output.write(chunk)
        with path.open('rb') as input_file:
            if not input_file.read(1024).lstrip().startswith(b'%PDF-'):
                raise HTTPException(415, 'Invalid PDF signature')
        # Full extraction runs in the worker. Quick structural validation runs here.
        import pymupdf
        try:
            # Open bounded bytes: failed PyMuPDF opens can retain a Windows file handle.
            with pymupdf.open(stream=path.read_bytes(), filetype='pdf') as pdf:
                if not pdf.is_pdf or pdf.needs_pass or not 1 <= len(pdf) <= settings.max_pdf_pages:
                    raise HTTPException(422, 'Invalid, encrypted, or oversized PDF')
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(422, 'Cannot parse PDF')
        db.add(document)
        db.add(Usage(user_id=user.id, kind='upload', units=document.size))
        audit(db, user.id, 'document.upload', document.id)
        db.commit()
        return doc_json(document)
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get('/documents/{document_id}/file')
def view_document(document_id: str, user: User = Depends(require('documents.manage')), db: Session = Depends(get_db)):
    document = owned_doc(db, document_id, user)
    path = file_path(document.id)
    if not path.exists():
        raise HTTPException(404, 'File unavailable')
    # Attachment avoids executing active PDF content in the application origin.
    return FileResponse(path, media_type='application/pdf', filename=document.name, content_disposition_type='attachment')


@router.post('/documents/{document_id}/retry', status_code=202)
def retry(document_id: str, user: User = Depends(require('documents.manage')), db: Session = Depends(get_db)):
    rate_limit(db, 'retry:' + user.id, 10, 600)
    document = owned_doc(db, document_id, user)
    if document.status != 'failed':
        raise HTTPException(409, 'Only failed documents can be retried')
    document.status, document.attempts, document.error = 'queued', 0, None
    db.commit()
    return doc_json(document)


@router.delete('/documents/{document_id}', status_code=202)
def delete_document(document_id: str, user: User = Depends(require('documents.manage')), db: Session = Depends(get_db)):
    doc = owned_doc(db, document_id, user)
    # Erase conversations referencing the deleted document, including saved excerpts.
    for conv in db.scalars(select(Conversation).where(Conversation.owner_id == user.id)):
        if doc.id in conv.document_ids:
            db.delete(conv)
    doc.status = 'deleting'
    doc.lease_until = None
    audit(db, user.id, 'document.delete', doc.id)
    db.commit()
    return {'message': 'Deletion queued. Document access revoked immediately.'}


@router.get('/conversations')
def conversations(user: User = Depends(require('chat.use')), db: Session = Depends(get_db)):
    return [conv_json(c) for c in db.scalars(select(Conversation).where(Conversation.owner_id == user.id,
        Conversation.expires_at > utcnow()).order_by(Conversation.last_activity_at.desc()))]


@router.post('/conversations', status_code=201)
def new_conversation(body: schemas.NewConversation, user: User = Depends(require('chat.use')), db: Session = Depends(get_db)):
    rate_limit(db, 'new-chat:' + user.id, 20, 600)
    for document_id in set(body.document_ids):
        if owned_doc(db, document_id, user).status != 'ready':
            raise HTTPException(409, 'All selected documents must be ready')
    now = utcnow()
    conv = Conversation(owner_id=user.id, title=body.title, document_ids=list(set(body.document_ids)),
        created_at=now, last_activity_at=now, expires_at=now + timedelta(hours=24))
    db.add(conv)
    db.commit()
    return conv_json(conv)


@router.get('/conversations/{conversation_id}')
def conversation(conversation_id: str, user: User = Depends(require('chat.use')), db: Session = Depends(get_db)):
    conv = owned_conversation(db, conversation_id, user)
    messages = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at, Message.id))
    return conv_json(conv) | {'messages': [message_json(m) for m in messages]}


@router.delete('/conversations/{conversation_id}', status_code=204)
def delete_conversation(conversation_id: str, user: User = Depends(require('chat.use')), db: Session = Depends(get_db)):
    db.delete(owned_conversation(db, conversation_id, user, lock=True))
    db.commit()


@router.post('/conversations/{conversation_id}/messages')
def ask(conversation_id: str, body: schemas.Question, user: User = Depends(require('chat.use')), db: Session = Depends(get_db)):
    rate_limit(db, 'ask:' + user.id, 10, 60)
    # Serialize user requests for daily quota and conversation activity.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    conv = owned_conversation(db, conversation_id, user, lock=True)
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(select(func.count()).select_from(Usage).where(Usage.user_id == user.id,
        Usage.kind == 'question', Usage.created_at >= today))
    if count >= db.get(AppLimits, 1).daily_questions:
        raise HTTPException(429, 'Daily question allowance reached')
    docs = [owned_doc(db, document_id, user) for document_id in conv.document_ids]
    if any(d.status != 'ready' for d in docs):
        raise HTTPException(409, 'Selected document is unavailable')
    try:
        content, sources = ai.answer(body.content, user.id, docs)
    except ai.AIServiceError as exc:
        raise HTTPException(503, str(exc))
    except Exception:
        # No content, provider response or exception body is logged.
        raise HTTPException(503, 'AI service unavailable. Verify provider configuration and retry.')
    now = utcnow()
    # A request starting before expiry cannot revive a chat after expiry.
    if conv.expires_at <= now:
        db.rollback()
        raise HTTPException(404, 'Conversation expired while processing')
    question_message = Message(conversation_id=conv.id, role='user', content=body.content, created_at=now)
    reply = Message(conversation_id=conv.id, role='assistant', content=content, created_at=now + timedelta(microseconds=1),
                    sources=[Source(**s) for s in sources])
    db.add_all([question_message, reply, Usage(user_id=user.id, kind='question')])
    conv.last_activity_at, conv.expires_at = now, now + timedelta(hours=24)
    db.commit()
    return {'messages': [message_json(question_message), message_json(reply)], 'expires_at': iso(conv.expires_at)}


@router.get('/admin/users')
def admin_users(user: User = Depends(require('users.manage')), db: Session = Depends(get_db), offset: int = 0):
    return [user_json(u) for u in db.scalars(select(User).order_by(User.created_at.desc()).offset(max(0, offset)).limit(100))]


@router.patch('/admin/users/{user_id}')
def admin_user(user_id: str, body: schemas.UserUpdate, user: User = Depends(require('users.manage')), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    role = db.get(Role, body.role_id)
    if not target or not role:
        raise HTTPException(404, 'User or role not found')
    if target.id == user.id and (not body.active or body.role_id != user.role_id):
        raise HTTPException(400, 'Cannot suspend yourself or change your own role')
    target.active, target.role_id = body.active, body.role_id
    target.token_version += 1
    db.execute(delete(AuthSession).where(AuthSession.user_id == target.id))
    audit(db, user.id, 'admin.user_update', target.id)
    db.commit()
    db.refresh(target)
    return user_json(target)


@router.get('/admin/roles')
def roles(user: User = Depends(require('roles.manage')), db: Session = Depends(get_db)):
    return {'roles': [{'id': r.id, 'name': r.name, 'permissions': [p.name for p in r.permissions]} for r in db.scalars(select(Role))],
            'permissions': [p.name for p in db.scalars(select(Permission))]}


def permission_rows(db, names):
    rows = list(db.scalars(select(Permission).where(Permission.name.in_(names))))
    if len(rows) != len(set(names)):
        raise HTTPException(422, 'Unknown permission')
    return rows


@router.post('/admin/roles', status_code=201)
def create_role(body: schemas.RoleCreate, user: User = Depends(require('roles.manage')), db: Session = Depends(get_db)):
    role = Role(name=body.name, permissions=permission_rows(db, body.permissions))
    db.add(role)
    try:
        db.flush()
        audit(db, user.id, 'admin.role_created', str(role.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Role name already exists')
    return {'id': role.id}


@router.put('/admin/roles/{role_id}')
def edit_role(role_id: int, body: schemas.RoleUpdate, user: User = Depends(require('roles.manage')), db: Session = Depends(get_db)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, 'Role not found')
    if role.name in {'admin', 'user'}:
        raise HTTPException(400, 'Built-in roles are immutable; create a custom role')
    role.permissions = permission_rows(db, body.permissions)
    audit(db, user.id, 'admin.role_updated', str(role.id))
    db.commit()
    return {'message': 'Permissions updated'}


@router.put('/admin/limits')
def update_limits(body: schemas.LimitsUpdate, user: User = Depends(require('settings.manage')), db: Session = Depends(get_db)):
    row = db.get(AppLimits, 1)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    audit(db, user.id, 'admin.limits_updated')
    db.commit()
    return body


@router.get('/admin/stats')
def stats(user: User = Depends(require('monitor.read')), db: Session = Depends(get_db)):
    return {'users': db.scalar(select(func.count()).select_from(User)),
            'documents': db.scalar(select(func.count()).select_from(Document)),
            'active_conversations': db.scalar(select(func.count()).select_from(Conversation).where(Conversation.expires_at > utcnow())),
            'questions_today': db.scalar(select(func.count()).select_from(Usage).where(Usage.kind == 'question',
                Usage.created_at >= utcnow().replace(hour=0, minute=0, second=0, microsecond=0))),
            'processing': [{'id': d.id, 'status': d.status, 'pages': d.pages, 'error': d.error}
                for d in db.scalars(select(Document).order_by(Document.created_at.desc()).limit(100))]}


@router.get('/admin/audit')
def audit_logs(user: User = Depends(require('audit.read')), db: Session = Depends(get_db), offset: int = 0):
    return [{'id': a.id, 'actor_id': a.actor_id, 'action': a.action, 'target_id': a.target_id,
             'created_at': iso(a.created_at)} for a in db.scalars(select(Audit).order_by(Audit.id.desc()).offset(max(0, offset)).limit(100))]
