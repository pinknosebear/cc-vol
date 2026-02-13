import sqlite3


def get_db_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    """Return a sqlite3 connection with Row factory for dict-like access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables (volunteers, shifts, signups).

    This is called by the shared test fixture so every model's tests
    start with a fully-initialised schema.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            is_coordinator BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            shift_type TEXT NOT NULL CHECK(shift_type IN ('kakad', 'robe')),
            capacity INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, shift_type)
        );

        CREATE TABLE IF NOT EXISTS signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volunteer_id INTEGER NOT NULL,
            shift_id INTEGER NOT NULL,
            signed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dropped_at TIMESTAMP,
            FOREIGN KEY (volunteer_id) REFERENCES volunteers(id),
            FOREIGN KEY (shift_id) REFERENCES shifts(id),
            UNIQUE(volunteer_id, shift_id)
        );
        """
    )
