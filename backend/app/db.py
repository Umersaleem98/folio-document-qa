from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


def utcnow():
    # MySQL DATETIME is timezone-naive: all stored values are explicitly UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


engine_options = {'connect_args': {'check_same_thread': False}} if settings.database_url.startswith('sqlite') else {
    # Quota reads after owner-row locks must see preceding committed requests.
    'isolation_level': 'READ COMMITTED',
}
engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True, **engine_options)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_fk(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
else:
    @event.listens_for(engine, 'connect')
    def mysql_utc(conn, _):
        cur = conn.cursor()
        cur.execute("SET time_zone = '+00:00'")
        cur.close()
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
