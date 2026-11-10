from concurrent.futures import ThreadPoolExecutor
import sqlite3
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import Settings
from app.main import create_app
from app.migrations import migrate_database
from app.models import ReplyDraft, Ticket
from app.workflow_models import AuditEvent, DraftReview, SchemaMigration
from scripts.audit_order_references import audit
from test_support import add_ticket, mock_reply
from test_tickets import classification, mock_chat


def setup(client, app, *, conflict=False, unknown=False):
    mock_reply(app)
    ticket = add_ticket(app, message="My smartphone was delivered today but does not turn on." if conflict else "Where is my order #DEMO-LAMP-9001?",
                        order_id="UNKNOWN-777" if unknown else "DEMO-LAMP-9001")
    path = f"/api/tickets/{ticket['id']}"
    draft = client.post(path + "/drafts").json()
    assert "id" in draft, draft
    return ticket, draft, path


def decision(client, path, draft, **extra):
    state = client.get(path + "/workflow").json()
    return {"expected_version": draft["version"], "context_fingerprint": state["context_fingerprint"], "confirmed": True, **extra}


def edit(client, path, draft, text):
    body = decision(client, path, draft)
    body.pop("confirmed")
    return client.patch(f"{path}/drafts/{draft['id']}", json={**body, "reply_text": text})


def events(client, path):
    return client.get(path + "/activity?limit=100").json()["items"]


def test_pending_edit_save_revision_history_and_original_content(app):
    with TestClient(app) as client:
        ticket, original, path = setup(client, app)
        response = edit(client, path, original, "Thank you. Please let us know what additional help you need.")
        assert response.status_code == 200, response.text
        saved = response.json()
        assert saved["id"] == original["id"] and saved["version"] == 2
        assert saved["status"] == "pending_review"
        assert saved["reply_text"] != saved["original_content"] == original["reply_text"]
        assert saved["updated_at"] and saved["reviewer"] == "Local Operator"
        history = client.get(f"{path}/drafts/{saved['id']}/revisions").json()
        assert [item["version"] for item in history] == [1, 2]
        assert history[0]["content"] == original["reply_text"]
        assert history[1]["content"] == saved["reply_text"]
        assert any(item["event_type"] == "draft_edited" for item in events(client, path))
        with Session(app.state.engine) as session:
            assert session.get(ReplyDraft, UUID(original["id"])).reply_text == original["reply_text"]


def test_approval_does_not_send_or_resolve_and_cannot_be_duplicated(app):
    with TestClient(app) as client:
        ticket, draft, path = setup(client, app)
        payload = decision(client, path, draft)
        url = f"{path}/drafts/{draft['id']}/approve"
        approved = client.post(url, json=payload)
        assert approved.status_code == 200, approved.text
        data = approved.json()
        assert data["status"] == "approved" and data["approved_at"].endswith("Z")
        assert data["reviewer"] == "Local Operator" and data["version"] == 2
        assert client.get(path).json()["status"] == "new"
        assert client.post(url, json=payload).status_code == 409
        assert client.post(url, json=decision(client, path, data)).status_code == 409
        approvals = [item for item in events(client, path) if item["event_type"] == "draft_approved"]
        assert len(approvals) == 1 and approvals[0]["data"]["message_sent"] is False


def test_simultaneous_approval_has_one_winner(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        payload = decision(client, path, draft)
        def approve(_):
            return client.post(f"{path}/drafts/{draft['id']}/approve", json=payload).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(approve, range(2))) == [200, 409]
        assert sum(item["event_type"] == "draft_approved" for item in events(client, path)) == 1


