from dotenv import dotenv_values
from configure_project import save_settings


def test_settings_save_preserves_secret_and_quotes_values(tmp_path):
    path = tmp_path / '.env'
    secret = 'existing-jwt-secret-that-must-not-change'
    path.write_text('JWT_SECRET=' + secret + '\nUNRELATED=keep\n', encoding='utf-8')
    save_settings(path, {'CHAT_API_KEY': 'test-key-with-#-and-"', 'CHAT_PROVIDER': 'openai-compatible'})
    values = dotenv_values(path)
    assert values['JWT_SECRET'] == secret
    assert values['UNRELATED'] == 'keep'
    assert values['CHAT_API_KEY'] == 'test-key-with-#-and-"'
    assert not list(tmp_path.glob('.env-write-*'))


def test_first_setup_generates_secret(tmp_path):
    path = tmp_path / '.env'
    save_settings(path, {'JWT_SECRET': 'REPLACE_EXAMPLE', 'CHAT_API_KEY': ''})
    assert len(dotenv_values(path)['JWT_SECRET']) >= 32
