from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Ticket
from app.workflow_models import TicketWorkflow


@pytest.fixture
def filter_tickets(app):
    with TestClient(app) as client:
        with Session(app.state.engine) as session:
            ids = []
            for index, (category, priority, status) in enumerate([
                ("delivery", "high", "in_progress"),
                ("delivery", "high", "waiting_for_customer"),
                ("returns", "urgent", "resolved"),
                ("payments", "low", None),
                ("delivery", "high", "in_progress"),
                ("technical_support", "medium", None),
            ]):
                ticket = Ticket(message="Needle parcel" if index == 4 else "Support request",
                                category=category, priority=priority, customer_intent="Get help",
                                reason="Question", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index))
                session.add(ticket)
                session.flush()
                ids.append(str(ticket.id))
                if status:
                    session.add(TicketWorkflow(ticket_id=ticket.id, status=status))
            session.commit()
        yield client, ids


@pytest.mark.parametrize("params,indices", [
    ({"category": "delivery"}, [4, 1, 0]),
    ({"category": "returns"}, [2]),
    ({"category": "payments"}, [3]),
    ({"category": "technical_support"}, [5]),
    ({"category": "other"}, []),
    ({"priority": "high"}, [4, 1, 0]),
    ({"priority": "urgent"}, [2]),
    ({"priority": "low"}, [3]),
    ({"priority": "medium"}, [5]),
    ({"status": "new"}, [5, 3]),
    ({"status": "in_progress"}, [4, 0]),
    ({"status": "waiting_for_customer"}, [1]),
    ({"status": "resolved"}, [2]),
    ({"category": "delivery", "priority": "high", "status": "in_progress"}, [4, 0]),
    ({"category": "delivery", "priority": "urgent"}, []),
    ({"search": "NEEDLE", "category": "delivery", "priority": "high", "status": "in_progress"}, [4]),
])
def test_individual_combined_and_search_filters(filter_tickets, params, indices):
    client, ids = filter_tickets
    response = client.get("/api/tickets", params=params)
    assert response.status_code == 200, response.text
    page = response.json()
    assert [ticket["id"] for ticket in page["items"]] == [ids[index] for index in indices]
    assert page["counts"]["total"] == len(indices)


def test_filters_apply_before_pagination_and_counts(filter_tickets):
    client, ids = filter_tickets
    params = {"category": "delivery", "priority": "high", "limit": 1, "offset": 1}
    page = client.get("/api/tickets", params=params).json()
    assert [ticket["id"] for ticket in page["items"]] == [ids[1]]
    assert page["items"][0]["status"] == "waiting_for_customer"
    assert page["counts"] == {"total": 3, "new": 0, "high": 3, "urgent": 0}
    assert page["limit"] == 1 and page["offset"] == 1
    beyond = client.get("/api/tickets", params={**params, "offset": 3}).json()
    assert beyond["items"] == []
    assert beyond["counts"] == page["counts"]
    new_page = client.get("/api/tickets", params={"status": "new", "limit": 1}).json()
    assert new_page["counts"] == {"total": 2, "new": 2, "high": 0, "urgent": 0}


@pytest.mark.parametrize("params", [
    {"category": ""}, {"priority": ""}, {"status": ""},
    {"category": "", "priority": "", "status": ""},
])
def test_empty_filters_preserve_results(filter_tickets, params):
    client, _ = filter_tickets
    assert client.get("/api/tickets", params=params).json() == client.get("/api/tickets").json()


@pytest.mark.parametrize("field,value", [
    ("category", "invalid"), ("priority", "critical"), ("status", "closed"),
    ("category", "' OR 1=1 --"),
])
def test_invalid_filters_return_validation_errors(filter_tickets, field, value):
    client, _ = filter_tickets
    response = client.get("/api/tickets", params={field: value})
    assert response.status_code == 422
    assert any(error["loc"][:2] == ["query", field] and error["type"] == "enum"
               for error in response.json()["detail"])
    assert client.get("/api/tickets").json()["counts"]["total"] == 6
