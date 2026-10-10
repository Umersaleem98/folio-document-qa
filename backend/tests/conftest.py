import os
from pathlib import Path
import tempfile

# Explicit test-only SQLite DB; production remains MySQL.
TEST_DIR = Path(tempfile.mkdtemp(prefix='docqa-tests-'))
integration_url = os.environ.get('MYSQL_TEST_DATABASE_URL')
if integration_url:
    from sqlalchemy.engine import make_url
    parsed = make_url(integration_url)
    if not parsed.drivername.startswith('mysql') or not parsed.database or not parsed.database.endswith('_test'):
        raise RuntimeError('MYSQL_TEST_DATABASE_URL must use an explicitly disposable *_test database')
os.environ['DATABASE_URL'] = integration_url or ('sqlite:///' + (TEST_DIR / 'test.db').as_posix())
os.environ['JWT_SECRET'] = 'test-only-secret-which-is-longer-than-32-characters'
os.environ['STORAGE_DIR'] = str(TEST_DIR / 'data')
os.environ['COOKIE_SECURE'] = 'false'

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.main import app
from app.cli import initialize


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    initialize()
    yield


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def register_login(client, email='one@example.com'):
    result = client.post('/api/auth/register', json={'email': email, 'name': 'Researcher', 'password': 'StrongPassword123!'})
    assert result.status_code == 201, result.text
    result = client.post('/api/auth/login', json={'email': email, 'password': 'StrongPassword123!'})
    assert result.status_code == 200, result.text
    client.headers['X-CSRF-Token'] = client.cookies['csrf_token']
    return result.json()


@pytest.fixture
def auth(client):
    return register_login(client)
