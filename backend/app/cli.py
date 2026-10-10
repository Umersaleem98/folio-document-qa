import argparse
import getpass
from sqlalchemy import select
from .db import SessionLocal
from .models import AppLimits, Audit, Document, Permission, Role, User
from .security import hasher
from .retention import cleanup_expired

PERMISSIONS = ['documents.manage', 'chat.use', 'users.manage', 'roles.manage', 'settings.manage', 'monitor.read', 'audit.read']


def initialize():
    with SessionLocal() as db:
        for name in PERMISSIONS:
            if not db.scalar(select(Permission).where(Permission.name == name)):
                db.add(Permission(name=name))
        db.flush()
        all_permissions = list(db.scalars(select(Permission)))
        for name, names in [('user', ['documents.manage', 'chat.use']), ('admin', PERMISSIONS)]:
            if not db.scalar(select(Role).where(Role.name == name)):
                db.add(Role(name=name, permissions=[p for p in all_permissions if p.name in names]))
        if not db.get(AppLimits, 1):
            db.add(AppLimits(id=1))
        db.commit()


def create_admin():
    from pydantic import TypeAdapter, EmailStr
    initialize()
    email = str(TypeAdapter(EmailStr).validate_python(input('Administrator email: ').strip())).lower()
    name = input('Administrator name: ').strip()
    password = getpass.getpass('Password (at least 12 characters): ')
    if len(password) < 12 or len(password) > 128 or not name or len(name) > 100:
        raise SystemExit('Invalid name or password length')
    if getpass.getpass('Confirm password: ') != password:
        raise SystemExit('Passwords differ')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit('Email already registered; use dashboard to manage existing users')
        role = db.scalar(select(Role).where(Role.name == 'admin'))
        user = User(email=email, name=name, password_hash=hasher.hash(password), role_id=role.id)
        db.add(user)
        db.flush()
        db.add(Audit(actor_id=user.id, action='admin.bootstrap', target_id=user.id))
        db.commit()
    print('Administrator created.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init', 'create-admin', 'cleanup', 'reindex'])
    command = parser.parse_args().command
    if command == 'init':
        initialize()
        print('Roles, permissions and limits initialized.')
    elif command == 'create-admin':
        create_admin()
    elif command == 'reindex':
        with SessionLocal() as db:
            documents = list(db.scalars(select(Document).where(Document.status == 'ready')))
            for document in documents:
                document.status, document.attempts, document.error, document.lease_until = 'queued', 0, None, None
            db.add(Audit(action='document.reindex_requested'))
            db.commit()
        print(f'Queued {len(documents)} documents for reindexing.')
    else:
        print(f'Deleted {cleanup_expired()} expired conversations.')
