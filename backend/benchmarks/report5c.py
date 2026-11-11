"""Read-only postprocessing of both preserved 5C experiments."""
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.classification_rules import immediate_physical_risk, validate_summary_language
from app.config import PROJECT_ROOT
from benchmarks import milestone5c as runner
from benchmarks.evaluate import classification_metrics, latency_stats
from benchmarks.report import fmt, table
from benchmarks.run import write_json

ROOT=PROJECT_ROOT/'docs/milestone5c'


def main():
    runner.REVISION=2; runner.DOCS=ROOT/'followup-v2'; runner.LOCAL=PROJECT_ROOT/'.cache/milestone5c/followup-v2'
    runner.verify(json.loads((runner.DOCS/'freeze-v1.json').read_text()))
    scenarios={**{case['id']:case for case in json.loads((ROOT/'regression-v1.json').read_text(encoding='utf-8'))['cases']},
               **{case['id']:case for case in json.loads((runner.DOCS/'regression-v1.json').read_text(encoding='utf-8'))['cases']},
               **{case['id']:case for case in json.loads((PROJECT_ROOT/'docs/milestone5b/heldout-v1.json').read_text(encoding='utf-8'))['cases']}}
    runs={name:[json.loads(line) for line in (folder/'results-v1.jsonl').read_text(encoding='utf-8').splitlines()]
          for name,folder in [('initial',ROOT),('followup',runner.DOCS)]}
    assert len(runs['initial'])==39 and len(runs['followup'])==23
    metrics={}; reviewed=[]
    for revision,rows in runs.items():
        metrics[revision]={}
        for kind in ['independent','known5b','reply']:
            values=[row for row in rows if row['kind']==kind]
            if kind!='reply':
                result=classification_metrics(values)
                language_count=0
                for row in values:
                    parsed=row.get('parsed_model_output')
                    language_valid=False
                    if parsed:
                        try:
                            validate_summary_language(scenarios[row['case_id']]['message'],parsed['customer_intent'],parsed['reason'])
                            language_count+=1; language_valid=True
                        except ValueError: pass
                    reviewed.append({**row,'revision':revision,'raw_language_check_passed':language_valid})
                result['raw_language_correct_count']=language_count
                result['case_count']=len(values)
            else:
                result={'cases':len(values),'accepted':sum(row['accepted'] for row in values),
                        'all_checks_passed':sum(row['accepted'] and all(row['checks'].values()) for row in values)}
            result['latency']=latency_stats(values)
            metrics[revision][kind]=result
    write_json(ROOT/'metrics-v1.json',metrics)
    with (ROOT/'classification-results-v1.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['revision','set','case_id','expected_language','raw_language_check','expected_category','model_category','expected_priority','model_priority','expected_order_id','model_order_id','accepted','latency_seconds','error'])
        for row in reviewed:
            predicted=row.get('parsed_model_output') or {}
            writer.writerow([row['revision'],row['kind'],row['case_id'],row['language'],row['raw_language_check_passed'],row['expected']['category'],predicted.get('category'),row['expected']['priority'],predicted.get('priority'),row['expected']['order_id'] or '<null>',predicted.get('order_id') or '<null>',row['accepted'],row['latency_seconds'],row.get('error',{}).get('cause','')])
    replies=[{**row,'revision':name,'human_semantic_review':'pending'} for name,rows in runs.items() for row in rows if row['kind']=='reply']
    write_json(ROOT/'reply-review-v1.json',[{key:value for key,value in row.items() if key not in {'raw','settings','context','parsed_model_output'}} for row in replies])
    old_wrong=next(row for row in runs['followup'] if row['case_id']=='HEN06')
    assert old_wrong['accepted'] and old_wrong['predicted']['priority']=='urgent'
    failures=[row for row in reviewed if not row['accepted'] or any(row['predicted'][key]!=row['expected'][key] for key in ['category','priority','order_id'])]
    initial,final=metrics['initial'],metrics['followup']
    pieces=['# Milestone 5C — final reliability corrections',
      '\nMeasured November 11, 2026. The three targeted corrections are implemented **without reverting 5B**. Original 5A/5B datasets, expectations and results remain byte-for-byte unchanged. No demo database records, UI, models or Windows settings changed.',
      '\n## Outcome and functional commit review',
      '\nThe bilingual regression is resolved in this validation: every raw classification in both runs passes the language/identifier checks (54/54), and no wrong-language summary was accepted. On the **final implementation**, all 11 formerly wrong-language 5B messages produce English summaries; 9 are accepted and 2 are rejected for customer narrative. Do not describe 11/11 language correction as 11/11 successful classifications. The electric-shock return HEN06 is now returns/urgent with null order ID. All four final reply cases pass the fact-aware ETA and grounding checks.',
      '\nFunctional review of `backend/app/classifier.py`: appropriate for commit for these corrections, with remaining narrative-generation and adversarial-priority limitations explicitly documented. Existing gender, narrative, schema, verbosity, evidence and human-review protections remain. Correct language is not a claim of overall fluent/helpful or production-grade output.',
      '\n## Root cause and exact implementation',
      '\nBefore changes, `customer_language` selected English for all 11 5B failures. `classify_message` returned Qwen strings unchanged; no translation/postprocessing caused them. The shared prompt and schema descriptions contained repeated Greek styles regardless of input, creating a plausible priming bias. Lack of runtime output-language validation allowed the observed regression. The priming mechanism is an engineering explanation, not a controlled causal ablation.',
      '\nShared category/severity/main-remedy rules are retained. Summary examples/descriptions now depend on the selected language. JSON-schema script patterns constrain generation, and an additional runtime check rejects wrong-language or identifier-only fields. No repair call, translation, generic substitution, label overwrite or fallback result is used. Gender/narrative validation still runs unchanged before the new check. Original customer messages and extracted order IDs are never rewritten.',
      '\nMixed-language rule: mask explicit control spans, exclude URLs/emails and digit-bearing identifiers for counting, then compare Greek and Latin letters in the first 500 remaining prose characters. Greek wins a tie if at least three Greek letters exist; otherwise English. Output prose follows that language. Verbatim foreign-script names/identifiers may remain only when present in non-control input and contain a capital letter or digit. Lowercase arbitrary foreign prose is not a name exception. This is a transparent script rule, not full natural-language identification; all-lowercase foreign names may need omission from the summary while the original message remains untouched.',
      '\nImmediate physical danger recognition uses narrow affirmative patterns for electric shock, burning/sparking/melting, hazardous overheating, swollen/leaking batteries, actual product injury and exposed live wires, including Greek equivalents. Explicit control spans, quoted warnings, nearby negation, historical/resolved or hypothetical contexts are excluded. For recognized current evidence, the inference schema requires urgent; a nonurgent model result is rejected rather than silently overwritten. Ordinary returns do not acquire urgent status from their category. Fraud/security still use existing model/policy priority rules. Finite recognition can miss complex phrasing or negation; it is not proof against arbitrary adversarial prose.',
      '\n## Transparent follow-up (both runs retained)',
      '\nThe first frozen experiment used 24 new cases (12 per language), 11 named 5B diagnostics and 4 reply scenarios: 39 calls. Static functional review then found that the language exception list could treat foreign words from control text as names. It was tightened to non-control, capitalized/digit-bearing tokens. A generic prevention-leaflet false-positive rule/test was also added. No existing case, label or result was changed.',
      '\nThe final implementation was frozen again and evaluated on **8 additional unseen cases** (4 per language), the same 11 named diagnostics and 4 reply confirmations: 23 calls. Both run directories, freezes, outputs and errors remain. Named diagnostics/reply confirmations are repeated checks after a code change, not extra independent successes. Original v1 application-rule and runner snapshots remain in ignored local audit files. Earlier frozen source hashes describe their historical versions; the final follow-up freeze matches current source.',
      table(['Population','Category','Priority','Order ID','Complete tuple','Invalid output','Raw language checks'],[[name,fmt(value['category']),fmt(value['priority']),fmt(value['order_id']),fmt(value['complete']),fmt(value['invalid_output']),f"{value['raw_language_correct_count']}/{value['case_count']}"] for name,value in [('Initial new 24',initial['independent']),('Initial known 11',initial['known5b']),('Final unseen 8',final['independent']),('Final known 11',final['known5b'])]]),
      '\nComplete accuracy remains the exact category/priority/order-ID tuple plus pipeline acceptance. Failed cases stay in every operational denominator, including null-ID cases. Script/name checks are reported separately and are not semantic quality ratings. The 24 and 8 sets are small, intentionally difficult, same-author synthetic sets, not production prevalence samples or externally blinded validation; their scores must not be directly compared as proof of improvement.',
      '\n## Actual remaining failures',
      table(['Revision / case','Failure'],[[row['revision']+' / '+row['case_id'],row['error']['cause'] if not row['accepted'] else 'priority '+row['predicted']['priority']+' vs expected '+row['expected']['priority']] for row in failures]),
      '\nCEN03/CEN04/CEN12, HEN07/HEN08 and final FEN04 contain customer-narrative wording and are deliberately rejected by the existing guard. No guard was relaxed to hide them. Initial CEL12 (ordinary tracking with an injected fire/urgent instruction) was labelled urgent rather than medium. The physical-evidence detector masks that role span and does not force urgent; the remaining model priority error is preserved. This broader adversarial weakness is unresolved, and no post-evaluation tuning was performed to improve that score.',
      '\n## ETA assertion correction',
      '\n5B N06 / GR-1046 had `estimated_delivery_date: null`. The actual reply explicitly said no estimated date was available and omitted the injected date. The frozen `estimate_caveat` assertion nevertheless required a caveat for a nonexistent estimate. [eta-correction-v2.json](eta-correction-v2.json) records the original false result, exact same reply, verified null and separate corrected result, with no inference. The historical 5B 11/12 score remains unchanged.',
      '\n`backend/benchmarks/reply_eta.py` adds a versioned fact-aware check: a known ETA must be exact and qualified; an open order with no ETA must explicitly preserve uncertainty; unknown/disputed data must not acquire calendar facts; closed/delivered records need no invented ETA sentence. No date is ever synthesized. Unit tests cover unknown/known/invented dates and missing caveats.',
      '\n## Real reply checks',
      table(['Run','Accepted','All finite checks passed'],[['Initial',f"{initial['reply']['accepted']}/4",f"{initial['reply']['all_checks_passed']}/4"],['Final',f"{final['reply']['accepted']}/4",f"{final['reply']['all_checks_passed']}/4"]]),
      '\nActual outputs and pending human-review markers are in [reply-review-v1.json](reply-review-v1.json). Four distinct scenarios cover English/Greek, known/unknown ETA and an unknown reference with injected date/refund/contact claims. No unsupported date, refund approval or completed-action claim was observed by the stated finite checks. All drafts remain unsaved, unapproved and unsent; semantic fluency/helpfulness still needs human review. The 5B grounded renderer, security guidance, eligibility rules and policy version v3 were not reverted.',
      '\n## Tests, latency and integrity',
      '\n**233 relevant backend tests passed**, including all existing ticket, support, consistency, workflow/approval and health regressions, the 5B AI-quality tests and new positive/negative/language/ETA tests. The length-limit test now mocks a Greek result for its Greek input instead of mocking English; its 5,000-character acceptance requirement remains. No frontend changes or new dependencies were needed.',
      table(['Run / population','N / rejected','p50 s','p95 s','Mean s','Min s','Max s'],[[rev+' / '+kind,f"{value['latency']['attempts']} / {value['latency']['failed']}",value['latency']['p50_seconds'],value['latency']['p95_seconds'],value['latency']['mean_seconds'],value['latency']['min_seconds'],value['latency']['max_seconds']] for rev,result in metrics.items() for kind,value in result.items()]),
      '\nAll 62 calls used local `qwen3.5:9b` serially, temperature 0, seed 42, thinking/streaming false, context 8192 and unchanged 120-second pipeline bounds. First calls may include model loading; these small run distributions are not steady-state SLAs. Raw Ollama token/load/eval durations are retained in each results JSONL. No new hardware profile was captured.',
      '\nOriginal database table fingerprints and all 5A/5B evidence hashes match the pre-work lock. The QA target is verified repository-local and distinct from production before seeding. No benchmark ticket/draft/approval writes occurred. Final source/expectation freeze verification passes. No commits, pushes, Windows settings or original data changes were made.',
      '\n## Commit readiness and stop point',
      '\nSee [commit-readiness.md](commit-readiness.md) for every actual changed/new path, per-file reasons and ignored artifacts. This review includes the already-uncommitted 5B work rather than assuming it was committed. Classifier bilingual functional review passes on the stated evidence, with fail-closed availability errors and the broader priority-injection limitation disclosed. Do not describe this as production-grade reliability or start presentation work from these metrics alone. Milestone 5C stops here.',
    ]
    (ROOT/'report.md').write_text('\n\n'.join(pieces)+'\n',encoding='utf-8')
    print(json.dumps({key:{kind:{k:value[k] for k in ['category','priority','complete','raw_language_correct_count'] if k in value} for kind,value in result.items()} for key,result in metrics.items()},indent=2))


if __name__=='__main__': main()
