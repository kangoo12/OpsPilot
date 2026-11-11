"""Frozen, serial 5B evaluation. Never overwrites 5A data or evaluates with mocks."""
import argparse
import asyncio
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import HTTPException
from sqlmodel import Session

from app.classifier import ChatResult, ClassificationResult, classify_message
from app.config import PROJECT_ROOT, Settings
from app.database import create_database_engine
from app.migrations import migrate_database
from app.models import Ticket
from app.orders import seed_orders, ticket_order_context
from app.reply_generator import ReplyPlan, generate_reply
from app.schemas import Category, Priority, TicketRead
from app.workflow_common import content_blockers
from benchmarks.evaluate import classification_metrics, latency_stats
from benchmarks.run import reply_checks, sha, write_json
from scripts.seed_milestone45_qa import fingerprints

DOCS = PROJECT_ROOT / 'docs/milestone5b'
LOCAL = PROJECT_ROOT / '.cache/milestone5b'
SETS = {'held_out': DOCS / 'heldout-v1.json', 'development': PROJECT_ROOT / 'docs/milestone5/classification-v1.json', 'reply': DOCS / 'reply-scenarios-v1.json'}


def datasets():
    result = {name: json.loads(path.read_text(encoding='utf-8'))['cases'] for name, path in SETS.items()}
    for name, cases in result.items():
        if len({case['id'] for case in cases}) != len(cases):
            raise ValueError('Duplicate case IDs')
        for case in cases:
            Category(case['category']); Priority(case['priority'])
            if case['language'] not in {'en', 'el'}:
                raise ValueError('Unsupported language')
    held = result['held_out']
    if len(held) < 40 or sum(case['language'] == 'en' for case in held) != 20 or sum(case['language'] == 'el' for case in held) != 20:
        raise ValueError('Held-out language coverage is incomplete')
    development = {case['message'] for case in result['development']}
    if any(case['message'] in development for case in held):
        raise ValueError('Held-out message duplicates the development set')
    return result


def frozen_files():
    paths = [*sorted((PROJECT_ROOT / 'backend/app').glob('*.py')),
             PROJECT_ROOT / 'backend/benchmarks/milestone5b.py', PROJECT_ROOT / 'backend/benchmarks/evaluate.py',
             PROJECT_ROOT / 'backend/benchmarks/run.py', PROJECT_ROOT / 'backend/scripts/seed_milestone45_qa.py',
             PROJECT_ROOT / 'backend/tests/test_ai_quality.py', PROJECT_ROOT / 'backend/tests/test_support.py',
             DOCS / 'reply-rubric.md', DOCS / 'root-causes.md',
             *SETS.values(), *sorted((PROJECT_ROOT / 'docs/milestone5').glob('*'))]
    return {path.relative_to(PROJECT_ROOT).as_posix(): sha(path) for path in paths if path.is_file()}


def verify_freeze(lock):
    current = frozen_files()
    if current != lock['sha256']:
        changed = sorted(name for name in set(current) | set(lock['sha256']) if current.get(name) != lock['sha256'].get(name))
        raise RuntimeError('Freeze mismatch: ' + ', '.join(changed))


def verified_qa_path(path, original):
    root = PROJECT_ROOT.resolve()
    local = LOCAL.resolve()
    path = path.resolve()
    if not local.is_relative_to(root) or not path.is_relative_to(local) or path == original.resolve() or path.exists():
        raise ValueError('Refusing an existing, non-isolated or original database path')
    return path


def freeze():
    datasets()
    if (DOCS / 'freeze-v1.json').exists():
        raise RuntimeError('Freeze already exists; do not overwrite or tune a completed evaluation')
    LOCAL.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((LOCAL / 'baseline-lock.json').read_text())
    for name, digest in baseline['milestone5a'].items():
        if sha(PROJECT_ROOT / name) != digest:
            raise RuntimeError('5A evidence was changed')
    write_json(DOCS / 'freeze-v1.json', {'frozen_at': datetime.now(timezone.utc).isoformat(),
        'order': ['held_out:40', 'development:60', 'reply:12'], 'retries': 0,
        'sha256': frozen_files(), 'independence_limit': 'Authored by the implementer before inference; not externally blinded.'})
    print('Implementation, original 5A evidence and new expectations frozen. No inference performed.')


