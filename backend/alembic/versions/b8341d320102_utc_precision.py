"""Preserve UTC microseconds on MySQL/MariaDB for deterministic message order."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'b8341d320102'
down_revision = '72d4000a68cc'
branch_labels = None
depends_on = None

COLUMNS = {
    'users': [('created_at', False)],
    'auth_sessions': [('expires_at', False)],
    'documents': [('lease_until', True), ('created_at', False)],
    'conversations': [('created_at', False), ('last_activity_at', False), ('expires_at', False)],
    'messages': [('created_at', False)],
    'usage_logs': [('created_at', False)],
    'audit_records': [('created_at', False)],
    'rate_buckets': [('reset_at', False)],
}


def upgrade():
    if op.get_bind().dialect.name in {'mysql', 'mariadb'}:
        for table, columns in COLUMNS.items():
            for column, nullable in columns:
                op.alter_column(table, column, existing_type=sa.DateTime(),
                                type_=mysql.DATETIME(fsp=6), existing_nullable=nullable)


def downgrade():
    if op.get_bind().dialect.name in {'mysql', 'mariadb'}:
        for table, columns in COLUMNS.items():
            for column, nullable in columns:
                op.alter_column(table, column, existing_type=mysql.DATETIME(fsp=6),
                                type_=sa.DateTime(), existing_nullable=nullable)
