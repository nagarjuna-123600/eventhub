"""SQLite connection handling.

A connection is opened per request. Registration writes use BEGIN IMMEDIATE
transactions (see `transaction`), which take SQLite's write lock up front so
concurrent registrations are serialized and capacity can never be exceeded.
"""
import sqlite3
from contextlib import contextmanager

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT,
    date        TEXT    NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity > 0),
    location    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS registrations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    email      TEXT    NOT NULL,
    name       TEXT    NOT NULL,
    status     TEXT    NOT NULL CHECK (status IN ('CONFIRMED', 'CANCELLED')),
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    UNIQUE (event_id, email)
);

CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
CREATE INDEX IF NOT EXISTS idx_registrations_event_status
    ON registrations(event_id, status);
"""


def _connect(path):
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app):
    conn = _connect(app.config["DATABASE"])
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
    finally:
        conn.close()
    app.teardown_appcontext(close_db)


@contextmanager
def transaction(db):
    """Atomic write transaction that holds the write lock from the start."""
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")
