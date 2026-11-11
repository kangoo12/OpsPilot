"""Restart only the preserved 5D QA database; make read-only API requests."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx

from app.config import PROJECT_ROOT, Settings
from scripts.audit_milestone5d import verify_original, write
from scripts.seed_milestone45_qa import fingerprints


def main():
    folder = PROJECT_ROOT / '.cache/milestone5d'
    path = (folder / 'browser-qa.db').resolve()
    seed = json.loads((folder / 'seed.json').read_text())
    previous = json.loads((folder / 'browser-results-resumed.json').read_text(encoding='utf-8'))
    before = json.loads((folder / 'pre-restart.json').read_text())
    destination = PROJECT_ROOT / 'docs/milestone5d/restart-verification-v1.json'
    assert not destination.exists(), 'Preserve existing evidence'
    assert path.is_relative_to(folder.resolve()) and path != Settings().database_path
    assert path.exists() and seed['database'] == '.cache/milestone5d/browser-qa.db'
    assert fingerprints(path) == before, 'QA rows changed since browser pass'
    verify_original()
    # A separate port prevents interaction with an existing user/server session.
    port = 8016
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))
    environment = {**os.environ, 'DATABASE_PATH': str(path), 'PYTHONUTF8': '1',
                   'OLLAMA_BASE_URL': 'http://127.0.0.1:11434', 'OLLAMA_MODEL': 'qwen3.5:9b'}
    target = previous['tickets'][0]['id']
    rounds = []
    for number in (1, 2):
        with (folder / f'restart-{number}.log').open('x', encoding='utf-8') as log:
            process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
                cwd=PROJECT_ROOT / 'backend', env=environment, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            try:
                started = time.monotonic()
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=2) as client:
                    while True:
                        assert process.poll() is None, 'QA server exited before startup'
                        try:
                            response = client.get('/api/health')
                            if response.status_code == 200:
                                break
                        except httpx.RequestError:
                            pass
                        assert time.monotonic() - started < 15, 'QA startup timeout'
                        time.sleep(0.1)
                    startup = round(time.monotonic() - started, 3)
                    def get(route):
                        response = client.get(route)
                        response.raise_for_status()
                        return response.json()
                    assert seed['run_id'] in get(f"/api/tickets/{seed['conflict_id']}")['message']
                    ticket = get(f'/api/tickets/{target}')
                    assert ticket['status'] == 'in_progress'
                    assert ticket['message'] == previous['tickets'][0]['message']
                    drafts = get(f'/api/tickets/{target}/drafts')
                    assert drafts['total'] == 3
                    assert sorted(d['status'] for d in drafts['items']) == ['approved', 'pending_review', 'rejected']
                    approved = next(d for d in drafts['items'] if d['status'] == 'approved')
                    assert approved['reply_text'] == previous['generatedDraft'] + '\n\nPlease let us know if you need further clarification.'
                    history = get(f"/api/tickets/{target}/drafts/{approved['id']}/revisions")
                    assert [r['action'] for r in history] == ['created', 'edited', 'approved']
                    events = get(f'/api/tickets/{target}/activity?limit=100')['items']
                    assert {'draft_approved', 'draft_rejected', 'draft_regenerated', 'ticket_status_changed'} <= {e['event_type'] for e in events}
                    metrics = get('/api/analytics')
                    assert metrics['total_tickets'] == 26
                    assert metrics['draft_decisions'] == {'approved': 1, 'rejected': 1}
                    rounds.append({'startup_seconds': startup, 'health': 'ok', 'qa_sentinel_verified': True,
                                   'tickets': 26, 'drafts_on_target': 3, 'status': 'in_progress',
                                   'approved_content_and_history_preserved': True,
                                   'analytics_matches': True})
            finally:
                # Terminate only the process created above. No shared services touched.
                process.terminate()
                process.wait(timeout=10)
        assert fingerprints(path) == before, 'Startup or read-only checks changed QA rows'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    result = {**verify_original(), 'qa_rows_match_pre_restart': True, 'qa_sqlite_integrity': 'ok',
              'qa_foreign_key_violations': 0, 'process_starts': rounds, 'inference_calls': 0,
              'api_mutations': 0, 'test_servers_stopped': True}
    write(destination, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
