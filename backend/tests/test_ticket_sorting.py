from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Ticket
from app.workflow_models import AuditEvent


@pytest.fixture
def sorted_tickets(app):
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            for index, priority in enumerate(['high', 'urgent', 'low', 'medium', 'high'], 1):
                ticket = Ticket(id=UUID(int=index), message='Parcel help', category='delivery', priority=priority,
                                customer_intent='Track parcel', reason='Delay', created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index // 2))
                session.add(ticket)
                session.flush()
            session.add(AuditEvent(ticket_id=UUID(int=1), event_type='draft_edited', actor='Local Operator', created_at=datetime(2026, 2, 1, tzinfo=timezone.utc), data={}))
            session.add(AuditEvent(ticket_id=UUID(int=2), event_type='order_reference_imported', actor='Historical import', created_at=datetime(2026, 3, 1, tzinfo=timezone.utc), data={}))
            session.commit()
        yield client


@pytest.mark.parametrize('sort,expected', [
    ('newest', [5, 4, 3, 2, 1]), ('oldest', [1, 2, 3, 4, 5]),
    ('priority_high', [2, 5, 1, 4, 3]), ('priority_low', [3, 4, 5, 1, 2]),
    ('updated', [1, 5, 4, 3, 2]),
])
def test_sorting_and_stable_pagination(sorted_tickets, sort, expected):
    def ids(page):
        return [UUID(item['id']).int for item in page['items']]
    whole = sorted_tickets.get('/api/tickets', params={'sort': sort}).json()
    assert ids(whole) == expected
    pages = [sorted_tickets.get('/api/tickets', params={'sort': sort, 'limit': 2, 'offset': offset}).json() for offset in (0, 2, 4)]
    assert [item for page in pages for item in ids(page)] == expected
    assert all(page['counts'] == whole['counts'] for page in pages)


def test_sort_with_search_and_filters(sorted_tickets):
    page = sorted_tickets.get('/api/tickets', params={'search': 'PARCEL', 'category': 'delivery', 'priority': 'high', 'status': 'new', 'sort': 'oldest', 'limit': 1, 'offset': 1}).json()
    assert UUID(page['items'][0]['id']).int == 5
    assert page['counts'] == {'total': 2, 'new': 2, 'high': 2, 'urgent': 0}


def test_default_and_invalid_sort(sorted_tickets):
    assert sorted_tickets.get('/api/tickets').json() == sorted_tickets.get('/api/tickets?sort=newest').json()
    response = sorted_tickets.get('/api/tickets', params={'sort': 'created_at; DROP TABLE ticket'})
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'] == ['query', 'sort']
