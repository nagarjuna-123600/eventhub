import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eventhub.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False, "timeout": 30} if IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

if IS_SQLITE:
    # SQLite has no row locks (SELECT ... FOR UPDATE is a no-op), so we take
    # the write lock up-front with BEGIN IMMEDIATE. This serializes writers
    # and makes the capacity check + insert atomic.
    @event.listens_for(engine, "connect")
    def _disable_pysqlite_autobegin(dbapi_conn, _):
        dbapi_conn.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin_immediate(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
