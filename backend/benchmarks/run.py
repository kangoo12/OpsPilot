"""One serial real-Ollama run; no application prompt edits, production writes or approvals."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from app.classifier import ChatResult, ClassificationResult, classify_message, order_candidates
from app.config import PROJECT_ROOT, Settings
from app.database import create_database_engine
from app.migrations import migrate_database
from app.models import Order, Ticket
from app.orders import seed_orders, ticket_order_context
from app.reply_generator import ReplyPlan, generate_reply, reply_material
from app.schemas import TicketRead
from app.workflow_common import content_blockers
from benchmarks.evaluate import load_cases
from scripts.seed_milestone45_qa import fingerprints

DOCS = PROJECT_ROOT / 'docs/milestone5'
LOCAL = PROJECT_ROOT / '.cache/milestone5'
SOURCE_FILES = ['backend/app/classifier.py', 'backend/app/reply_generator.py', 'backend/app/consistency.py', 'backend/app/orders.py', 'backend/app/workflow.py', 'backend/app/workflow_common.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def hardware():
    command = "@{cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);memory_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion)} | ConvertTo-Json -Depth 5 -Compress"
    try:
        result = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True, timeout=20, check=True)
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return {'unavailable': type(error).__name__}


def reply_checks(case, ticket, context, output, language, raw):
    plan = ReplyPlan.model_validate_json(raw['message']['content'], strict=True)
    material = reply_material(ticket, context)
    dates = set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b', output))
    allowed_dates = set()
    if context.order and context.consistency.status != 'discrepancy':
        allowed_dates = {str(context.order.snapshot_date), str(context.order.order_date), str(context.order.estimated_delivery_date)}
    positive_actions = re.findall(r'we (?:have |already )?(?:refunded|contacted|cancelled|shipped)|refund (?:is|has been) approved|εγκρίθηκε η επιστροφή|επικοινωνήσαμε με', output, flags=re.I)
    checks = {
        'expected_language': language == case['language'],
        'expected_next_step': plan.next_step == case['next_step'],
        'expected_human_review_flag': context.consistency.status == case['human_review'],
        'only_verified_calendar_dates': dates <= allowed_dates,
        'only_context_order_ids': set(order_candidates(output)) <= {context.reference_order_id},
        'no_listed_positive_action_claim': not positive_actions,
        'required_renderer_facts_present': all(sentence in output for sentence in material['required']),
        'original_message_preserved': ticket.message == case['message'],
    }
    if case['human_review'] == 'discrepancy':
        checks['disputed_product_omitted'] = context.order.product not in output
        checks['explicit_human_review'] = 'Human review is needed' in output or 'Χρειάζεται ανθρώπινος έλεγχος' in output
    if case['id'] in {'R01', 'R02', 'R12'}:
        checks['estimate_not_guarantee'] = 'not a delivery guarantee' in output
    if case['id'] == 'R03':
        checks['unknown_date_explicit'] = 'No estimated delivery date is available' in output
    if case['id'] == 'R09':
        checks['card_provider_advice_present'] = 'contact your card provider' in output
    return checks


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Required explicit opt-in to 72 real local calls')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Use --execute after reviewing the versioned datasets; no inference was performed.')
    _, classifications = load_cases(DOCS / 'classification-v1.json', True)
    _, replies = load_cases(DOCS / 'replies-v1.json')
    LOCAL.mkdir(parents=True, exist_ok=True)
    path = LOCAL / 'benchmark-v1.db'
    # Fail closed before any DB write. Never read the demo DB through SQLAlchemy.
    assert path.resolve().is_relative_to(LOCAL.resolve()) and path.resolve() != Settings().database_path
    if path.exists() or (DOCS / 'results-v1.jsonl').exists():
        raise SystemExit('Existing benchmark artifacts found; refusing to overwrite or rerun the original experiment.')
    original = Settings().database_path
    before = fingerprints(original)
    write_json(LOCAL / 'original-fingerprints.json', before)
    settings = Settings(_env_file=None, database_path=path, ollama_base_url='http://127.0.0.1:11434')
    source_hashes = {name: sha(PROJECT_ROOT / name) for name in SOURCE_FILES}
    manifest = {'started_at': datetime.now(timezone.utc).isoformat(), 'dataset_sha256': {name: sha(DOCS / name) for name in ['classification-v1.json', 'replies-v1.json']},
                'source_sha256': source_hashes, 'model': settings.ollama_model, 'serial': True, 'retries': 0,
                'classification_timeout_seconds': settings.classification_timeout_seconds, 'reply_timeout_seconds': settings.reply_timeout_seconds,
                'python': platform.python_version(), 'os': platform.system() + ' ' + platform.release(), 'architecture': platform.machine(),
                'packages': {name: version(name) for name in ['sqlalchemy', 'sqlmodel', 'httpx', 'pydantic']}, 'hardware': hardware()}
    engine = create_database_engine(path)
    captured = []
    async def observe_request(request):
        assert request.url.host == '127.0.0.1' and request.url.port == 11434
    async def observe_response(response):
        if response.request.url.path == '/api/chat':
            await response.aread()
            payload = json.loads(response.request.content)
            try:
                body = response.json()
            except ValueError:
                body = {'unparseable_body': response.text[:2000]}
            captured.append({'raw': body, 'http_status': response.status_code,
                             'settings': {key: payload[key] for key in ['model', 'stream', 'think', 'options', 'keep_alive']}})
    try:
        migrate_database(engine, path)
        seed_orders(engine)
        initial_qa = fingerprints(path)
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, trust_env=False, follow_redirects=False, timeout=10,
                                     event_hooks={'request': [observe_request], 'response': [observe_response]}) as client:
            for route, key in [('/api/version', 'ollama'), ('/api/tags', 'model_release'), ('/api/ps', 'initial_residency')]:
                response = await client.get(route); response.raise_for_status()
                value = response.json()
                if key == 'model_release':
                    value = [model for model in value['models'] if model['name'] == settings.ollama_model]
                    assert len(value) == 1, 'Required installed model not found; no model will be downloaded'
                manifest[key] = value
            response = await client.post('/api/show', json={'model': settings.ollama_model}); response.raise_for_status()
            show = response.json()
            manifest['model_details'] = {key: show.get(key) for key in ['details', 'capabilities', 'parameters']}
            write_json(DOCS / 'environment-v1.json', manifest)
            with (DOCS / 'results-v1.jsonl').open('x', encoding='utf-8') as stream:
                for kind, cases in [('classification', classifications), ('reply', replies)]:
                    for index, case in enumerate(cases):
                        captured.clear()
                        row = {'kind': kind, 'case_id': case['id'], 'language': case['language'], 'cohort': case.get('cohort', 'reply_scenario'),
                               'expected': {key: case[key] for key in ['category', 'priority', 'order_id', 'human_review']},
                               'accepted': False, 'schema_valid': None, 'predicted': None, 'first_in_phase': index == 0}
                        started = perf_counter()
                        try:
                            if kind == 'classification':
                                value = await classify_message(case['message'], client, settings)
                                row['predicted'] = value.model_dump(mode='json')
                                ticket = Ticket(message=case['message'], **value.model_dump())
                                with Session(engine) as session:
                                    row['human_review'] = ticket_order_context(session, ticket).consistency.status
                            else:
                                ticket = Ticket(message=case['message'], category=case['category'], priority=case['priority'], order_id=case['order_id'], customer_intent='Benchmark fixture intent', reason='Independently authored reply scenario')
                                with Session(engine) as session:
                                    context = ticket_order_context(session, ticket)
                                original_message = ticket.message
                                output, language = await generate_reply(TicketRead.model_validate(ticket), context, client, settings)
                                row['output'] = output; row['output_language'] = language
                                row['context'] = context.model_dump(mode='json')
                                row['checks'] = reply_checks(case, ticket, context, output, language, captured[-1]['raw'])
                                assert ticket.message == original_message
                                row['existing_approval_guard_signals'] = content_blockers(output, context)
                                row['semantic_review'] = 'pending_product_owner_review'
                                row['draft_disposition'] = 'not_saved_not_approved_not_sent'
                            row['accepted'] = True
                        except HTTPException as error:
                            row['error'] = {'http_status': error.status_code, **error.detail, 'cause': str(error.__cause__) if error.__cause__ else None}
                        except Exception as error:
                            row['error'] = {'code': 'benchmark_harness_error', 'type': type(error).__name__, 'message': str(error)}
                        row['latency_seconds'] = round(perf_counter() - started, 6)
                        if captured:
                            row.update(captured[-1])
                            try:
                                envelope = ChatResult.model_validate(row['raw'], strict=True)
                                parsed = (ClassificationResult if kind == 'classification' else ReplyPlan).model_validate_json(envelope.message.content, strict=True)
                                row['schema_valid'] = envelope.done and envelope.done_reason == 'stop' and envelope.message.role == 'assistant' and not envelope.message.tool_calls
                                row['parsed_model_output'] = parsed.model_dump(mode='json')
                            except ValueError:
                                row['schema_valid'] = False
                        stream.write(json.dumps(row, ensure_ascii=False) + '\n'); stream.flush()
                        print(f"{kind} {case['id']}: {'accepted' if row['accepted'] else row['error']['code']} {row['latency_seconds']:.3f}s", flush=True)
    finally:
        engine.dispose()
        manifest['finished_at'] = datetime.now(timezone.utc).isoformat()
        manifest['original_tables_unchanged'] = fingerprints(original) == before
        manifest['qa_tables_unchanged_after_seeding'] = fingerprints(path) == initial_qa if 'initial_qa' in locals() else None
        manifest['sources_unchanged'] = all(sha(PROJECT_ROOT / name) == digest for name, digest in source_hashes.items())
        write_json(DOCS / 'environment-v1.json', manifest)
        assert manifest['original_tables_unchanged'], 'Original database changed during the run; investigate concurrent application activity'
        assert manifest['sources_unchanged'], 'Application sources changed during measurement'


if __name__ == '__main__':
    asyncio.run(run())
