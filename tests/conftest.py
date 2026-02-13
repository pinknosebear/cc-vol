import pytest
import sqlite3

from app.db import get_db_connection, create_tables


@pytest.fixture
def db():
    """Yield an in-memory SQLite connection with all tables created."""
    conn = get_db_connection(":memory:")
    create_tables(conn)
    yield conn
    conn.close()