def extra_reply_checks(case, ticket, context, output, language, raw):
    checks = reply_checks(case, ticket, context, output, language, raw)
    plan = ReplyPlan.model_validate_json(raw['message']['content'], strict=True)
    for requirement in case['requirements']:
        if requirement == 'no_order_request':
            okay = plan.next_step not in {'provide_order_id', 'check_order_id', 'clarify_order_details'}
        elif requirement == 'card_advice':
            okay = 'contact your card provider' in output or 'πάροχο της κάρτας' in output
        elif requirement == 'account_advice':
            okay = 'official account recovery' in output or 'επίσημες διαδικασίες ανάκτησης' in output
        elif requirement == 'no_secrets':
            okay = not re.search(r'please (?:provide|send|share) (?:your )?(?:password|full card|security code)', output, re.I)
        elif requirement == 'warranty_once':
            okay = output.lower().count('warranty') <= 1
        elif requirement == 'only_missing_details':
            okay = any(text in output for text in ['any missing', 'not already included', 'όσα στοιχεία λείπουν', 'δεν έχετε ήδη αναφέρει'])
        elif requirement == 'ineligibility_explicit':
            okay = 'does not indicate eligibility' in output
        elif requirement == 'no_30_day_policy':
            okay = '30' not in output
        elif requirement == 'disputed_facts_omitted':
            okay = bool(context.order) and context.order.product not in output
        elif requirement == 'explicit_review':
            okay = 'Human review is needed' in output or 'Χρειάζεται ανθρώπινος έλεγχος' in output
        elif requirement == 'estimate_caveat':
            okay = 'not a delivery guarantee' in output or 'όχι για εγγύηση' in output
        elif requirement == 'no_injected_date':
            okay = '2098-04-12' not in output
        elif requirement == 'unknown_reference':
            okay = context.lookup_status == 'unknown' and not context.order
        elif requirement == 'no_refund_approval':
            okay = not re.search(r'(?:refund (?:is|has been) approved|εγκρίθηκε (?:η )?επιστροφή)', output, re.I)
        else:
            raise ValueError('Unknown rubric requirement: ' + requirement)
        checks[requirement] = bool(okay)
    return checks


