"""Package only reviewable source/config examples; never .env or runtime data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
destination = root.parent / 'document-qa-source.zip'
files = [root / '.gitignore', root / 'README.md', root / 'package_source.py', root / 'Configure-Folio.cmd']
files += [root / 'backend' / name for name in [
    '.env.example', 'requirements.txt', 'requirements.lock.txt', 'alembic.ini',
    'setup_local.py', 'verify_xampp.py',
    'configure_project.py',
    'install_portable_ollama.py', 'start_local_ai.py', 'start-ai.ps1', 'download_ai_models.py',
]]
files += [root / 'frontend' / name for name in [
    'package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html',
]]
for directory in ['docs', 'backend/app', 'backend/alembic', 'backend/tests', 'frontend/src', 'frontend/public']:
    files += [p for p in (root / directory).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.db'}]

with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        relative = path.relative_to(root)
        if path.name == '.env' or any(part in {'.venv', 'node_modules', 'data'} for part in relative.parts):
            raise RuntimeError('Private/runtime file rejected')
        archive.write(path, 'document-qa/' + relative.as_posix())
with ZipFile(destination) as archive:
    assert not any(name.endswith('/.env') for name in archive.namelist())
    print(f'Packaged {len(archive.namelist())} source files; secrets and runtime data excluded.')
print(destination)
