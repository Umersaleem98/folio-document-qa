"""Start the official portable Ollama server with local project model storage."""
import os
import subprocess
from pathlib import Path
from install_portable_ollama import install

root = Path(__file__).resolve().parent
runtime = root / 'data' / 'ollama-runtime' / 'ollama.exe'
if not runtime.exists():
    install()
env = os.environ.copy()
env['OLLAMA_MODELS'] = str(root / 'data' / 'models')
env['OLLAMA_HOST'] = '127.0.0.1:11434'
env['OLLAMA_NO_CLOUD'] = '1'
env['OLLAMA_DEBUG_LOG_REQUESTS'] = 'false'
raise SystemExit(subprocess.call([str(runtime), 'serve'], env=env))
