"""Database connection, session management, and SQLite engine configuration.

Provides both synchronous and asynchronous session factories with SQLite
WAL (Write-Ahead Logging) and Foreign Key constraint enforcement.
"""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# SQLite Performance and Foreign Key PRAGMAs
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, foreign keys, and optimized pragmas for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# Base Declarative Class for SQLAlchemy Models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Synchronous Engine & Session Factory (for background threads & migrations)
sync_engine = create_engine(
    settings.SQLITE_DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Asynchronous Engine & Session Factory (lazy fallback)
_async_engine = None
_AsyncSessionLocal = None


def get_async_engine():
    """Lazily initializes and returns the async SQLAlchemy engine."""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.ASYNC_SQLITE_DATABASE_URL,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
        )
    return _async_engine


def get_async_session_factory():
    """Lazily returns the async sessionmaker."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = get_async_engine()
        _AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


def init_db() -> None:
    """Synchronously creates all database tables."""
    settings.ensure_directories()
    Base.metadata.create_all(bind=sync_engine)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an asynchronous DB session."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency / context helper for obtaining a synchronous DB session."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
