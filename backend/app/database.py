from pathlib import Path

from sqlalchemy import URL
from sqlmodel import Session, create_engine, select


def create_database_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"check_same_thread": False, "timeout": 5},
    )


def check_database(engine) -> None:
    with Session(engine) as session:
        session.exec(select(1)).one()
