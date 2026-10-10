from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import SessionLocal, utcnow
from app.main import app
from app.models import AuthSession, Role, User
from .conftest import register_login


def test_registration_rejects_admin_role(client):
    assert client.post('/api/auth/register', json={'email':'evil@example.com','name':'Evil','password':'StrongPassword123!','role_id':1}).status_code == 422


def test_session_status_preserves_protected_routes(client):
    response = client.get('/api/auth/session')
    assert response.status_code == 200 and response.json() == {'user': None}
    assert response.headers['cache-control'] == 'no-store'
    assert client.get('/api/auth/me').status_code == 401
    client.cookies.set('access_token', 'invalid-token', path='/api')
    assert client.get('/api/auth/session').json() == {'user': None}
    register_login(client, 'session@example.com')
    assert client.get('/api/auth/session').json()['user']['email'] == 'session@example.com'
    assert client.get('/api/auth/me').status_code == 200


def test_argon2_admin_denial_and_csrf(client, auth):
    with SessionLocal() as db:
        user = db.get(User, auth['id'])
        assert user.password_hash.startswith('$argon2id$')
        assert user.role.name == 'user'
    assert client.get('/api/admin/users').status_code == 403
    del client.headers['X-CSRF-Token']
    assert client.patch('/api/profile', json={'name':'Changed'}).status_code == 403
    assert client.post('/api/auth/login', headers={'Origin':'https://evil.example'}, json={'email':auth['email'],'password':'StrongPassword123!'}).status_code == 403


def test_logout_revokes_token(client, auth):
    old = client.cookies['access_token']
    assert client.post('/api/auth/logout').status_code == 204
    client.cookies.set('access_token', old, path='/api')
    assert client.get('/api/auth/me').status_code == 401


def test_expired_session_and_suspended_account(client, auth):
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession).where(AuthSession.user_id==auth['id']))
        session.expires_at = utcnow()-timedelta(seconds=1)
        db.commit()
    assert client.get('/api/auth/me').status_code == 401
    client.post('/api/auth/login', json={'email':auth['email'],'password':'StrongPassword123!'})
    with SessionLocal() as db:
        db.get(User,auth['id']).active=False
        db.commit()
    assert client.get('/api/auth/me').status_code == 401


def test_admin_suspends_user_and_cannot_suspend_self(client,auth):
    with SessionLocal() as db:
        db.get(User,auth['id']).role_id=db.scalar(select(Role).where(Role.name=='admin')).id
        db.commit()
    with TestClient(app) as other:
        second=register_login(other,'two@example.com')
        assert client.patch('/api/admin/users/'+second['id'],json={'active':False,'role_id':second['role_id']}).status_code==200
        assert other.get('/api/auth/me').status_code==401
    assert client.patch('/api/admin/users/'+auth['id'],json={'active':False,'role_id':auth['role_id']}).status_code==400


def test_rate_limit_persists(client):
    for _ in range(10):
        assert client.post('/api/auth/login',json={'email':'unknown@example.com','password':'bad'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'unknown@example.com','password':'bad'}).status_code==429


def test_validation_does_not_echo_sensitive_input(client):
    response=client.post('/api/auth/register',json={'email':'bad','name':'Test','password':'private'})
    assert response.status_code==422
    assert 'private' not in response.text


def test_password_change_revokes_all_sessions(client,auth):
    with TestClient(app) as other:
        response=other.post('/api/auth/login',json={'email':auth['email'],'password':'StrongPassword123!'})
        assert response.status_code==200
        assert client.post('/api/profile/password',json={'current_password':'StrongPassword123!','new_password':'NewStrongPassword123!'}).status_code==204
        assert other.get('/api/auth/me').status_code==401
        assert client.get('/api/auth/me').status_code==401
