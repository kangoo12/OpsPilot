"""Create a fresh repository-local QA database; never touches the demo database."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.config import PROJECT_ROOT, Settings
from app.main import create_app
from app.models import Ticket
from app.orders import ticket_order_context
from app.drafts import save_draft
from app.workflow_common import audit
from app.workflow_models import TicketWorkflow


def fingerprints(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
        result = {}
        for (table,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + table.replace('"', '""') + '"'
            rows = sorted(json.dumps(row, ensure_ascii=False, default=str) for row in connection.execute('SELECT * FROM ' + quoted))
            result[table] = {'rows': len(rows), 'sha256': hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()}
        return result


def main():
    folder = PROJECT_ROOT / '.cache/milestone45'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'qa.db'
    if path.exists():
        raise SystemExit('QA database already exists. Preserve it; use a separate fresh checkout for a new run.')
    original = Settings().database_path
    before = fingerprints(original)
    run_id = str(uuid4())
    app = create_app(Settings(_env_file=None, database_path=path))
    with TestClient(app) as client:
        ids = []
        with Session(app.state.engine) as session:
            for index in range(27):
                message = f'QA45 {run_id}: support request {index}.'
                order_id = None
                if index in (0, 1, 2):
                    message = f'QA45 {run_id}: Where is my order #DEMO-LAMP-9001?'
                    order_id = 'DEMO-LAMP-9001'
                if index == 3:
                    message = f'QA45 conflict {run_id}: My smartphone from order #DEMO-LAMP-9001 was delivered today.'
                    order_id = 'DEMO-LAMP-9001'
                ticket = Ticket(message=message, order_id=order_id, category='delivery' if index % 2 == 0 else 'returns',
                                priority=['low', 'medium', 'high', 'urgent'][index % 4], customer_intent=f'QA45 support request {index}', reason='Synthetic QA fixture',
                                created_at=datetime.now(timezone.utc) - timedelta(hours=index + 1))
                session.add(ticket); session.flush()
                session.add(TicketWorkflow(ticket_id=ticket.id, updated_at=ticket.created_at))
                audit(session, ticket.id, 'ticket_created', data={'synthetic_qa': True}, timestamp=ticket.created_at)
                ids.append(str(ticket.id))
            session.commit()
        # Historical decision fixtures, created via the normal safety APIs.
        for index, action in [(1, 'approve'), (2, 'reject')]:
            from uuid import UUID
            with Session(app.state.engine) as session:
                ticket = session.get(Ticket, UUID(ids[index]))
                context = ticket_order_context(session, ticket)
            draft = save_draft(app.state.engine, ticket.id, context, 'Thank you for your message. Please let us know what help you need.', 'en')
            workflow = client.get(f'/api/tickets/{ticket.id}/workflow').json()
            body = {'expected_version': draft.version, 'context_fingerprint': workflow['context_fingerprint'], 'confirmed': True}
            if action == 'reject':
                body['reason'] = 'Synthetic rejection fixture for analytics'
            response = client.post(f'/api/tickets/{ticket.id}/drafts/{draft.id}/{action}', json=body)
            assert response.status_code == 200, response.text
        for status in ('in_progress', 'resolved'):
            workflow = client.get(f'/api/tickets/{ids[2]}/workflow').json()
            assert client.patch(f'/api/tickets/{ids[2]}/status', json={'status': status, 'expected_version': workflow['version'], 'confirmed': True}).status_code == 200
    assert fingerprints(original) == before
    evidence = {'run_id': run_id, 'database': str(path), 'target_id': ids[0], 'approved_id': ids[1], 'conflict_id': ids[3], 'total': 27,
                'original_database': str(original), 'original_fingerprints': before}
    (folder / 'seed.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f'Created isolated QA database with {len(ids)} fictional tickets. Original database unchanged.')


if __name__ == '__main__':
    main()
