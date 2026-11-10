from pathlib import Path

from sqlalchemy import URL, event
from sqlmodel import Session, create_engine, select


def create_database_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"check_same_thread": False, "timeout": 5},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    return engine


def check_database(engine) -> None:
    with Session(engine) as session:
        session.exec(select(1)).one()
