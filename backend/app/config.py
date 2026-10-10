from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'mysql+pymysql://docqa:change@127.0.0.1/document_qa'
    jwt_secret: str = Field(min_length=32)
    environment: str = 'development'
    cors_origins: list[str] = ['http://localhost:5173']
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    storage_dir: Path = Path('./data')
    cookie_secure: bool = False
    ai_provider: str = 'ollama'
    ai_base_url: str = 'http://127.0.0.1:11434'
    ai_api_key: str = ''
    # Optional independent chat endpoint; embeddings remain on AI_PROVIDER.
    chat_provider: str = ''
    chat_base_url: str = ''
    chat_api_key: str = ''
    llm_model: str = 'qwen2.5:0.5b'
    embedding_model: str = 'nomic-embed-text'
    embedding_version: str = 'v1'
    max_distance: float = Field(default=0.45, ge=0, le=2)
    cleanup_interval_seconds: int = Field(default=60, ge=1, le=3600)
    worker_poll_seconds: int = Field(default=2, ge=1)
    max_pdf_pages: int = 500
    max_extracted_characters: int = 2_000_000

    @model_validator(mode='after')
    def validate_security(self):
        if self.jwt_secret.startswith('REPLACE_'):
            raise ValueError('Generate a real JWT_SECRET; example secret is forbidden')
        if self.environment == 'production' and (not self.cookie_secure or '*' in self.cors_origins):
            raise ValueError('Production requires secure cookies and explicit CORS origins')
        if self.ai_provider not in {'ollama', 'openai-compatible'}:
            raise ValueError('AI_PROVIDER must be ollama or openai-compatible')
        if self.chat_provider not in {'', 'ollama', 'openai-compatible'}:
            raise ValueError('CHAT_PROVIDER must be ollama or openai-compatible')
        if self.chat_provider and not self.chat_base_url:
            raise ValueError('CHAT_BASE_URL is required when CHAT_PROVIDER is set')
        return self


settings = Settings()
