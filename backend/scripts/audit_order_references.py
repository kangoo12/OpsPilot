"""Read-only audit of ticket/order/draft provenance. Run from any working directory.

Example: backend/.venv/Scripts/python.exe backend/scripts/audit_order_references.py
         --database data/opspilot.db --order-id 7821
Only databases inside OpsPilot may be inspected. No rows are written or removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.consistency import check_consistency


def audit(database: Path, order_id: str) -> dict:
    path = (ROOT / database).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("The database must be inside OpsPilot")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        fingerprints = {}
        for table in ("ticket", "order", "replydraft", "ticketorderreference"):
            if table in tables:
                rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY 1')]
                fingerprints[table] = {"rows": len(rows), "sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}
        tickets = [dict(row) for row in connection.execute(
            "SELECT * FROM ticket WHERE upper(order_id)=upper(?) OR message LIKE ? ORDER BY created_at", (order_id, f"%{order_id}%")
        )] if "ticket" in tables else []
        ticket_ids = {ticket["id"] for ticket in tickets}
        drafts = [dict(row) for row in connection.execute("SELECT * FROM replydraft ORDER BY created_at") if row["ticket_id"] in ticket_ids] if "replydraft" in tables else []
        orders = [dict(row) for row in connection.execute('SELECT * FROM "order" WHERE upper(id)=upper(?)', (order_id,))] if "order" in tables else []
        checks = []
        for ticket in tickets:
            manual = connection.execute("SELECT order_id FROM ticketorderreference WHERE ticket_id=?", (ticket["id"],)).fetchone() if "ticketorderreference" in tables else None
            reference = manual["order_id"] if manual else ticket["order_id"]
            matched = connection.execute('SELECT * FROM "order" WHERE upper(id)=upper(?)', (reference,)).fetchone() if reference and "order" in tables else None
            checks.append({"ticket_id": ticket["id"], "reference_order_id": reference,
                           "consistency": check_consistency(ticket["message"], SimpleNamespace(**dict(matched)) if matched else None, reference).model_dump()})
        return {"database": str(path.relative_to(ROOT)), "fingerprints": fingerprints, "tickets": tickets, "orders": orders, "drafts": drafts, "consistency_checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/opspilot.db"))
    parser.add_argument("--order-id", default="7821")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(audit(args.database, args.order_id), ensure_ascii=False, indent=2))
