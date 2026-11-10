"""Versioned, additive SQLite migrations. No legacy tables are rebuilt or reset."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, select

from app.models import ReplyDraft, Ticket, TicketOrderReference
from app.workflow_common import audit, ensure_review
from app.workflow_models import SchemaMigration, TicketWorkflow

VERSION = 1


def migrate_database(engine, path: Path):
    with engine.connect() as connection:
        existing = inspect(connection).get_table_names()
        if "schemamigration" in existing and connection.execute(text("SELECT 1 FROM schemamigration WHERE version=:v"), {"v": VERSION}).first():
            return
    if "ticket" in existing:
        # sqlite.backup includes committed WAL data and creates a consistent copy.
        folder = path.parent / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = folder / f"{path.stem}-pre-3b-{stamp}-{uuid4().hex[:8]}.sqlite3"
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(destination) as backup:
                source.backup(backup)
    with engine.begin() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        SQLModel.metadata.create_all(connection)
        with Session(bind=connection) as session:
            if session.get(SchemaMigration, VERSION):
                return
            for ticket in session.exec(select(Ticket)).all():
                if not session.get(TicketWorkflow, ticket.id):
                    session.add(TicketWorkflow(ticket_id=ticket.id, status=ticket.status, updated_at=ticket.created_at))
                    audit(session, ticket.id, "ticket_created", "Historical import",
                          {"historical_import": True, "status": ticket.status}, ticket.created_at, f"ticket_created:{ticket.id}")
            session.flush()
            for draft in session.exec(select(ReplyDraft)).all():
                ensure_review(session, draft, session.get(Ticket, draft.ticket_id))
            for reference in session.exec(select(TicketOrderReference)).all():
                audit(session, reference.ticket_id, "order_reference_imported", "Historical import",
                      {"order_id": reference.order_id, "original_change_time_unknown": True},
                      dedupe_key=f"reference_imported:{reference.ticket_id}")
            session.add(SchemaMigration(version=VERSION, name="additive_human_workflow"))
            session.flush()
        # Defense in depth: history and approved review rows cannot be mutated.
        for table in ("auditevent", "draftrevision", "discrepancyresolution", "replydraft"):
            for action in ("UPDATE", "DELETE"):
                connection.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable history'); END")
        for action in ("UPDATE", "DELETE"):
            connection.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS immutable_approved_{action.lower()} BEFORE {action} ON draftreview WHEN OLD.status = 'approved' BEGIN SELECT RAISE(ABORT, 'Approved content is immutable'); END")
