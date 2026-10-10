"""Execute migrations and the API/security suite in a new disposable XAMPP schema.

Local development convenience for default passwordless-root XAMPP only. Other
installations should supply MYSQL_TEST_DATABASE_URL as described in TESTING.md.
No existing schemas are modified. Only the generated test schema is dropped.
"""
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MYSQL = Path('C:/xampp/mysql/bin/mysql.exe')


def sql(statement):
    result = subprocess.run([str(MYSQL), '-u', 'root', '--batch'], input=statement,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('XAMPP SQL operation failed; no credentials or SQL payload printed')
    return result.stdout


def run():
    database = 'docqa_' + uuid.uuid4().hex[:12] + '_test'
    if not re.fullmatch(r'docqa_[0-9a-f]{12}_test', database):
        raise RuntimeError('Invalid disposable schema name')
    if sql(f"SHOW DATABASES LIKE '{database}';").strip():
        raise RuntimeError('Unexpected existing schema; no changes made')
    sql(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    env = os.environ.copy()
    url = f'mysql+pymysql://root@127.0.0.1:3306/{database}?charset=utf8mb4'
    env['DATABASE_URL'] = url
    env['MYSQL_TEST_DATABASE_URL'] = url
    try:
        for command in [['alembic', 'upgrade', 'head'], ['alembic', 'check'],
                        ['pytest', '-q', 'tests/test_security.py', 'tests/test_retention.py', 'tests/test_documents_rag.py', 'tests/test_worker.py', 'tests/test_mysql_concurrency.py'],
                        ['alembic', 'downgrade', 'base'], ['alembic', 'upgrade', 'head']]:
            result = subprocess.run([sys.executable, '-m', *command], cwd=ROOT, env=env)
            if result.returncode:
                return result.returncode
        print('Disposable XAMPP migration roundtrip and backend suite completed.')
        return 0
    finally:
        sql(f'DROP DATABASE `{database}`;')
        print('Only the generated disposable test schema was removed.')


if __name__ == '__main__':
    raise SystemExit(run())
