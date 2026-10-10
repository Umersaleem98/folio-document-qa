"""Durable queue + retention worker. Run exactly one per local Chroma storage directory."""
import logging
import signal
import threading
import time
from datetime import timedelta
from sqlalchemy import or_, select
from . import ai
from .config import settings
from .db import SessionLocal, utcnow
from .documents import extract_chunks, file_path
from .models import Document
from .retention import cleanup_expired

log = logging.getLogger('docqa.worker')
stop = threading.Event()


def process_one():
    with SessionLocal() as db:
        now = utcnow()
        doc = db.scalar(select(Document).where(or_(Document.status == 'queued',
            (Document.status == 'deleting') & or_(Document.lease_until.is_(None), Document.lease_until <= now),
            (Document.status == 'processing') & (Document.lease_until <= now)))
            .order_by(Document.created_at).with_for_update().limit(1))
        if not doc:
            return False
        deleting = doc.status == 'deleting'
        if doc.attempts >= 3 and not deleting:
            doc.status, doc.error = 'failed', 'Processing failed after 3 attempts; retry from the library.'
            db.commit()
            return True
        if deleting:
            # Keep SQL row until filesystem/vector deletion succeeds. Retries survive restart.
            try:
                ai.delete_vectors(doc.id)
                file_path(doc.id).unlink(missing_ok=True)
                db.delete(doc)
                db.commit()
            except Exception:
                db.rollback()
                doc = db.get(Document, doc.id)
                if doc:
                    doc.lease_until = utcnow() + timedelta(seconds=60)
                    db.commit()
                log.warning('Document deletion failed; retry scheduled')
            return True
        doc.status = 'processing'
        doc.attempts += 1
        doc.lease_until = now + timedelta(minutes=30)
        doc_id = doc.id
        db.commit()
        try:
            pages, chunks = extract_chunks(file_path(doc_id))
            ai.index_chunks(doc, chunks)
            db.expire_all()
            doc = db.get(Document, doc_id)
            if doc.status == 'deleting':
                return True
            doc.pages, doc.status, doc.error, doc.lease_until = pages, 'ready', None, None
            db.commit()
        except ai.AIServiceError as exc:
            db.rollback()
            doc = db.get(Document, doc_id)
            if doc and doc.status != 'deleting':
                doc.status, doc.error = 'failed', str(exc)
                db.commit()
        except ValueError as exc:
            db.rollback()
            doc = db.get(Document, doc_id)
            if doc and doc.status != 'deleting':
                doc.status, doc.error = 'failed', str(exc) if str(exc).startswith(('PDF ', 'No extractable', 'Encrypted')) else 'Invalid PDF or AI response.'
                db.commit()
        except Exception:
            db.rollback()
            doc = db.get(Document, doc_id)
            if doc and doc.status != 'deleting':
                doc.status, doc.error = 'failed', 'Processing service unavailable. Check AI configuration and retry.'
                db.commit()
            log.warning('Document processing failed; no document text logged')
        return True


def run():
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    def retention_loop():
        while not stop.is_set():
            try:
                cleanup_expired()
            except Exception:
                log.warning('Retention cleanup failed; retry scheduled')
            stop.wait(settings.cleanup_interval_seconds)
    # Independent sweep: long embedding requests cannot postpone retention.
    cleanup_thread = threading.Thread(target=retention_loop, daemon=True)
    cleanup_thread.start()
    while not stop.is_set():
        try:
            process_one()
        except Exception:
            log.warning('Worker service unavailable; retrying without logging payloads')
        stop.wait(settings.worker_poll_seconds)
    cleanup_thread.join(timeout=5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    run()
