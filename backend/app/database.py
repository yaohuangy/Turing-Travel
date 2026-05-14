import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base

from app.config import settings

db_url = settings.DATABASE_URL

# Ensure the database directory exists for SQLite
if db_url.startswith("sqlite:///"):
    db_path = db_url[len("sqlite:///"):]
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

connect_args = {}
if "sqlite" in db_url:
    connect_args["check_same_thread"] = False

engine = create_engine(db_url, connect_args=connect_args, echo=False)

Base = declarative_base()


def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)
