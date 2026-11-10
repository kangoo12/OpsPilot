from uuid import UUID

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, select

from app.consistency import check_consistency
from app.models import Order, ReplyDraft, Ticket
from app.orders import seed_orders
from app.support_schemas import OrderRead
from test_support import add_ticket, mock_reply


def record(app, order_id):
    with Session(app.state.engine) as session:
        return OrderRead.model_validate(session.get(Order, order_id))


@pytest.mark.parametrize("message,order_id,codes", [
    ("My smartphone is defective.", "DEMO-LAMP-9001", {"product_mismatch"}),
    ("Το κινητό μου δεν ανοίγει.", "DEMO-LAMP-9001", {"product_mismatch"}),
    ("My lamp was delivered today.", "DEMO-LAMP-9001", {"delivery_status_mismatch"}),
    ("Παρέλαβα σήμερα την παραγγελία #DEMO-LAMP-9001.", "DEMO-LAMP-9001", {"delivery_status_mismatch"}),
    ("My smartphone hasn't arrived.", "7821", {"delivery_status_mismatch"}),
    ("Δεν έχω παραλάβει το κινητό μου.", "7821", {"delivery_status_mismatch"}),
    ("My lamp was delivered, but I have not received it.", "DEMO-LAMP-9001", {"conflicting_customer_statements", "delivery_status_mismatch"}),
    ("Παρέλαβα το κινητό, αλλά δεν το παρέλαβα.", "7821", {"conflicting_customer_statements", "delivery_status_mismatch"}),
    ("I ordered a smartphone but received a lamp.", "7821", {"product_mismatch", "conflicting_customer_statements"}),
    ("My lamp has not been shipped, but it is in transit.", "DEMO-LAMP-9001", {"conflicting_customer_statements", "delivery_status_mismatch"}),
])
def test_material_discrepancies(app, message, order_id, codes):
    with TestClient(app):
        result = check_consistency(message, record(app, order_id), order_id)
    assert result.status == "discrepancy"
    assert result.requires_human_review
    assert {issue.code for issue in result.issues} == codes


@pytest.mark.parametrize("message,order_id", [
    ("My smartphone was delivered today and is defective.", "7821"),
    ("Παρέλαβα σήμερα την παραγγελία #7821, αλλά το κινητό δεν ανοίγει.", "7821"),
    ("My LumaLite desk lamp has not arrived.", "DEMO-LAMP-9001"),
    ("Where is order #DEMO-LAMP-9001?", "DEMO-LAMP-9001"),
    ("When will my lamp be delivered?", "DEMO-LAMP-9001"),
    ("Has my order arrived?", "DEMO-LAMP-9001"),
    ("I received an email about my lamp.", "DEMO-LAMP-9001"),
    ("I'm using my phone to track my lamp.", "DEMO-LAMP-9001"),
    ("I ordered a lamp, not a smartphone.", "DEMO-LAMP-9001"),
    ("Τα ακουστικά μου δεν έχουν φτάσει.", "GR-1042"),
    ("Πότε θα παραδοθεί η παραγγελία;", "7821"),
    ("Πότε έφτασε η παραγγελία;", "7821"),
    ("Γράφω από το κινητό μου για το φωτιστικό.", "DEMO-LAMP-9001"),
])
def test_normal_matching_orders_and_non_assertions(app, message, order_id):
    with TestClient(app):
        result = check_consistency(message, record(app, order_id), order_id)
    assert result.status == "consistent", result.model_dump()
    assert not result.requires_human_review
    assert result.issues == []


def test_unknown_orders_and_conflicting_statements_without_a_record():
    result = check_consistency("My smartphone is defective.", None, "UNKNOWN-999")
    assert result.status == "unknown_order" and result.requires_human_review
    assert result.issues[0].code == "order_unknown"
    missing = check_consistency("Please help.", None, None)
    assert missing.status == "no_order_id"
    conflict = check_consistency("My item was delivered but I have not received it.", None, "UNKNOWN-999")
    assert conflict.status == "discrepancy"


def test_words_inside_order_ids_are_not_product_claims_after_manual_correction(app):
    with TestClient(app):
        result = check_consistency("Where is order #DEMO-LAMP-9001?", record(app, "GR-1042"), "GR-1042")
        assert result.status == "consistent"
        assert result.reported_products == []