def test_editing_approved_creates_new_pending_child_and_preserves_approved(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        approved = client.post(f"{path}/drafts/{draft['id']}/approve", json=decision(client, path, draft)).json()
        child_response = edit(client, path, approved, "Thank you for your message. Please confirm the information you need.")
        assert child_response.status_code == 200, child_response.text
        child = child_response.json()
        assert child["id"] != approved["id"] and child["parent_draft_id"] == approved["id"]
        assert child["status"] == "pending_review" and child["origin"] == "human_revision"
        stored = client.get(path + "/drafts").json()["items"]
        assert next(item for item in stored if item["id"] == approved["id"])["reply_text"] == approved["reply_text"]
        assert next(item for item in stored if item["id"] == approved["id"])["status"] == "approved"
        with Session(app.state.engine) as session:
            row = session.get(DraftReview, UUID(approved["id"]))
            row.content = "Trying to mutate an approved row directly"
            with pytest.raises(IntegrityError):
                session.commit()


@pytest.mark.parametrize("reason", [None, "", "   ", "bad"])
def test_rejection_requires_reason(app, reason):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        payload = decision(client, path, draft)
        if reason is not None:
            payload["reason"] = reason
        assert client.post(f"{path}/drafts/{draft['id']}/reject", json=payload).status_code == 422
        assert client.get(path + "/drafts").json()["items"][0]["status"] == "pending_review"


def test_rejection_records_reason_and_editing_rejected_forks(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        rejected = client.post(f"{path}/drafts/{draft['id']}/reject", json=decision(client, path, draft, reason="Needs a clearer explanation.")).json()
        assert rejected["status"] == "rejected" and rejected["rejected_at"].endswith("Z")
        assert rejected["rejection_reason"] == "Needs a clearer explanation."
        child = edit(client, path, rejected, "Thank you for explaining the issue. Please clarify your request.").json()
        assert child["id"] != draft["id"] and child["status"] == "pending_review"


def test_regeneration_preserves_parent_and_audits_both_actions(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        response = client.post(f"{path}/drafts/{draft['id']}/regenerate", json=decision(client, path, draft))
        assert response.status_code == 201, response.text
        regenerated = response.json()
        assert regenerated["id"] != draft["id"] and regenerated["parent_draft_id"] == draft["id"]
        assert client.get(path + "/drafts").json()["total"] == 2
        assert {"draft_generated", "draft_regenerated"} <= {item["event_type"] for item in events(client, path)}


def test_ticket_transitions_counts_and_reopening(app):
    with TestClient(app) as client:
        _, _, path = setup(client, app)
        for version, target in enumerate(["in_progress", "waiting_for_customer", "resolved", "in_progress"], 1):
            response = client.patch(path + "/status", json={"expected_version": version, "status": target, "confirmed": True})
            assert response.status_code == 200, response.text
            assert response.json()["status"] == target
        assert client.get("/api/tickets").json()["counts"]["new"] == 0
        assert client.get(path + "/workflow").json()["version"] == 5
        assert sum(item["event_type"] == "ticket_status_changed" for item in events(client, path)) == 4


def test_invalid_and_stale_status_transitions(app):
    with TestClient(app) as client:
        _, _, path = setup(client, app)
        assert client.patch(path + "/status", json={"expected_version": 1, "status": "resolved", "confirmed": True}).status_code == 409
        assert client.patch(path + "/status", json={"expected_version": 1, "status": "in_progress", "confirmed": True}).status_code == 200
        assert client.patch(path + "/status", json={"expected_version": 1, "status": "waiting_for_customer", "confirmed": True}).status_code == 409
        assert client.patch(path + "/status", json={"expected_version": 2, "status": "invented", "confirmed": True}).status_code == 422


def test_stale_edit_rejected_without_losing_original_or_first_edit(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        first = edit(client, path, draft, "First operator edit for the support reply.")
        assert first.status_code == 200
        assert edit(client, path, draft, "Second stale edit should not overwrite.").status_code == 409
        assert client.get(path + "/drafts").json()["items"][0]["reply_text"] == first.json()["reply_text"]


@pytest.mark.parametrize("unknown", [False, True])
def test_unresolved_discrepancy_blocks_approval_until_documented(app, unknown):
    with TestClient(app) as client:
        _, draft, path = setup(client, app, conflict=not unknown, unknown=unknown)
        url = f"{path}/drafts/{draft['id']}/approve"
        assert client.post(url, json=decision(client, path, draft)).status_code == 409
        state = client.get(path + "/workflow").json()
        response = client.post(path + "/discrepancy-resolutions", json={"context_fingerprint": state["context_fingerprint"],
            "reason": "Reviewed the mismatch; only a neutral clarification may be approved.", "confirmed": True})
        assert response.status_code == 201, response.text
        assert response.json()["consistency"]["requires_human_review"] is True
        assert response.json()["resolution"]["actor"] == "Local Operator"
        approved = client.post(url, json=decision(client, path, draft))
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"


def test_resolution_does_not_allow_unsafe_content_or_survive_context_change(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app, conflict=True)
        state = client.get(path + "/workflow").json()
        client.post(path + "/discrepancy-resolutions", json={"context_fingerprint": state["context_fingerprint"], "reason": "Reviewed this conflicting order information carefully.", "confirmed": True})
        edited = edit(client, path, draft, "Your LumaLite desk lamp is in transit and will arrive on 2026-11-14.").json()
        assert client.post(f"{path}/drafts/{edited['id']}/approve", json=decision(client, path, edited)).status_code == 409
        client.put(path + "/order", json={"order_id": "UNKNOWN-888"})
        new_state = client.get(path + "/workflow").json()
        assert new_state["resolution"] is None
        assert client.post(path + "/discrepancy-resolutions", json={"context_fingerprint": state["context_fingerprint"], "reason": "Stale review should not dismiss the new facts.", "confirmed": True}).status_code == 409


@pytest.mark.parametrize("text", ["We have refunded your payment.", "We will refund your payment.", "Έχουμε επιστρέψει τα χρήματά σας.", "Your refund is approved.", "Delivery is guaranteed.", "Your order will arrive on 2099-12-31.", "Your order will arrive tomorrow.", "Your smartphone was delivered today."])
def test_unsupported_manual_claims_cannot_bypass_approval(app, text):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        edited = edit(client, path, draft, text).json()
        assert client.post(f"{path}/drafts/{edited['id']}/approve", json=decision(client, path, edited)).status_code == 409


def test_no_confirmation_actor_override_or_ticket_mismatch_bypasses(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app)
        payload = decision(client, path, draft)
        url = f"{path}/drafts/{draft['id']}/approve"
        assert client.post(url, json={**payload, "confirmed": False}).status_code == 422
        assert client.post(url, json={**payload, "confirmed": 1}).status_code == 422
        assert client.post(url, json={**payload, "actor": "Administrator"}).status_code == 422
        assert client.post(url, json={"confirmed": True}).status_code == 422
        other = add_ticket(app)
        assert client.post(f"/api/tickets/{other['id']}/drafts/{draft['id']}/approve", json=payload).status_code == 404


def test_resolution_reason_required_and_audit_persists(app):
    with TestClient(app) as client:
        _, draft, path = setup(client, app, conflict=True)
        state = client.get(path + "/workflow").json()
        assert client.post(path + "/discrepancy-resolutions", json={"context_fingerprint": state["context_fingerprint"], "reason": " ", "confirmed": True}).status_code == 422
        settings = app.state.settings
        history = events(client, path)
        assert client.get(path + "/workflow").json()["identity_is_authenticated"] is False
    with TestClient(create_app(settings)) as client:
        assert events(client, path) == history


def test_additive_migration_preserves_existing_3a_rows_and_is_idempotent(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        CREATE TABLE ticket (id CHAR(32) PRIMARY KEY, message TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL,
            order_id TEXT, customer_intent TEXT, reason TEXT, status TEXT CHECK(status='new'), created_at DATETIME);
        CREATE TABLE replydraft (id CHAR(32) PRIMARY KEY, ticket_id CHAR(32), reply_text TEXT, language TEXT,
            status TEXT CHECK(status='pending_review'), model TEXT, order_context JSON, policy_version TEXT, created_at DATETIME);
        """)
        ticket_id, draft_id = uuid4().hex, uuid4().hex
        connection.execute("INSERT INTO ticket VALUES (?,?,?,?,?,?,?,?,?)", (ticket_id, 'Please help.', 'other','low', None,'Get support','General request','new','2026-11-10 12:00:00'))
        connection.execute("INSERT INTO replydraft VALUES (?,?,?,?,?,?,?,?,?)", (draft_id,ticket_id,'Original historical content','en','pending_review','qwen3.5:9b','{"reference_order_id":null,"extracted_order_id":null,"source":"extracted","lookup_status":"not_provided","order":null}','legacy','2026-11-10 12:01:00'))
    before = audit(database, '7821')["fingerprints"]
    settings = Settings(_env_file=None, database_path=database)
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/tickets/{UUID(ticket_id)}").status_code == 200
        assert client.get(f"/api/tickets/{UUID(ticket_id)}/drafts").json()["items"][0]["original_content"] == 'Original historical content'
        first_history = client.get(f"/api/tickets/{UUID(ticket_id)}/activity").json()
        assert first_history["total"] == 2
    after = audit(database, '7821')["fingerprints"]
    assert before['ticket'] == after['ticket'] and before['replydraft'] == after['replydraft']
    assert list((tmp_path / 'backups').glob('legacy-pre-3b-*.sqlite3'))
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/tickets/{UUID(ticket_id)}/activity").json() == first_history
    assert len(list((tmp_path / 'backups').glob('legacy-pre-3b-*.sqlite3'))) == 1


def test_all_required_audit_events_survive_restart_and_cannot_be_rewritten(app):
    with TestClient(app) as client:
        mock_chat(app, classification(order_id="DEMO-LAMP-9001"))
        ticket = client.post('/api/tickets', json={"message": "Where is my order #DEMO-LAMP-9001?"}).json()
        path = f"/api/tickets/{ticket['id']}"
        client.put(path + '/order', json={"order_id": "GR-1042"})
        mock_reply(app)
        draft = client.post(path + '/drafts').json()
        edited = edit(client, path, draft, "Please let us know what additional information you need.").json()
        approved = client.post(f"{path}/drafts/{draft['id']}/approve", json=decision(client, path, edited)).json()
        regenerated = client.post(f"{path}/drafts/{draft['id']}/regenerate", json=decision(client, path, approved)).json()
        client.post(f"{path}/drafts/{regenerated['id']}/reject", json=decision(client, path, regenerated, reason="Needs a more relevant explanation."))
        client.patch(path + '/status', json={"expected_version": 1, "status": "in_progress", "confirmed": True})
        client.put(path + '/order', json={"order_id": "UNKNOWN-999"})
        state = client.get(path + '/workflow').json()
        client.post(path + '/discrepancy-resolutions', json={"context_fingerprint": state['context_fingerprint'], "reason": "Order is unknown; request a corrected reference without asserting facts.", "confirmed": True})
        history = events(client, path)
        assert {"ticket_created", "ticket_status_changed", "order_reference_corrected", "draft_generated", "draft_edited", "draft_approved", "draft_rejected", "draft_regenerated", "discrepancy_documented"} <= {item['event_type'] for item in history}
        settings = app.state.settings
        with Session(app.state.engine) as session:
            event = session.get(AuditEvent, history[0]['id'])
            event.actor = 'Tampered identity'
            with pytest.raises(IntegrityError):
                session.commit()
    with TestClient(create_app(settings)) as client:
        assert events(client, path) == history


def test_failed_migration_rolls_back_without_resetting_legacy_data(tmp_path, monkeypatch):
    database = tmp_path / 'rollback.db'
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE ticket (id CHAR(32) PRIMARY KEY, message TEXT, category TEXT, priority TEXT, order_id TEXT, customer_intent TEXT, reason TEXT, status TEXT CHECK(status='new'), created_at DATETIME)")
        connection.execute("INSERT INTO ticket VALUES (?,?,?,?,?,?,?,?,?)", (uuid4().hex, 'Legacy message', 'other', 'low', None, 'Get help', 'General support', 'new', '2026-11-10 12:00:00'))
    before = audit(database, '7821')['fingerprints']['ticket']
    def fail(*args, **kwargs):
        raise RuntimeError('Simulated migration failure')
    monkeypatch.setattr('app.migrations.audit', fail)
    with pytest.raises(RuntimeError, match='Simulated migration failure'):
        with TestClient(create_app(Settings(_env_file=None, database_path=database))):
            pass
    assert audit(database, '7821')['fingerprints']['ticket'] == before
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schemamigration'").fetchone() is None
    assert list((tmp_path / 'backups').glob('rollback-pre-3b-*.sqlite3'))


def test_browser_smoke_marker_requires_the_dedicated_qa_database(tmp_path, monkeypatch):
    monkeypatch.setattr('app.main.PROJECT_ROOT', tmp_path)
    for name, expected in [('opspilot.db', False), ('milestone3b-qa.db', True)]:
        settings = Settings(_env_file=None, database_path=tmp_path / 'data' / name)
        with TestClient(create_app(settings)) as client:
            assert client.get('/api/health').json()['isolated_qa'] is expected
