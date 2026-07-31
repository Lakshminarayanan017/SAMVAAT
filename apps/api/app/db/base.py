"""The SQLAlchemy declarative base and shared column types."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, TypeDecorator
from sqlalchemy.orm import DeclarativeBase

#: Explicit constraint naming. Without it, Alembic generates anonymous
#: constraints that cannot be dropped by name in a later migration, and the
#: first time that matters is the migration you cannot roll back.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UtcDateTime(TypeDecorator):
    """A datetime that is always timezone-aware UTC, on every backend.

    SQLite has no native timezone support and hands back naive datetimes. A
    naive value compared against an aware one raises at runtime, usually in the
    retention purge — the one job where being wrong means keeping a learner's
    voice recording longer than we promised.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
