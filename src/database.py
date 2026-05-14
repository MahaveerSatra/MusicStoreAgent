import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text

load_dotenv()

_DB_PATH = os.environ.get("CHINOOK_DB_PATH", "chinook.db")

# Resolve path relative to project root (parent of src/)
_PROJECT_ROOT = Path(__file__).parent.parent
_ABSOLUTE_DB_PATH = _PROJECT_ROOT / _DB_PATH

_engine = None
_db = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = f"sqlite:///{_ABSOLUTE_DB_PATH}"
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return _engine


def get_db() -> SQLDatabase:
    global _db
    if _db is None:
        _db = SQLDatabase(get_engine())
    return _db


def run_query(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SQL query and return results as a list of dicts."""
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]
