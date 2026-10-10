from datetime import timedelta
import threading
import time
from app import worker
from app.config import settings
from app.db import SessionLocal, utcnow
from app.models import Conversation, Document
from .test_documents_rag import pdf_bytes
from .test_retention import seed_chat


def test_crashed_processing_lease_is_reclaimed(client, auth, monkeypatch):
    result = client.post('/api/documents', files={'file': ('recovery.pdf', pdf_bytes(), 'application/pdf')})
    assert result.status_code == 202
    document_id = result.json()['id']
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        doc.status = 'processing'
        doc.lease_until = utcnow() - timedelta(minutes=1)
        doc.attempts = 1
        db.commit()
    monkeypatch.setattr(worker.ai, 'index_chunks', lambda *_: None)
    assert worker.process_one()
    with SessionLocal() as db:
        assert db.get(Document, document_id).status == 'ready'
        assert db.get(Document, document_id).attempts == 2


def test_cleanup_continues_during_stalled_document_job(client, auth, monkeypatch):
    conversation_id, _ = seed_chat(auth['id'], expired=True)
    entered, release = threading.Event(), threading.Event()
    stop = threading.Event()
    monkeypatch.setattr(worker, 'stop', stop)
    monkeypatch.setattr(settings, 'cleanup_interval_seconds', 1)
    def blocked_job():
        entered.set()
        release.wait(5)
    monkeypatch.setattr(worker, 'process_one', blocked_job)
    thread = threading.Thread(target=worker.run)
    thread.start()
    try:
        assert entered.wait(2)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            with SessionLocal() as db:
                if db.get(Conversation, conversation_id) is None:
                    break
            time.sleep(0.05)
        with SessionLocal() as db:
            assert db.get(Conversation, conversation_id) is None
    finally:
        stop.set()
        release.set()
        thread.join(5)
    assert not thread.is_alive()
