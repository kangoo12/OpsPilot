"""Independent 5D regressions; all mutations use the isolated pytest database."""
import pytest
from fastapi.testclient import TestClient

from test_support import add_ticket, mock_reply
from test_workflow import decision, edit


@pytest.mark.parametrize('reference,message', [
    ('UNKNOWN-5201', 'Please locate order UNKNOWN-5201.'),
    (None, 'Please locate my purchase.'),
    ('DEMO-LAMP-9001', 'My smartphone was delivered today.'),
])
def test_review_documentation_cannot_authorize_a_different_order(app, reference, message):
    with TestClient(app) as client:
        mock_reply(app)
        ticket = add_ticket(app, message=message, order_id=reference)
        path = f"/api/tickets/{ticket['id']}"
        draft = client.post(path + '/drafts').json()
        state = client.get(path + '/workflow').json()
        assert client.post(path + '/discrepancy-resolutions', json={
            'context_fingerprint': state['context_fingerprint'], 'confirmed': True,
            'reason': 'Reviewed missing or conflicting facts; clarification is still required.',
        }).status_code == 201
        altered = edit(client, path, draft, 'Please use order #FAKE-5202 for this request.').json()
        response = client.post(f"{path}/drafts/{altered['id']}/approve", json=decision(client, path, altered))
        assert response.status_code == 409, response.text
        assert response.json()['detail']['code'] == 'approval_blocked'
        assert client.get(path + '/drafts').json()['items'][0]['status'] == 'pending_review'
        # Referring to the supplied reference for clarification remains allowed.
        neutral = f'Please check order #{reference} on your confirmation.' if reference else 'Please provide your order reference.'
        corrected = edit(client, path, altered, neutral).json()
        assert client.post(f"{path}/drafts/{corrected['id']}/approve", json=decision(client, path, corrected)).status_code == 200


def test_search_literal_sql_payload_and_contract_enums(app):
    with TestClient(app) as client:
        add_ticket(app)
        response = client.get('/api/tickets', params={'search': "%' OR 1=1 --"})
        assert response.status_code == 200
        assert response.json()['counts']['total'] == 0
        assert client.get('/api/tickets').json()['counts']['total'] == 1
        schema = client.get('/openapi.json').json()['components']['schemas']
        assert schema['Category']['enum'] == ['delivery', 'returns', 'payments', 'technical_support', 'other']
        assert schema['Priority']['enum'] == ['low', 'medium', 'high', 'urgent']
        assert schema['TicketStatus']['enum'] == ['new', 'in_progress', 'waiting_for_customer', 'resolved']
