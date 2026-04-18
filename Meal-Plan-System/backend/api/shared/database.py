"""Database - SQLAlchemy engine and session."""
import os

from sqlalchemy import Boolean as SABoolean
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from api.core.config import DATABASE_URL
from api.core.logging_config import get_logger

logger = get_logger("api.database")

_connect_args = {"check_same_thread": False}
if str(DATABASE_URL).startswith("sqlite"):
    # Reduce "database is locked" during concurrent seed + auth (Windows / dev).
    _connect_args["timeout"] = 30.0

if str(DATABASE_URL).startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    )
else:
    engine = create_engine(DATABASE_URL, connect_args=_connect_args)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    if not str(DATABASE_URL).startswith("sqlite"):
        return
    try:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()
    except Exception as e:
        logger.warning("SQLite PRAGMA setup skipped", extra={"error": str(e)})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency - yields DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_users_add_column_ddl(col, dialect) -> str:
    """
    Build ALTER TABLE ... ADD COLUMN for SQLite. NOT NULL columns on a non-empty table
    require a DEFAULT (SQLite limitation); without it, migration fails with misleading errors.
    """
    col_sql = col.type.compile(dialect=dialect)
    typ = str(col_sql)
    name = col.name
    if col.nullable:
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NULL"

    # NOT NULL: must supply DEFAULT if table may already have rows
    if isinstance(col.type, SABoolean):
        arg = getattr(col.default, "arg", False) if col.default is not None else False
        if callable(arg):
            arg = False
        v = 1 if arg else 0
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT {v}"

    if col.default is not None and hasattr(col.default, "arg"):
        arg = col.default.arg
        if callable(arg):
            if "DATETIME" in typ.upper() or "TIMESTAMP" in typ.upper():
                return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT (datetime('now'))"
            if "DATE" in typ.upper() and "TIME" not in typ.upper():
                return f"ALTER TABLE users ADD COLUMN {name} {typ} NULL"
            return f"ALTER TABLE users ADD COLUMN {name} {typ} NULL"
        if isinstance(arg, str):
            esc = arg.replace("'", "''")
            return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT '{esc}'"
        if isinstance(arg, bool):
            return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT {1 if arg else 0}"
        if isinstance(arg, (int, float)):
            return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT {arg}"

    if "INTEGER" in typ.upper():
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT 0"
    if "FLOAT" in typ.upper() or "REAL" in typ.upper():
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT 0.0"
    if "TEXT" in typ.upper() or "VARCHAR" in typ.upper() or "STRING" in typ.upper():
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NOT NULL DEFAULT ''"
    if "DATE" in typ.upper() and "TIME" not in typ.upper():
        return f"ALTER TABLE users ADD COLUMN {name} {typ} NULL"
    return f"ALTER TABLE users ADD COLUMN {name} {typ} NULL"


def _migrate_sqlite_users_columns() -> None:
    """
    create_all() does not add new columns to existing SQLite tables.
    Missing columns cause OperationalError on SELECT/INSERT (often surfacing as 500 via the dev proxy).
    """
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    existing = {c["name"] for c in insp.get_columns("users")}
    from api.models import User

    with engine.begin() as conn:
        for col in User.__table__.columns:
            if col.name in existing:
                continue
            ddl = _sqlite_users_add_column_ddl(col, engine.dialect)
            try:
                conn.execute(text(ddl))
                logger.info("SQLite migration applied", extra={"ddl": ddl})
            except Exception as e:
                err = str(e).lower()
                if "duplicate column" in err:
                    logger.debug("SQLite column already exists", extra={"column": col.name})
                else:
                    logger.warning("SQLite migration skipped for column", extra={"column": col.name, "error": str(e)})


def _migrate_sqlite_chat_session_id() -> None:
    """Add chat_session_id to chat_messages for existing SQLite DBs."""
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    insp = inspect(engine)
    if not insp.has_table("chat_messages"):
        return
    existing = {c["name"] for c in insp.get_columns("chat_messages")}
    if "chat_session_id" in existing:
        return
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN chat_session_id INTEGER NULL"))
            logger.info("SQLite migration applied: chat_messages.chat_session_id")
        except Exception as e:
            logger.warning("SQLite chat_session_id migration skipped", extra={"error": str(e)})


def init_db():
    """Create tables from models."""
    from api.models import User, FoodItem, GlucoseReading, ChatMessage, ChatSession  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_users_columns()
    _migrate_sqlite_chat_session_id()
    logger.info("Database initialized")
