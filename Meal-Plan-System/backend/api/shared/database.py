"""Database - SQLAlchemy engine and session."""
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from api.core.config import DATABASE_URL
from api.core.logging_config import get_logger

logger = get_logger("api.database")

_connect_args = {"check_same_thread": False}
if str(DATABASE_URL).startswith("sqlite"):
    # Reduce "database is locked" during concurrent seed + auth (Windows / dev).
    _connect_args["timeout"] = 30.0

# SQLite: avoid QueuePool exhaustion under TestClient / threaded workers — each checkout is a fresh connection.
_engine_kwargs = {"connect_args": _connect_args}
if str(DATABASE_URL).startswith("sqlite"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


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
            col_sql = col.type.compile(dialect=engine.dialect)
            parts = [col.name, str(col_sql)]
            if col.nullable:
                parts.append("NULL")
            else:
                if col.default is not None:
                    parts.append("NOT NULL")
                elif "BOOLEAN" in str(col_sql).upper() or str(col.type).upper().startswith("BOOL"):
                    parts.append("NOT NULL DEFAULT 0")
                elif "INTEGER" in str(col_sql).upper():
                    parts.append("NOT NULL DEFAULT 0")
                elif "FLOAT" in str(col_sql).upper() or "REAL" in str(col_sql).upper():
                    parts.append("NOT NULL DEFAULT 0")
                elif "TEXT" in str(col_sql).upper() or "VARCHAR" in str(col_sql).upper() or "STRING" in str(
                    col_sql
                ).upper():
                    parts.append("NOT NULL DEFAULT ''")
                elif "DATE" in str(col_sql).upper():
                    parts.append("NULL")
                else:
                    parts.append("NULL")
            ddl = f"ALTER TABLE users ADD COLUMN {' '.join(parts)}"
            try:
                conn.execute(text(ddl))
                logger.info("SQLite migration applied", extra={"ddl": ddl})
            except Exception as e:
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
    from api.models import User, FoodItem, GlucoseReading, UserFoodFeedback, ChatMessage, ChatSession  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_users_columns()
    _migrate_sqlite_chat_session_id()
    logger.info("Database initialized")
