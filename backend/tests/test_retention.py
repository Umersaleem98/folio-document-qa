from datetime import timedelta
from sqlalchemy import func, select
from app.db import SessionLocal, utcnow
from app.models import Conversation, Document, Message, Source, User
from app.retention import cleanup_expired
from app import routes


def seed_chat(owner,expired=False):
    now=utcnow()
    with SessionLocal() as db:
        doc=Document(owner_id=owner,name='Evidence.pdf',size=100,status='ready')
        db.add(doc);db.flush()
        conv=Conversation(owner_id=owner,title='Research',document_ids=[doc.id],
            expires_at=now+timedelta(hours=-1 if expired else 24))
        db.add(conv);db.flush()
        msg=Message(conversation_id=conv.id,role='assistant',content='Private answer',
            sources=[Source(document_id=doc.id,document_name=doc.name,page=1,excerpt='Private evidence')])
        db.add(msg);db.commit()
        return conv.id,doc.id


def test_expired_api_and_cascade_cleanup_preserves_documents_and_users(client,auth):
    expired_id,doc_id=seed_chat(auth['id'],expired=True)
    live_id,_=seed_chat(auth['id'])
    assert client.get('/api/conversations/'+expired_id).status_code==404
    assert client.post('/api/conversations/'+expired_id+'/messages',json={'content':'Question?'}).status_code==404
    assert [c['id'] for c in client.get('/api/conversations').json()]==[live_id]
    assert cleanup_expired()==1
    assert cleanup_expired()==0
    with SessionLocal() as db:
        assert db.get(Conversation,expired_id) is None
        assert db.get(Document,doc_id) is not None
        assert db.get(User,auth['id']) is not None
        assert db.scalar(select(func.count()).select_from(Message))==1
        assert db.scalar(select(func.count()).select_from(Source))==1


def test_exact_boundary_and_restart_cleanup(client,auth):
    conv_id,_=seed_chat(auth['id'])
    with SessionLocal() as db:
        boundary=utcnow()
        db.get(Conversation,conv_id).expires_at=boundary
        db.commit()
    assert cleanup_expired(boundary)==1
    conv_id,_=seed_chat(auth['id'],expired=True)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app):pass
    with SessionLocal() as db:
        assert db.get(Conversation,conv_id) is None


def test_success_extends_activity_but_reads_and_failures_do_not(client,auth,monkeypatch):
    conv_id,doc_id=seed_chat(auth['id'])
    with SessionLocal() as db:
        before=utcnow()+timedelta(hours=2)
        db.get(Conversation,conv_id).expires_at=before
        db.commit()
    assert client.get('/api/conversations/'+conv_id).status_code==200
    with SessionLocal() as db:assert db.get(Conversation,conv_id).expires_at==before
    def fail(*args):raise RuntimeError('private provider content')
    monkeypatch.setattr(routes.ai,'answer',fail)
    response=client.post('/api/conversations/'+conv_id+'/messages',json={'content':'Question?'})
    assert response.status_code==503
    assert 'private' not in response.text
    with SessionLocal() as db:assert db.get(Conversation,conv_id).expires_at==before
    monkeypatch.setattr(routes.ai,'answer',lambda *args:('Evidence answer',[{'document_id':doc_id,'document_name':'Evidence.pdf','page':1,'excerpt':'Exact evidence'}]))
    response=client.post('/api/conversations/'+conv_id+'/messages',json={'content':'Question?'})
    assert response.status_code==200,response.text
    with SessionLocal() as db:
        conv=db.get(Conversation,conv_id)
        assert conv.expires_at-conv.last_activity_at==timedelta(hours=24)
        assert conv.expires_at>before


def test_inflight_answer_cannot_revive_expired_conversation(client,auth,monkeypatch):
    conv_id,_=seed_chat(auth['id'])
    deadline=utcnow()+timedelta(seconds=10)
    with SessionLocal() as db:
        db.get(Conversation,conv_id).expires_at=deadline
        db.commit()
    def late_answer(*args):
        monkeypatch.setattr(routes,'utcnow',lambda:deadline+timedelta(seconds=1))
        return 'Late answer',[]
    monkeypatch.setattr(routes.ai,'answer',late_answer)
    assert client.post('/api/conversations/'+conv_id+'/messages',json={'content':'Question?'}).status_code==404
    with SessionLocal() as db:
        assert db.get(Conversation,conv_id).expires_at==deadline
        assert db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id==conv_id))==1
