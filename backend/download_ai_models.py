"""Download configured real models through the running local Ollama API."""
import json
import httpx
from app.config import settings


def download():
    if settings.ai_provider != 'ollama':
        raise SystemExit('This helper is for local Ollama only.')
    with httpx.Client(timeout=httpx.Timeout(180, connect=10)) as client:
        for model in dict.fromkeys([settings.embedding_model, settings.llm_model]):
            print('Downloading configured model:', model, flush=True)
            last_percent = -10
            with client.stream('POST', settings.ai_base_url.rstrip('/') + '/api/pull',
                               json={'model': model, 'stream': True}) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    progress = json.loads(line)
                    if 'error' in progress:
                        raise RuntimeError('Model download failed. Check the configured model name and network connection.')
                    if progress.get('total'):
                        percent = int(100 * progress.get('completed', 0) / progress['total'])
                        if percent >= last_percent + 10:
                            print(model, str(percent) + '%', flush=True)
                            last_percent = percent
                    elif progress.get('status') == 'success':
                        print(model, 'ready', flush=True)
    print('Configured embedding and chat models downloaded.', flush=True)


if __name__ == '__main__':
    download()
