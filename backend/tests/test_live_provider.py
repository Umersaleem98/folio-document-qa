import os
import pytest
from app import worker
from .test_documents_rag import pdf_bytes
import pymupdf


@pytest.mark.skipif(os.environ.get('RUN_LIVE_AI_TESTS') != '1',
                    reason='Requires configured real embedding and LLM endpoints; explicitly opt in')
def test_real_provider_pdf_to_cited_answer(client, auth):
    uploaded = client.post('/api/documents', files={'file': ('live-test.pdf', pdf_bytes(), 'application/pdf')})
    assert uploaded.status_code == 202, uploaded.text
    document_id = uploaded.json()['id']
    assert worker.process_one()

    documents = client.get('/api/documents').json()
    assert documents[0]['status'] == 'ready', documents[0]
    chat = client.post('/api/conversations', json={'document_ids': [document_id]})
    assert chat.status_code == 201, chat.text
    result = client.post('/api/conversations/' + chat.json()['id'] + '/messages',
                         json={'content': 'What is the project deadline?'})
    assert result.status_code == 200, result.text
    reply = result.json()['messages'][1]
    assert reply['sources'], 'Real provider did not return supported evidence; inspect retrieval/model configuration'
    assert 'October 30' in reply['content']
    assert reply['sources'][0]['document_id'] == document_id
    assert reply['sources'][0]['page'] == 1
    assert client.delete('/api/documents/' + document_id).status_code == 202
    assert worker.process_one()


@pytest.mark.skipif(os.environ.get('RUN_LIVE_AI_TESTS') != '1',
                    reason='Requires real configured embedding endpoint')
def test_real_resume_short_questions(client, auth):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), 'JANE DOE\nSoftware Engineer\nProfessional summary\nExperienced web developer.')
    content = pdf.tobytes()
    pdf.close()
    uploaded = client.post('/api/documents', files={'file': ('resume.pdf', content, 'application/pdf')})
    assert uploaded.status_code == 202
    document_id = uploaded.json()['id']
    assert worker.process_one()
    chat = client.post('/api/conversations', json={'document_ids': [document_id]})
    assert chat.status_code == 201
    for question in ['my name', 'tell me aboiut my name']:
        response = client.post('/api/conversations/' + chat.json()['id'] + '/messages',
                               json={'content': question})
        assert response.status_code == 200
        reply = response.json()['messages'][-1]
        assert 'JANE DOE' in reply['content']
        assert reply['sources'][0]['excerpt'] == 'JANE DOE'
        assert reply['sources'][0]['page'] == 1
    assert client.delete('/api/documents/' + document_id).status_code == 202
    assert worker.process_one()
