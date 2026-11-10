from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Ticket, TicketOrderReference
from app.workflow_models import TicketWorkflow


@pytest.fixture
def searchable_tickets(app):
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            tickets = [
                Ticket(message="Damaged PHONE screen", order_id="GR-1042", category="returns",
                       priority="high", customer_intent="Request replacement", reason="Damage"),
                Ticket(message="Where is my parcel?", category="delivery", priority="urgent",
                       customer_intent="Track shipment", reason="Delay"),
                Ticket(message="Έκπτωση 50% on model_a / accessories", category="payments",
                       priority="low", customer_intent="Explain discount", reason="Question"),
            ]
            session.add_all(tickets)
            session.flush()
            ids = [str(ticket.id) for ticket in tickets]
            session.add(TicketOrderReference(ticket_id=tickets[1].id, order_id="MANUAL-9001"))
            session.add(TicketWorkflow(ticket_id=tickets[0].id, status="in_progress"))
            session.commit()
        yield client, ids


@pytest.mark.parametrize("query,index", [
    ("phone", 0), ("PHONE", 0), ("gr-1042", 0), ("REPLACEMENT", 0),
    ("shipment", 1), ("manual-9001", 1), ("Έκπτωση", 2),
    ("%", 2), ("_", 2), ("/", 2), ("  phone  ", 0),
])
def test_search_fields_case_and_literal_characters(searchable_tickets, query, index):
    client, ids = searchable_tickets
    response = client.get("/api/tickets", params={"search": query})
    assert response.status_code == 200
    page = response.json()
    assert [ticket["id"] for ticket in page["items"]] == [ids[index]]
    assert page["counts"]["total"] == 1


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_search_preserves_normal_results(searchable_tickets, query):
    client, _ = searchable_tickets
    assert client.get("/api/tickets", params={"search": query}).json() == client.get("/api/tickets").json()


@pytest.mark.parametrize("query", ["not-present", "' OR 1=1 --"])
def test_no_match_and_sql_injection_are_literal(searchable_tickets, query):
    client, _ = searchable_tickets
    page = client.get("/api/tickets", params={"search": query}).json()
    assert page["items"] == []
    assert page["counts"] == {"total": 0, "new": 0, "high": 0, "urgent": 0}
    assert client.get("/api/tickets").json()["counts"]["total"] == 3


def test_search_counts_use_current_workflow_status(searchable_tickets):
    client, _ = searchable_tickets
    page = client.get("/api/tickets", params={"search": "phone"}).json()
    assert page["counts"] == {"total": 1, "new": 0, "high": 1, "urgent": 0}


def test_search_filters_all_stored_tickets_before_pagination(app):
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            tickets = [Ticket(message="Needle issue" if i < 5 else "Unrelated issue",
                              category="other", priority="medium", customer_intent="Get help",
                              reason="Question", created_at=start + timedelta(minutes=i))
                       for i in range(30)]
            session.add_all(tickets)
            session.flush()
            expected = [str(ticket.id) for ticket in tickets[:5]][::-1]
            session.commit()
        assert not any(ticket["id"] in expected for ticket in client.get("/api/tickets").json()["items"])
        page = client.get("/api/tickets", params={"search": "needle", "limit": 2, "offset": 1}).json()
        assert [ticket["id"] for ticket in page["items"]] == expected[1:3]
        assert page["counts"] == {"total": 5, "new": 5, "high": 0, "urgent": 0}
        assert page["limit"] == 2 and page["offset"] == 1
        assert client.get("/api/tickets", params={"search": "needle", "offset": 5}).json()["items"] == []
