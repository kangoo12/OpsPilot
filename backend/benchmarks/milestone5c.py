"""Freeze and run a small real local 5C regression, keeping prior evidence immutable."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import HTTPException
from sqlmodel import Session

from app.classifier import ChatResult, ClassificationResult, classify_message
from app.classification_rules import validate_summary_language
from app.config import PROJECT_ROOT, Settings
from app.database import create_database_engine
from app.migrations import migrate_database
from app.models import Ticket
from app.orders import seed_orders, ticket_order_context
from app.reply_generator import ReplyPlan, generate_reply
from app.schemas import TicketRead
from app.workflow_common import content_blockers
from benchmarks.reply_eta import evaluate_delivery_eta
from benchmarks.run import reply_checks, sha, write_json
from scripts.seed_milestone45_qa import fingerprints

DOCS = PROJECT_ROOT / 'docs/milestone5c'
LOCAL = PROJECT_ROOT / '.cache/milestone5c'
REVISION = 1


def cases():
    independent = json.loads((DOCS / 'regression-v1.json').read_text(encoding='utf-8'))['cases']
    replies = json.loads((DOCS / 'replies-v1.json').read_text(encoding='utf-8'))['cases']
    old = PROJECT_ROOT / 'docs/milestone5b'
    ids = json.loads((old / 'metrics-v1.json').read_text())['held_out']['language_mismatch_ids']
    known = [case for case in json.loads((old / 'heldout-v1.json').read_text(encoding='utf-8'))['cases'] if case['id'] in ids]
    required = 24 if REVISION == 1 else 8
    if len(independent) != required or sum(case['language'] == 'el' for case in independent) != required // 2 or len(known) != 11:
        raise ValueError('Incomplete regression coverage')
    existing = [case['message'] for folder in ['milestone5','milestone5b'] for name in ['classification-v1.json','heldout-v1.json']
                if (PROJECT_ROOT/'docs'/folder/name).exists()
                for case in json.loads((PROJECT_ROOT/'docs'/folder/name).read_text(encoding='utf-8'))['cases']]
    if any(case['message'] in existing for case in independent):
        raise ValueError('New regression case copies a previous message')
    return {'independent': independent, 'known5b': known, 'reply': replies}


def hashes():
    paths = [*sorted((PROJECT_ROOT/'backend/app').glob('*.py')),
             PROJECT_ROOT/'backend/benchmarks/milestone5c.py', PROJECT_ROOT/'backend/benchmarks/reply_eta.py',
             PROJECT_ROOT/'backend/benchmarks/run.py', PROJECT_ROOT/'backend/benchmarks/evaluate.py',
             PROJECT_ROOT/'backend/scripts/seed_milestone45_qa.py',
             PROJECT_ROOT/'backend/tests/test_final_reliability.py', PROJECT_ROOT/'backend/tests/test_tickets.py',
             DOCS/'regression-v1.json', DOCS/'replies-v1.json',
             *sorted((PROJECT_ROOT/'docs/milestone5').glob('*')), *sorted((PROJECT_ROOT/'docs/milestone5b').glob('*'))]
    if REVISION == 2:
        paths += [PROJECT_ROOT/'docs/milestone5c'/name for name in ['regression-v1.json','replies-v1.json','freeze-v1.json','environment-v1.json','results-v1.jsonl','eta-correction-v2.json']]
    return {path.relative_to(PROJECT_ROOT).as_posix(): sha(path) for path in paths if path.is_file()}


def verify(lock):
    if hashes() != lock['sha256']:
        raise RuntimeError('Implementation, expectations or historical evidence changed after freeze')


def correct_old_eta():
    path = PROJECT_ROOT/'docs/milestone5b/results-v1.jsonl'
    row = next(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if json.loads(line)['case_id']=='N06')
    result = evaluate_delivery_eta(row['context'], row['output'], row['output_language'])
    write_json(DOCS/'eta-correction-v2.json', {
        'source': 'docs/milestone5b/results-v1.jsonl', 'source_sha256': sha(path), 'case_id': 'N06',
        'verified_order_id': row['context']['order']['id'], 'verified_eta': row['context']['order']['estimated_delivery_date'],
        'original_assertion': 'estimate_caveat', 'original_result': row['checks']['estimate_caveat'],
        'corrected_assertion': result, 'same_preserved_output': row['output'], 'new_inference': False,
        'explanation': 'The old assertion required an estimate caveat despite no recorded ETA. Original 5B evidence and 11/12 frozen score remain unchanged; this is a separate versioned reevaluation.'})


def freeze():
    cases()
    if (DOCS/'freeze-v1.json').exists():
        raise RuntimeError('Refusing to overwrite a freeze')
    baseline = json.loads((PROJECT_ROOT/'.cache/milestone5c/baseline-lock.json').read_text())
    if any(sha(PROJECT_ROOT/name)!=digest for name,digest in baseline['evidence'].items()):
        raise RuntimeError('Historical evidence changed')
    write_json(DOCS/'freeze-v1.json', {'frozen_at': datetime.now(timezone.utc).isoformat(), 'sha256': hashes(),
               'revision': REVISION, 'order': [f'independent:{len(cases()["independent"])}', 'known5b:11', 'reply:4'], 'retries': 0,
               'mixed_language_rule': 'Dominant Greek/Latin script in first 500 prose characters after control spans, URLs/emails and digit-bearing identifiers are excluded; Greek wins a tie with at least 3 letters, otherwise English.'})
    correct_old_eta()
    print('Source and new expectations frozen; old ETA reevaluated separately without inference.')


async def execute():
    lock = json.loads((DOCS/'freeze-v1.json').read_text()); verify(lock)
    original = Settings().database_path
    path = (LOCAL/'evaluation-v1.db').resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_relative_to(LOCAL.resolve()) or path==original or path.exists() or (DOCS/'results-v1.jsonl').exists():
        raise RuntimeError('Nonisolated or existing target; no overwrite/retry allowed')
    before = fingerprints(original); write_json(LOCAL/'original-fingerprints.json', before)
    settings = Settings(_env_file=None, database_path=path, ollama_base_url='http://127.0.0.1:11434')
    engine = create_database_engine(path)
    captured=[]
    async def request_hook(request):
        if request.url.host!='127.0.0.1' or request.url.port!=11434:
            raise RuntimeError('Nonlocal inference refused')
    async def response_hook(response):
        if response.request.url.path=='/api/chat':
            await response.aread()
            payload=json.loads(response.request.content)
            captured.append({'raw':response.json(), 'settings':{key:payload[key] for key in ['model','stream','think','options','keep_alive']}})
    env={'started_at':datetime.now(timezone.utc).isoformat(),'retries':0,'serial':True,'model':settings.ollama_model,'freeze_sha256':sha(DOCS/'freeze-v1.json')}
    try:
        migrate_database(engine,path); seed_orders(engine); qa_before=fingerprints(path)
        async with httpx.AsyncClient(base_url=settings.ollama_base_url,trust_env=False,follow_redirects=False,timeout=10,event_hooks={'request':[request_hook],'response':[response_hook]}) as client:
            for endpoint,name in [('/api/version','ollama'),('/api/tags','model_release'),('/api/ps','initial_residency')]:
                response=await client.get(endpoint); response.raise_for_status(); value=response.json()
                if name=='model_release':
                    value=[model for model in value['models'] if model['name']==settings.ollama_model]
                    if len(value)!=1: raise RuntimeError('Required installed model unavailable')
                env[name]=value
            write_json(DOCS/'environment-v1.json',env)
            with (DOCS/'results-v1.jsonl').open('x',encoding='utf-8') as stream:
                for kind,values in cases().items():
                    for case in values:
                        captured.clear(); started=perf_counter()
                        row={'kind':kind,'case_id':case['id'],'language':case['language'],'cohort':case.get('cohort','reply'),
                             'expected':{key:case[key] for key in ['category','priority','order_id','human_review']},'accepted':False,'predicted':None,'schema_valid':None}
                        try:
                            if kind!='reply':
                                value=await classify_message(case['message'],client,settings)
                                row['predicted']=value.model_dump(mode='json')
                                validate_summary_language(case['message'],value.customer_intent,value.reason)
                                row['summary_language_valid']=True
                                ticket=Ticket(message=case['message'],**value.model_dump())
                                with Session(engine) as session: row['human_review']=ticket_order_context(session,ticket).consistency.status
                            else:
                                ticket=Ticket(message=case['message'],category=case['category'],priority=case['priority'],order_id=case['order_id'],customer_intent='Reply regression fixture',reason='Independent synthetic case')
                                with Session(engine) as session: context=ticket_order_context(session,ticket)
                                output,language=await generate_reply(TicketRead.model_validate(ticket),context,client,settings)
                                checks=reply_checks(case,ticket,context,output,language,captured[-1]['raw'])
                                eta=evaluate_delivery_eta(context.model_dump(mode='json'),output,language)
                                checks['fact_aware_eta_v2']=eta['passed']
                                row.update(output=output,output_language=language,context=context.model_dump(mode='json'),checks=checks,eta_evaluation=eta,
                                           existing_guard_signals=content_blockers(output,context),semantic_review='pending_human_review',disposition='not_saved_not_approved_not_sent')
                            row['accepted']=True
                        except HTTPException as error:
                            row['error']={**error.detail,'http_status':error.status_code,'cause':str(error.__cause__) if error.__cause__ else None}
                        except Exception as error:
                            row['error']={'code':'benchmark_harness_error','type':type(error).__name__,'message':str(error)}
                        row['latency_seconds']=round(perf_counter()-started,6)
                        if captured:
                            row.update(captured[-1])
                            try:
                                parsed=ChatResult.model_validate(row['raw'],strict=True)
                                value=(ReplyPlan if kind=='reply' else ClassificationResult).model_validate_json(parsed.message.content,strict=True)
                                row['schema_valid']=bool(parsed.done and parsed.done_reason=='stop' and parsed.message.role=='assistant' and not parsed.message.tool_calls)
                                row['parsed_model_output']=value.model_dump(mode='json')
                            except ValueError: row['schema_valid']=False
                        stream.write(json.dumps(row,ensure_ascii=False)+'\n'); stream.flush()
                        print(f"{kind} {case['id']}: {'accepted' if row['accepted'] else row['error']['code']} {row['latency_seconds']:.3f}s",flush=True)
    finally:
        engine.dispose(); verify(lock)
        env.update(finished_at=datetime.now(timezone.utc).isoformat(),original_tables_unchanged=fingerprints(original)==before,
                   qa_tables_unchanged=fingerprints(path)==qa_before if 'qa_before' in locals() else None,freeze_unchanged=True)
        write_json(DOCS/'environment-v1.json',env)
        if not env['original_tables_unchanged']: raise RuntimeError('Original database changed during evaluation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['freeze','execute']); parser.add_argument('--revision',type=int,choices=[1,2],default=1); args=parser.parse_args()
    REVISION=args.revision
    if REVISION==2:
        DOCS=DOCS/'followup-v2'; LOCAL=LOCAL/'followup-v2'
        DOCS.mkdir(parents=True,exist_ok=True); LOCAL.mkdir(parents=True,exist_ok=True)
    freeze() if args.action=='freeze' else asyncio.run(execute())
