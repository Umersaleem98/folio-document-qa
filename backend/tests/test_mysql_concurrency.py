from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.db import engine, SessionLocal
from app.main import app
from app.models import AppLimits, Document
from app import routes
from .test_documents_rag import pdf_bytes
from .test_retention import seed_chat

pytestmark = pytest.mark.skipif(engine.dialect.name == 'sqlite',
    reason='Validates MySQL row-lock serialization; run with MYSQL_TEST_DATABASE_URL')


def parallel_requests(client, request):
    cookies = {'access_token': client.cookies['access_token'], 'csrf_token': client.cookies['csrf_token']}
    def invoke(_):
        with TestClient(app, cookies=cookies, headers={'X-CSRF-Token': cookies['csrf_token']}) as separate:
            return request(separate).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        return sorted(executor.map(invoke, range(2)))


def test_parallel_uploads_cannot_exceed_quota(client, auth):
    with SessionLocal() as db:
        db.get(AppLimits, 1).max_documents = 1
        db.commit()
    statuses = parallel_requests(client, lambda separate: separate.post('/api/documents',
        files={'file': ('quota.pdf', pdf_bytes(), 'application/pdf')}))
    assert statuses == [202, 422]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Document).where(Document.owner_id == auth['id'])) == 1


def test_parallel_questions_cannot_exceed_daily_allowance(client, auth, monkeypatch):
    conversation_id, _ = seed_chat(auth['id'])
    with SessionLocal() as db:
        db.get(AppLimits, 1).daily_questions = 1
        db.commit()
    monkeypatch.setattr(routes.ai, 'answer', lambda *_: ('Insufficient information', []))
    statuses = parallel_requests(client, lambda separate: separate.post(
        '/api/conversations/' + conversation_id + '/messages', json={'content': 'Question?'}))
    assert statuses == [200, 429]
