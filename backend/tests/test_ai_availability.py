import httpx
import pytest
from app import ai


def test_connection_error_is_actionable_without_leaking_payloads(monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError('private internal connection details')
    monkeypatch.setattr(httpx.Client, 'post', unavailable)
    with pytest.raises(ai.AIServiceError, match='Cannot connect to Ollama') as caught:
        ai.provider.embed(['private document text'])
    assert 'private' not in str(caught.value)


def test_missing_model_has_safe_diagnostic(monkeypatch):
    def missing(*args, **kwargs):
        response = httpx.Response(404, request=httpx.Request('POST', 'http://localhost/api/embed'),
                                  json={'error': 'private provider response'})
        return response
    monkeypatch.setattr(httpx.Client, 'post', missing)
    with pytest.raises(ai.AIServiceError, match='AI model unavailable') as caught:
        ai.provider.embed(['private document text'])
    assert 'private' not in str(caught.value)


def test_status_requires_authentication_and_reports_missing_service(client, auth, monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError('unavailable')
    monkeypatch.setattr(httpx, 'get', unavailable)
    response = client.get('/api/ai/status')
    assert response.status_code == 200
    assert response.json()['available'] is False
    assert 'Ollama is not running' in response.json()['message']
    client.cookies.clear()
    assert client.get('/api/ai/status').status_code == 401


def test_separate_remote_chat_keeps_embeddings_local(monkeypatch):
    monkeypatch.setattr(ai.settings, 'chat_provider', 'openai-compatible')
    monkeypatch.setattr(ai.settings, 'chat_base_url', 'https://example.invalid/v1')
    monkeypatch.setattr(ai.settings, 'chat_api_key', 'unit-test-key')
    calls = []
    def respond(client, url, **kwargs):
        calls.append((url, kwargs))
        payload = ({'embeddings': [[1, 0]]} if url.endswith('/api/embed') else
                   {'choices': [{'message': {'content': '{"supported":false,"evidence":[]}'}}]})
        return httpx.Response(200, request=httpx.Request('POST', url), json=payload)
    monkeypatch.setattr(httpx.Client, 'post', respond)
    assert ai.provider.embed(['Document']) == [[1, 0]]
    assert ai.provider.select_evidence('Question', [{'text': 'Document'}])['supported'] is False
    assert calls[0][0].endswith('/api/embed')
    assert 'headers' not in calls[0][1]
    assert calls[1][0] == 'https://example.invalid/v1/chat/completions'
    assert calls[1][1]['headers']['Authorization'] == 'Bearer unit-test-key'