def test_conflict_flags_ticket_list_details_and_neutral_draft(app):
    mock_reply(app)
    with TestClient(app) as client:
        ticket = add_ticket(app, message="My smartphone was delivered today, but it does not turn on.", order_id="DEMO-LAMP-9001", category="technical_support")
        original = None
        with Session(app.state.engine) as session:
            original = session.get(Ticket, UUID(ticket["id"])).model_dump(mode="json")
        detail = client.get(f"/api/tickets/{ticket['id']}").json()
        assert detail["requires_human_review"] is True
        assert detail["status"] == "new"
        assert detail["consistency"]["status"] == "discrepancy"
        assert client.get("/api/tickets").json()["items"][0]["requires_human_review"] is True
        lookup = client.get(f"/api/tickets/{ticket['id']}/order").json()
        assert lookup["consistency"]["requires_human_review"]
        response = client.post(f"/api/tickets/{ticket['id']}/drafts")
        assert response.status_code == 201, response.text
        draft = response.json()
        text = draft["reply_text"]
        assert "need clarification" in text and "Human review is needed" in text
        for unsupported in ("LumaLite", "in transit", "2026-11-14", "was delivered today", "refund", "carrier", "mistake"):
            assert unsupported not in text
        assert draft["order_context"]["consistency"]["status"] == "discrepancy"
        assert draft["status"] == "pending_review"
        with Session(app.state.engine) as session:
            assert session.get(Ticket, UUID(ticket["id"])).model_dump(mode="json") == original


def test_conflict_reply_cannot_be_overridden_with_order_facts(app):
    mock_reply(app, fact_keys=["warranty_eligibility"], next_step="fault_details")
    with TestClient(app) as client:
        ticket = add_ticket(app, message="My smartphone was delivered today.", order_id="DEMO-LAMP-9001")
        path = f"/api/tickets/{ticket['id']}/drafts"
        assert client.post(path).status_code == 502
        assert client.get(path).json()["total"] == 0


def test_new_fixtures_are_unique_and_old_seed_and_history_never_overwritten(app):
    mock_reply(app)
    with TestClient(app) as client:
        orders = client.get("/api/orders").json()
        assert len(orders) == len({order["id"] for order in orders}) == 19
        assert client.get("/api/orders/7821").json()["order"]["product"] == "Aster Nova smartphone"
        with Session(app.state.engine) as session:
            old = session.get(Order, "7821")
            old.product = "LumaLite desk lamp"
            old.delivery_status = "in_transit"
            session.add(old); session.commit()
        ticket = add_ticket(app, message="Where is my order #7821?", order_id="7821")
        draft = client.post(f"/api/tickets/{ticket['id']}/drafts").json()
        with Session(app.state.engine) as session:
            before_ticket = session.get(Ticket, UUID(ticket["id"])).model_dump(mode="json")
            before_draft = session.get(ReplyDraft, UUID(draft["id"])).model_dump(mode="json")
        seed_orders(app.state.engine)
        with Session(app.state.engine) as session:
            assert session.get(Order, "7821").product == "LumaLite desk lamp"
            assert session.get(Ticket, UUID(ticket["id"])).model_dump(mode="json") == before_ticket
            assert session.get(ReplyDraft, UUID(draft["id"])).model_dump(mode="json") == before_draft
            assert len(session.exec(select(Order)).all()) == 19


def test_historical_draft_snapshot_is_checked_without_rewriting_history(app):
    with TestClient(app) as client:
        ticket = add_ticket(app, message="My smartphone was delivered today but is defective.", order_id="7821", category="technical_support")
        with Session(app.state.engine) as session:
            legacy = ReplyDraft(ticket_id=UUID(ticket["id"]), reply_text="Your LumaLite desk lamp is in transit.", language="en",
                                policy_version="aster-demo-2026-11-v1", order_context={
                                    "reference_order_id": "7821", "extracted_order_id": "7821", "source": "extracted", "lookup_status": "found",
                                    "order": {**record(app, "DEMO-LAMP-9001").model_dump(mode="json"), "id": "7821"},
                                })
            session.add(legacy); session.commit(); session.refresh(legacy)
            before = legacy.model_dump(mode="json")
        assert client.get(f"/api/tickets/{ticket['id']}").json()["requires_human_review"] is False
        old = client.get(f"/api/tickets/{ticket['id']}/drafts").json()["items"][0]
        assert old["snapshot_consistency"]["status"] == "discrepancy"
        assert old["reply_text"] == "Your LumaLite desk lamp is in transit."
        with Session(app.state.engine) as session:
            assert session.get(ReplyDraft, legacy.id).model_dump(mode="json") == before


def test_audit_tool_is_read_only_and_reports_conflicts(app):
    from scripts.audit_order_references import audit
    with TestClient(app):
        add_ticket(app, message="My smartphone was delivered today.", order_id="DEMO-LAMP-9001")
        path = app.state.settings.database_path
        before = audit(path, "DEMO-LAMP-9001")
        after = audit(path, "DEMO-LAMP-9001")
        assert before["fingerprints"] == after["fingerprints"]
        assert after["consistency_checks"][0]["consistency"]["status"] == "discrepancy"
