"""One-shot local release audit. Separate QA databases; immutable prior evidence."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.classifier import classify_message, validate_summary, ClassificationResult
from app.classification_rules import validate_summary_language
from app.config import PROJECT_ROOT, Settings
from app.main import create_app
from app.models import Ticket
from app.orders import ticket_order_context
from app.reply_generator import generate_reply
from app.schemas import TicketRead
from app.workflow_common import audit, content_blockers
from app.workflow_models import TicketWorkflow
from scripts.seed_milestone45_qa import fingerprints

ROOT = PROJECT_ROOT
LOCAL = ROOT / '.cache/milestone5d'
DOCS = ROOT / 'docs/milestone5d'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_original():
    baseline = json.loads((LOCAL / 'baseline.json').read_text())
    assert fingerprints(Path(baseline['original_database'])) == baseline['tables'], 'Original data changed'
    assert all(sha(ROOT / name) == digest for name, digest in baseline['history'].items()), 'Historical evidence changed'
    return {'original_tables_unchanged': True, 'table_count': len(baseline['tables']),
            'historical_files_unchanged': True, 'historical_file_count': len(baseline['history'])}


def settings_for(name):
    path = (LOCAL / name).resolve()
    assert path.is_relative_to(LOCAL.resolve()) and path.is_relative_to(ROOT.resolve())
    assert path != Settings().database_path and not path.exists(), 'Nonisolated/existing database refused'
    return Settings(_env_file=None, database_path=path, ollama_base_url='http://127.0.0.1:11434')


def source_hashes():
    paths = [*sorted((ROOT/'backend/app').glob('*.py')), DOCS/'scenarios-v1.json',
             Path(__file__), ROOT/'frontend/scripts/smoke5d.mjs', ROOT/'backend/tests/test_release_audit.py']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def prepare():
    verify_original()
    settings = settings_for('browser-qa.db')
    run_id = str(uuid4())
    app = create_app(settings)
    # Identity is asserted before startup migrations or any fixture writes.
    with TestClient(app):
        assert Path(app.state.engine.url.database).resolve() == settings.database_path
        with Session(app.state.engine) as session:
            ids = []
            for index in range(24):
                message = f'QA5D {run_id}: fictional general request {index}.'
                reference = None
                if index == 0:
                    message = f'QA5D {run_id}: My smartphone from order DEMO-LAMP-9001 arrived today.'
                    reference = 'DEMO-LAMP-9001'
                if index == 1:
                    message = f'QA5D {run_id}: <img src=x onerror="window.auditXss=1"> <script>window.auditXss=1</script>'
                ticket = Ticket(message=message, order_id=reference, category='other',
                                priority=['low','medium','high','urgent'][index % 4],
                                customer_intent='Review synthetic request', reason='Synthetic browser pagination fixture.',
                                created_at=datetime.now(timezone.utc)-timedelta(hours=index+1))
                session.add(ticket); session.flush()
                session.add(TicketWorkflow(ticket_id=ticket.id))
                audit(session, ticket.id, 'ticket_created', data={'synthetic_qa': True}, timestamp=ticket.created_at)
                ids.append(str(ticket.id))
            session.commit()
    write(LOCAL/'seed.json', {'run_id': run_id, 'database': '.cache/milestone5d/browser-qa.db',
                            'conflict_id': ids[0], 'xss_id': ids[1], 'total': 24})
    write(DOCS/'freeze-v1.json', {'frozen_at': datetime.now(timezone.utc).isoformat(),
                                 'sha256': source_hashes(), 'retries': 0,
                                 'expected_source': 'scenarios-v1.json authored before inference',
                                 'known_diagnostics': ['HEN07','HEN08','CEL12']})
    print('Fresh isolated browser QA seeded; implementation and new expectations frozen.')
    print(json.dumps(verify_original()))


async def evaluate():
    freeze = json.loads((DOCS/'freeze-v1.json').read_text())
    assert source_hashes() == freeze['sha256']
    verify_original()
    settings = settings_for('quality-qa.db')
    output = DOCS/'ai-results-v1.jsonl'
    assert not output.exists(), 'No overwrite/retry'
    cases = json.loads((DOCS/'scenarios-v1.json').read_text(encoding='utf-8'))['cases']
    captured = []
    async def capture(response):
        if response.request.url.path == '/api/chat':
            await response.aread(); captured.append(response.json())
    async def local_only(request):
        assert request.url.host == '127.0.0.1' and request.url.port == 11434
    app = create_app(settings)
    with TestClient(app):
        assert Path(app.state.engine.url.database).resolve() == settings.database_path
        qa_before = fingerprints(settings.database_path)
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, trust_env=False, follow_redirects=False,
                                    timeout=10, event_hooks={'request':[local_only], 'response':[capture]}) as client:
            tags = (await client.get('/api/tags')).json()
            model = next(m for m in tags['models'] if m['name'] == settings.ollama_model)
            write(DOCS/'environment-v1.json', {'model': model['name'], 'digest': model['digest'],
                                              'ollama': (await client.get('/api/version')).json(),
                                              'local_only': True, 'serial': True, 'thinking': False})
            known = []
            for folder, filename, ids in [('milestone5b','heldout-v1.json',['HEN07','HEN08']),
                                           ('milestone5c','regression-v1.json',['CEL12'])]:
                known += [c for c in json.loads((ROOT/'docs'/folder/filename).read_text(encoding='utf-8'))['cases'] if c['id'] in ids]
            with output.open('x', encoding='utf-8') as stream:
                for case in cases + known:
                    captured.clear(); started = perf_counter()
                    row = {'id': case['id'], 'kind': 'new' if case in cases else 'known_diagnostic',
                           'expected': {k:case[k] for k in ['category','priority','order_id']}, 'accepted': False}
                    try:
                        value = await classify_message(case['message'], client, settings)
                        row.update(accepted=True, classification=value.model_dump(mode='json'))
                        row['complete_match'] = all(getattr(value,k)==case[k] for k in row['expected'])
                    except HTTPException as error:
                        row.update(error={'status':error.status_code,'detail':error.detail,'cause':str(error.__cause__)}, complete_match=False)
                    row['classification_seconds'] = round(perf_counter()-started,6)
                    row['raw_classification'] = captured[-1] if captured else None
                    if captured:
                        try:
                            raw = ClassificationResult.model_validate_json(captured[-1]['message']['content'])
                            validate_summary_language(case['message'],raw.customer_intent,raw.reason)
                            row['raw_language_pass'] = True
                            validate_summary(case['message'],raw)
                            row['summary_guard_pass'] = True
                        except ValueError as error:
                            row['summary_guard_error'] = str(error)
                    if case in cases:
                        # Reply checks use frozen labels even if classification fails.
                        # This is isolated reply evaluation, not a claimed end-to-end success.
                        ticket = Ticket(message=case['message'], **row['expected'], customer_intent='Audit fixture', reason='Frozen synthetic reply context')
                        with Session(app.state.engine) as session: context = ticket_order_context(session,ticket)
                        row['reply_basis'] = 'frozen labels; transient ticket, not persisted'
                        row['context'] = context.model_dump(mode='json')
                        row['consistency_match'] = context.consistency.status == case['consistency']
                        captured.clear(); started = perf_counter()
                        try:
                            text, language = await generate_reply(TicketRead.model_validate(ticket),context,client,settings)
                            row['reply'] = {'text':text,'language':language,'language_match':language==case['language'],
                                            'guard_signals':content_blockers(text,context),'human_review':'required; not approved or sent'}
                        except HTTPException as error:
                            row['reply_error'] = {'status':error.status_code,'detail':error.detail,'cause':str(error.__cause__)}
                        row['reply_seconds'] = round(perf_counter()-started,6)
                        row['raw_reply'] = captured[-1] if captured else None
                    stream.write(json.dumps(row,ensure_ascii=False)+'\n'); stream.flush()
                    print(f"{row['id']}: accepted={row['accepted']} exact={row['complete_match']}",flush=True)
        assert qa_before == fingerprints(settings.database_path), 'Quality probe unexpectedly wrote rows'
    assert source_hashes() == freeze['sha256']
    write(DOCS/'data-integrity-v1.json', {**verify_original(), 'quality_rows_unchanged':True, 'source_freeze_matches':True})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','evaluate','verify']); args=parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'evaluate': asyncio.run(evaluate())
    else: print(json.dumps(verify_original()))