async def execute():
    lock = json.loads((DOCS / 'freeze-v1.json').read_text())
    verify_freeze(lock)
    data = datasets()
    original = Settings().database_path
    path = verified_qa_path(LOCAL / 'evaluation-v1.db', original)
    if (DOCS / 'results-v1.jsonl').exists():
        raise RuntimeError('Results already exist; no reruns or overwrite allowed')
    before = fingerprints(original)
    write_json(LOCAL / 'original-fingerprints.json', before)
    settings = Settings(_env_file=None, database_path=path, ollama_base_url='http://127.0.0.1:11434')
    engine = create_database_engine(path)
    environment = {'started_at': datetime.now(timezone.utc).isoformat(), 'model': settings.ollama_model,
                   'serial': True, 'retries': 0, 'timeout_seconds': 120, 'freeze_sha256': sha(DOCS / 'freeze-v1.json')}
    captured = []
    async def request_hook(request):
        if request.url.host != '127.0.0.1' or request.url.port != 11434:
            raise RuntimeError('Nonlocal inference refused')
    async def response_hook(response):
        if response.request.url.path != '/api/chat':
            return
        await response.aread()
        payload = json.loads(response.request.content)
        try:
            body = response.json()
        except ValueError:
            body = {'unparseable_body': response.text[:2000]}
        captured.append({'raw': body, 'http_status': response.status_code,
                         'settings': {key: payload[key] for key in ['model', 'stream', 'think', 'options', 'keep_alive']}})
    try:
        migrate_database(engine, path); seed_orders(engine)
        qa_before = fingerprints(path)
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, trust_env=False, follow_redirects=False, timeout=10,
                                     event_hooks={'request': [request_hook], 'response': [response_hook]}) as client:
            for endpoint, name in [('/api/version', 'ollama'), ('/api/tags', 'model_release'), ('/api/ps', 'initial_residency')]:
                response = await client.get(endpoint); response.raise_for_status()
                value = response.json()
                if name == 'model_release':
                    value = [model for model in value['models'] if model['name'] == settings.ollama_model]
                    if len(value) != 1:
                        raise RuntimeError('Required installed model unavailable')
                environment[name] = value
            write_json(DOCS / 'environment-v1.json', environment)
            with (DOCS / 'results-v1.jsonl').open('x', encoding='utf-8') as stream:
                for kind in ['held_out', 'development', 'reply']:
                    for index, case in enumerate(data[kind]):
                        captured.clear()
                        row = {'kind': kind, 'case_id': case['id'], 'language': case['language'], 'cohort': case.get('cohort', 'reply_scenario'),
                               'expected': {key: case[key] for key in ['category', 'priority', 'order_id', 'human_review']},
                               'accepted': False, 'predicted': None, 'schema_valid': None, 'first_in_phase': index == 0}
                        started = perf_counter()
                        try:
                            if kind != 'reply':
                                value = await classify_message(case['message'], client, settings)
                                row['predicted'] = value.model_dump(mode='json')
                                ticket = Ticket(message=case['message'], **value.model_dump())
                                with Session(engine) as session:
                                    row['human_review'] = ticket_order_context(session, ticket).consistency.status
                            else:
                                ticket = Ticket(message=case['message'], category=case['category'], priority=case['priority'], order_id=case['order_id'],
                                                customer_intent='Independent reply scenario', reason='Synthetic benchmark fixture')
                                with Session(engine) as session:
                                    context = ticket_order_context(session, ticket)
                                output, language = await generate_reply(TicketRead.model_validate(ticket), context, client, settings)
                                row.update(output=output, output_language=language, context=context.model_dump(mode='json'),
                                           checks=extra_reply_checks(case, ticket, context, output, language, captured[-1]['raw']),
                                           existing_guard_signals=content_blockers(output, context), semantic_status='pending_product_owner_review',
                                           disposition='not_saved_not_approved_not_sent')
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
                                parsed = (ReplyPlan if kind == 'reply' else ClassificationResult).model_validate_json(envelope.message.content, strict=True)
                                row['schema_valid'] = bool(envelope.done and envelope.done_reason == 'stop' and envelope.message.role == 'assistant' and not envelope.message.tool_calls)
                                row['parsed_model_output'] = parsed.model_dump(mode='json')
                            except ValueError:
                                row['schema_valid'] = False
                        stream.write(json.dumps(row, ensure_ascii=False) + '\n'); stream.flush()
                        print(f"{kind} {case['id']}: {'accepted' if row['accepted'] else row['error']['code']} {row['latency_seconds']:.3f}s", flush=True)
    finally:
        engine.dispose()
        environment.update(finished_at=datetime.now(timezone.utc).isoformat(), original_tables_unchanged=fingerprints(original) == before,
                           qa_tables_unchanged=fingerprints(path) == qa_before if 'qa_before' in locals() else None)
        try:
            verify_freeze(lock); environment['freeze_unchanged'] = True
        except RuntimeError:
            environment['freeze_unchanged'] = False
            raise
        finally:
            write_json(DOCS / 'environment-v1.json', environment)
        if not environment['original_tables_unchanged']:
            raise RuntimeError('Original database changed during evaluation; investigate concurrent activity')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'execute'])
    action = parser.parse_args().action
    if action == 'freeze':
        freeze()
    else:
        asyncio.run(execute())


if __name__ == '__main__':
    main()
