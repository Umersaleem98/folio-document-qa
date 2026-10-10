"""One-time Windows local setup. Creates a dedicated account; prints no secrets.

Does not overwrite an existing .env or database. Run interactively with local XAMPP.
"""
import secrets
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
env_file = root / '.env'
mysql = Path('C:/xampp/mysql/bin/mysql.exe')


def setup():
    if env_file.exists():
        raise SystemExit('.env already exists; no changes made.')
    check = subprocess.run([str(mysql), '-u', 'root', '--batch', '-N', '-e',
                            "SHOW DATABASES LIKE 'document_qa';"], capture_output=True, text=True)
    if check.returncode != 0:
        raise SystemExit('Local root authentication unavailable; follow manual README setup.')
    if check.stdout.strip():
        raise SystemExit('Database already exists; use manual configuration. No changes made.')
    database_password = secrets.token_urlsafe(36)
    sql = f"""CREATE DATABASE document_qa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'docqa'@'127.0.0.1' IDENTIFIED BY '{database_password}';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES ON document_qa.* TO 'docqa'@'127.0.0.1';
"""
    # Credentials are in stdin, never process arguments or terminal output.
    result = subprocess.run([str(mysql), '-u', 'root'], input=sql, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('Database setup failed; inspect account/database existence manually. No secret output.')
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('CHANGE_DATABASE_PASSWORD', database_password).replace(
        'REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS', secrets.token_urlsafe(48))
    with env_file.open('x', encoding='utf-8') as stream:
        stream.write(content)
    print('Created dedicated database/account and private ignored .env. No secrets printed.')


if __name__ == '__main__':
    setup()
