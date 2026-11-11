from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Ticket
from app.workflow_models import AuditEvent, TicketWorkflow, DraftRevision
from test_workflow import setup, decision, edit


def test_empty_analytics_and_parameter_validation(app):
    with TestClient(app) as client:
        data = client.get('/api/analytics?days=7').json()
        assert data['total_tickets'] == data['human_review_tickets'] == 0
        assert all(count == 0 for count in data['by_category'].values())
        assert data['draft_decisions'] == {'approved': 0, 'rejected': 0}
        assert data['resolution_time'] == {'average_seconds': None, 'measured_tickets': 0, 'unavailable_tickets': 0}
        assert len(data['volume']) == 7 and all(day['count'] == 0 for day in data['volume'])
        for days in ('0', '367', 'abc'):
            assert client.get('/api/analytics', params={'days': days}).status_code == 422


def test_real_aggregates_current_status_human_review_and_daily_volume(app):
    now = datetime.now(timezone.utc)
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            tickets = [
                Ticket(message='Where is order #DEMO-LAMP-9001?', order_id='DEMO-LAMP-9001', category='delivery', priority='high', customer_intent='Track parcel', reason='Question', created_at=now),
                Ticket(message='My smartphone from order #DEMO-LAMP-9001 was delivered today.', order_id='DEMO-LAMP-9001', category='returns', priority='urgent', customer_intent='Return item', reason='Fault', created_at=now - timedelta(days=1)),
                Ticket(message='Need help', category='other', priority='low', customer_intent='Ask support', reason='Question', created_at=now - timedelta(days=60)),
            ]
            session.add_all(tickets); session.flush()
            session.add(TicketWorkflow(ticket_id=tickets[0].id, status='in_progress'))
            session.commit()
        data = client.get('/api/analytics?days=7').json()
        assert data['total_tickets'] == 3
        assert data['by_category'] == {'delivery': 1, 'returns': 1, 'payments': 0, 'technical_support': 0, 'other': 1}
        assert data['by_priority'] == {'low': 1, 'medium': 0, 'high': 1, 'urgent': 1}
        assert data['by_status'] == {'new': 2, 'in_progress': 1, 'waiting_for_customer': 0, 'resolved': 0}
        assert data['human_review_tickets'] == 2
        assert [day['count'] for day in data['volume']] == [0, 0, 0, 0, 0, 1, 1]
        # GETs do not create audit entries or resolve discrepancies.
        assert client.get('/api/analytics?days=7').json()['human_review_tickets'] == 2


def test_draft_decisions_count_draft_ids_not_revision_rows(app):
    with TestClient(app) as client:
        ticket, draft, path = setup(client, app)
        edited = edit(client, path, draft, 'Thank you for your message. How can we help further?').json()
        approved = client.post(f"{path}/drafts/{draft['id']}/approve", json=decision(client, path, edited)).json()
        assert approved['status'] == 'approved'
        child = edit(client, path, approved, 'Please provide any additional details.').json()
        rejected = client.post(f"{path}/drafts/{child['id']}/reject", json=decision(client, path, child, reason='Needs clearer wording')).json()
        assert rejected['status'] == 'rejected'
        with Session(app.state.engine) as session:
            from sqlmodel import select
            assert len(session.exec(select(DraftRevision)).all()) == 5
        assert client.get('/api/analytics').json()['draft_decisions'] == {'approved': 1, 'rejected': 1}


def test_resolution_time_latest_resolution_excludes_reopened_and_unreliable(app):
    start = datetime.now(timezone.utc) - timedelta(days=2)
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            for index, status in enumerate(['resolved', 'resolved', 'in_progress', 'resolved'], 1):
                ticket = Ticket(id=UUID(int=index), message='Help', category='other', priority='low', customer_intent='Get help', reason='Question', created_at=start)
                session.add(ticket); session.flush()
                session.add(TicketWorkflow(ticket_id=ticket.id, status=status))
            for index, hours in [(1, 1), (1, 4), (3, 8), (4, -1)]:
                session.add(AuditEvent(ticket_id=UUID(int=index), event_type='ticket_status_changed', actor='Local Operator', created_at=start + timedelta(hours=hours), data={'previous': 'in_progress', 'new': 'resolved'}))
            session.commit()
        duration = client.get('/api/analytics').json()['resolution_time']
        assert duration['measured_tickets'] == 1 and duration['unavailable_tickets'] == 2
        assert duration['average_seconds'] == pytest.approx(14400, abs=0.1)
