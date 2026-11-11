"""5B postprocessing only: no new inference or ground-truth edits."""
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import PROJECT_ROOT
from benchmarks.evaluate import classification_metrics, latency_stats, rate
from benchmarks.milestone5b import DOCS, LOCAL, datasets, verify_freeze
from benchmarks.report import fmt, table
from benchmarks.run import write_json
from scripts.seed_milestone45_qa import fingerprints


def script_language(text):
    greek = len(re.findall(r'[\u0370-\u03ff\u1f00-\u1fff]', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    return 'el' if greek >= 3 and greek >= latin else 'en'


def summary_language_matches(row):
    return row['accepted'] and all(script_language(row['predicted'][key]) == row['language'] for key in ['customer_intent', 'reason'])


def extend_metrics(rows):
    result = classification_metrics(rows)
    result['gender_guard_failures'] = rate(sum(row.get('error', {}).get('cause') == 'Gendered customer assumption' for row in rows), len(rows))
    result['narrative_guard_failures'] = rate(sum(row.get('error', {}).get('cause') == 'Summary contains customer narrative' for row in rows), len(rows))
    result['summary_language_agreement_proxy'] = rate(sum(summary_language_matches(row) for row in rows), len(rows))
    result['tuple_and_summary_language_proxy'] = rate(sum(summary_language_matches(row) and all(row['predicted'][key] == row['expected'][key] for key in ['category','priority','order_id']) for row in rows), len(rows))
    result['language_mismatch_ids'] = [row['case_id'] for row in rows if row['accepted'] and not summary_language_matches(row)]
    return result


def main():
    verify_freeze(json.loads((DOCS / 'freeze-v1.json').read_text()))
    data = datasets()
    rows = [json.loads(line) for line in (DOCS / 'results-v1.jsonl').read_text(encoding='utf-8').splitlines()]
    groups = {kind: [row for row in rows if row['kind'] == kind] for kind in ['held_out', 'development', 'reply']}
    if {key: len(value) for key, value in groups.items()} != {'held_out': 40, 'development': 60, 'reply': 12}:
        raise RuntimeError('Incomplete run: retain artifacts and report partial results rather than claiming completion')
    original_rows = [json.loads(line) for line in (PROJECT_ROOT / 'docs/milestone5/results-v1.jsonl').read_text(encoding='utf-8').splitlines()]
    baseline = [row for row in original_rows if row['kind'] == 'classification']
    metrics = {'baseline_5a': extend_metrics(baseline), 'development': extend_metrics(groups['development']), 'held_out': extend_metrics(groups['held_out'])}
    for kind in ['development', 'held_out']:
        metrics[kind]['by_language'] = {language: extend_metrics([row for row in groups[kind] if row['language'] == language]) for language in ['en','el']}
        metrics[kind]['by_cohort'] = {cohort: extend_metrics([row for row in groups[kind] if row['cohort'] == cohort]) for cohort in ['normal','ambiguous','adversarial']}
    populations = [('5A classification steady', baseline[1:]), ('5B development warm', groups['development']),
                   ('5B held-out all', groups['held_out']), ('5B held-out steady', groups['held_out'][1:]),
                   ('5A replies', [row for row in original_rows if row['kind']=='reply']), ('5B new replies', groups['reply'])]
    performance = {name: {**latency_stats(values), 'input_tokens': sum(row.get('raw',{}).get('prompt_eval_count',0) for row in values),
                          'output_tokens': sum(row.get('raw',{}).get('eval_count',0) for row in values)} for name,values in populations}
    metrics['performance'] = performance
    metrics['replies'] = {'accepted': len([row for row in groups['reply'] if row['accepted']]), 'all_checks_passed': sum(row['accepted'] and all(row['checks'].values()) for row in groups['reply']), 'total': 12}
    write_json(DOCS / 'metrics-v1.json', metrics)
    with (DOCS / 'classification-results-v1.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['set','case_id','expected_language','expected_category','model_category','expected_priority','model_priority','expected_order_id','model_order_id','schema_valid','accepted','summary_language_proxy_matches','latency_seconds','error_code','error_cause'])
        for row in groups['held_out'] + groups['development']:
            value = row.get('parsed_model_output') or {}
            writer.writerow([row['kind'],row['case_id'],row['language'],row['expected']['category'],value.get('category'),row['expected']['priority'],value.get('priority'),row['expected']['order_id'] or '<null>',value.get('order_id') or '<null>',row['schema_valid'],row['accepted'],summary_language_matches(row),row['latency_seconds'],row.get('error',{}).get('code',''),row.get('error',{}).get('cause','')])
    observations = {
        'N01': 'Card guidance and no order-ID prerequisite; wording remains conditional and no action is promised.',
        'N02': 'Official recovery guidance without order lookup, credentials or claimed account changes.',
        'N03': 'Warranty uncertainty stated once; implicit possession versus the in-transit snapshot remains a semantic concern not caught by explicit consistency rules.',
        'N04': 'Ineligibility is explicit and the generic 30-day policy is absent; humans must assess whether a return request is still useful.',
        'N05': 'Explicit delivery contradiction remains a clarification request; no explanatory story invented.',
        'N06': 'Correctly says no ETA exists and omits injected date. Frozen fixture incorrectly required an estimate caveat despite the actual seed record having no ETA. Strict failed check retained.',
        'N07': 'Greek card-provider guidance without asking for an unavailable purchase reference; naturalness needs human review.',
        'N08': 'Greek official recovery guidance without warranty/order detour.',
        'N09': 'Avoids irrelevant order request and invented corporate facts, but asks for clarification although the policy question is already clear; usefulness remains limited.',
        'N10': 'Missing-details wording avoids an unconditional repeat request, but eligibility plus generic review policy still produces a long reply.',
        'N11': 'Unknown reference remains unknown; conditional warranty language does not approve coverage.',
        'N12': 'Website troubleshooting question avoids product/order/warranty assumptions; clarity and adequacy remain human judgments.',
    }
    review = [{**row, 'scenario': case['scenario'], 'assistant_qualitative_observation': observations[row['case_id']],
               'human_ratings': {dimension: 'pending' for dimension in ['grounding','safety','relevance','helpfulness','language','clarity_naturalness']}}
              for row, case in zip(groups['reply'], data['reply'], strict=True)]
    # Raw plans/timings already exist in results.jsonl; the review copy keeps readable essentials.
    write_json(DOCS / 'reply-review-v1.json', [{key: value for key,value in row.items() if key not in {'raw','settings','context','parsed_model_output'}} for row in review])
    env = json.loads((DOCS / 'environment-v1.json').read_text())
    old_env = json.loads((PROJECT_ROOT / 'docs/milestone5/environment-v1.json').read_text())
    b, d, h = (metrics[key] for key in ['baseline_5a','development','held_out'])
    pieces = ['# OpsPilot Milestone 5B — targeted improvements and frozen validation',
        '\nCompleted November 11, 2026. **40 new held-out classifications, 60 development-set reruns and 12 new replies**, each exactly once; zero retries. Implementation and expectations were frozen before inference. No post-evaluation tuning, ground-truth edits or failed-case removal.',
        '\n## Executive conclusion',
        '\nLabel reliability improved, but **do not call the bilingual hackathon demo ready without qualification**. The frozen implementation regressed summary-language consistency: many English inputs receive Greek summaries. One held-out immediate electric-shock return is still high rather than urgent. Keep operator review; no autonomous handling or production-grade reliability is claimed.',
        '\nA restricted supervised demonstration can show the grounded reply and workflow improvements, with these defects disclosed. A bilingual quality claim needs a later implementation fix and a fresh unseen evaluation; this run must not be reused as a new holdout after tuning.',
        table(['Metric','5A baseline (same original 60)','5B development (original 60)','5B held-out (new 40)'],
              [[name,fmt(b[key]),fmt(d[key]),fmt(h[key])] for name,key in [('Category','category'),('Priority','priority'),('Order ID','order_id'),('Complete label tuple','complete'),('Invalid pipeline output','invalid_output'),('Schema invalid','schema_invalid'),('Unusable attempts','failed_inference'),('Explicit gender guard','gender_guard_failures'),('Additional narrative guard','narrative_guard_failures'),('Summary-language agreement proxy','summary_language_agreement_proxy'),('Tuple + language proxy','tuple_and_summary_language_proxy')]]),
        '\n“Complete” retains 5A’s exact category/priority/order-ID tuple definition, requiring pipeline acceptance. It is **not** complete semantic/linguistic correctness. The additional language rows expose that distinction; failed outputs remain failures even when the expected ID is null. A script-dominance proxy flags language disagreement; it is not native-speaker scoring.',
        '\n## Exact changes and evidence',
        '\nSee [root-causes.md](root-causes.md) for the pre-evaluation decisions. `classifier.py` adds explicit severity precedence, payment/technical/main-remedy boundaries, tentative-reference handling, positive impersonal Greek forms and summary-language instruction. Existing gender/verbosity/repetition/schema/evidence checks stay active; customer-role narrative is additionally rejected in reasons. No priority/category/ID label is overwritten by a regex or a case-specific answer.',
        '\n`customer_data.py` masks explicit role/output-control spans only for classification candidates and language/topic helpers, retaining the original message. It adds no trusted interpretation of arbitrary customer prose. Raw `order_candidates` remains available to approval guards and gains standard order-reference labels. Masking can miss sophisticated injections or omit legitimate text; schema/runtime evidence checks and human review still apply. No automatic single-candidate fill was added.',
        '\n`reply_generator.py` keeps constrained plans and verified rendering. Conditional card/account guidance and general/site/payment next steps avoid irrelevant order-ID prerequisites. Known eligibility is required, exact duplicate facts are removed, known ineligibility excludes a generic 30-day option, and fixed prompts ask only for missing details. A redundant no-action follow-up is omitted. New drafts use policy version v3; old drafts and snapshots are untouched. No approval/workflow/immutability protections changed.',
        '\nRoot-cause distinctions: 5A’s gendered text was a model instruction failure caught by a valid guard; repetitive replies were renderer behavior; uncertain reference EN23 and mixed issue EL23 have contestable gold labels. Negative-example priming was an engineering hypothesis, not an experimentally proven cause. In 5B, language cross-contamination after stronger Greek examples is an observed regression; its exact causal attribution has not been established by an ablation study.',
        '\n## Independence, freezing and dataset coverage',
        '\n[freeze-v1.json](freeze-v1.json) hashes all backend application sources, inference/scoring harness dependencies, the old evidence, and new expectations/rubric before the first request. The held-out 40 ran first, then the original 60, then new replies. Hashes were rechecked after execution and again during reporting. The model digest is unchanged from 5A: ' + str(env['model_release'][0]['digest'] == old_env['model_release'][0]['digest']) + '.',
        '\nNew cases cover address/locker handling, invoice/VAT and FX fees, historical security negation, electrical hazards in return requests, conflicting receipts, privacy/employment/wholesale information and nonblocking website issues. Messages are not copied/translated surface variants of the original 60, although category themes necessarily overlap. The same implementer authored the holdout and knows the rules: this is operationally unseen, **not externally blinded independent scientific validation**. No Qwen output supplied expected labels.',
        table(['Dimension','New held-out distribution'], [[key,dict(Counter(case[key] for case in data['held_out']))] for key in ['language','category','priority','cohort','human_review']]),
        '\nStrict gold labels remain fixed even when a different interpretation is plausible. HEL08 expects null among competing references; HEL16 retains a tentative explicit reference for manual reconciliation. HEN10 labels a historical, resolved security mention as low because the current request is payment-method information.',
        '\n## Per-class precision/recall and confusion matrices',
    ]
    for kind in ['held_out','development']:
        values = metrics[kind]
        pieces += ['\n### ' + kind.replace('_',' ').title(), table(['Subset','Category','Priority','ID','Complete'], [[name,fmt(value['category']),fmt(value['priority']),fmt(value['order_id']),fmt(value['complete'])] for name,value in {**values['by_language'],**values['by_cohort']}.items()])]
        for field in ['category','priority']:
            matrix=values[field+'_confusion']; columns=list(next(iter(matrix.values())))
            pieces += ['\n' + field.title(),table(['Expected / predicted']+columns,[[label]+list(counts.values()) for label,counts in matrix.items()]),
                       table(['Class','Precision TP/predicted','Recall TP/actual'],[[label,fmt(value['precision']),fmt(value['recall'])] for label,value in values[field+'_per_class'].items()])]
    failures = [row for row in groups['held_out']+groups['development'] if not row['accepted'] or any(row['predicted'][key]!=row['expected'][key] for key in ['category','priority','order_id'])]
    pieces += ['\n## Remaining failures and regressions',
        table(['Set / case','Expected category / priority / ID','Observed tuple or rejection'],[[row['kind']+' / '+row['case_id'],' / '.join(str(row['expected'][key]) for key in ['category','priority','order_id']),' / '.join(str(row['predicted'][key]) for key in ['category','priority','order_id']) if row['accepted'] else str(row['error'].get('cause',row['error']['code']))] for row in failures]),
        '\nHEN06 reports electric shocks but is high rather than urgent: a genuine safety-related classification miss, not a fixture ambiguity. EN23 retains null despite a tentative offered reference; its old gold remains debatable under the original uncertainty policy. EL23 still selects delivery for a competing technical/receipt problem. EL07 is rejected by the strengthened narrative guard and EL09 by the unchanged gender guard. Total Greek summary-neutrality/narrative rejections fell from 10/60 to 2/60; the explicit original gender error alone is 1/60. Neither rejected output was accepted or rewritten.',
        '\n### Summary-language regression (not hidden by label accuracy)',
        table(['Set','Accepted language-mismatch case IDs'],[['Held-out',', '.join(h['language_mismatch_ids'])],['Development',', '.join(d['language_mismatch_ids'])]]),
        '\n11/40 held-out and 18/60 development inputs have at least one accepted summary field dominated by the wrong script (all flagged inputs are English). The prompt requests the proper language, but no runtime language guard currently rejects these fields. This is an unresolved quality regression, not a relaxed gender guard. No post-holdout edits were made to improve its score. Review the actual text in [classification-results-v1.csv](classification-results-v1.csv) and [results-v1.jsonl](results-v1.jsonl); the CSV labels the script proxy explicitly.',
        '\n## New reply-quality evaluation',
        '\nAll 12 real plans were accepted; **11/12 passed every frozen check**. All 12 passed the common date/reference/positive-action checks. The N06 failure is a fixture mistake: GR-1046 has no ETA, but the prewritten requirement demanded an estimate caveat. The actual reply correctly says the date is unavailable and excludes the injected 2098 date. The expectation and 11/12 score remain unchanged rather than being corrected after seeing the result.',
        '\nThis does not establish full safety or naturalness. The fixed [reply-rubric.md](reply-rubric.md) separates finite assertions from human grounding, safety, relevance, helpfulness, language and clarity/naturalness ratings. All six semantic dimensions remain pending product-owner review for every scenario; assistant observations are not blinded human ratings.',
        table(['Case','Scenario','Failed frozen checks','Qualitative observation'],[[row['case_id'],case['scenario'],', '.join(key for key,value in row.get('checks',{}).items() if not value) or 'None',observations[row['case_id']]] for row,case in zip(groups['reply'],data['reply'],strict=True)]),
        '\nActual replies are in [reply-review-v1.json](reply-review-v1.json). English/Greek fraud and account cases avoid purchase-ID demands; known warranty uncertainty occurs once; an ineligible return no longer carries the generic 30-day policy. N09 still offers limited help to a clear general-policy question, N10 remains verbose, and N03 exposes an implicit-possession conflict not recognized by explicit consistency rules. These concerns need human judgment and further work. New scenarios differ from the old 12, so timing/length comparisons are descriptive, not paired quality improvements.',
        '\n## Latency distributions and impact',
        table(['Population','N / failed','p50 s','p95 s','Mean s','Min s','Max s','Input/output tokens'],[[name,f"{value['attempts']} / {value['failed']}",value['p50_seconds'],value['p95_seconds'],value['mean_seconds'],value['min_seconds'],value['max_seconds'],f"{value['input_tokens']} / {value['output_tokens']}"] for name,value in performance.items()]),
        f"\nFirst held-out request: {groups['held_out'][0]['latency_seconds']} s, with Ollama load_duration {groups['held_out'][0]['raw'].get('load_duration',0)/1e9:.6f} s. Steady held-out excludes that first request; development and replies ran on the resident model. Original steady classification p50 {performance['5A classification steady']['p50_seconds']} s versus new development {performance['5B development warm']['p50_seconds']} s. These are one serial run per set, not a latency SLA or controlled cross-day hardware experiment.",
        '\nTemperature 0, seed 42, thinking/streaming false, context 8192, num_predict 512/256 and 120-second whole-call bounds remain unchanged. Wall timings include existing pipeline validation, local context checks and benchmark assertions, not browser/API/persistence round trips. Raw Ollama token and load/eval nanosecond fields are retained. p95 is linearly interpolated. No parallel inference, forced unload, new model, package or Windows setting was used. No new hardware/host identifiers were captured.',
        '\n## Regression tests, data integrity and limits',
        '\n**198 relevant backend tests passed**, including original safety/workflow tests, 20 targeted AI-quality cases, three runner-isolation/freeze tests and four original scoring tests. **48 relevant frontend tests passed**, covering order/reply, approval, workflow and API contracts, plus TypeScript checks. One old assertion was updated for intentionally changed “missing details” wording; refund eligibility/approval assertions remain intact. No UI files were changed.',
        '\nThe only database writes were migration/seeding inside verified `.cache/milestone5b/evaluation-v1.db`. Classification and reply cases use transient objects, with no saved tickets, drafts, approvals or sends. All original database table fingerprints match the pre-work baseline; all original 5A files are unchanged; post-seed QA tables are unchanged. Freeze verification passes after evaluation. Existing backend approval guards, immutable approved rows, order verification and human-review flags are unchanged.',
        '\nLimits: small category-balanced synthetic datasets; same-author holdout; contested labels; finite injection masking and consistency vocabularies; script heuristics instead of native-language judgments; one benchmark fixture error; no fully blinded reply ratings; no browser/load/concurrency test; no proof against adaptive injection or arbitrary manually edited prose. Correct schema/labels do not establish correct-language or helpful summaries. Remaining language and urgency defects block an unqualified bilingual readiness claim.',
        '\n## Next decisions (not implemented after freeze)',
        '\n1. Address English/Greek summary-language contamination and add a language regression guard with a fresh unseen validation set.\n2. Investigate urgent safety precedence across return remedies, retaining the HEN06 failure.\n3. Reduce the remaining Greek narrative generation without relaxing fail-closed checks.\n4. Obtain bilingual product-owner reply ratings; refine general-question relevance, implicit delivery contradictions and residual verbosity.\n5. Adjudicate ambiguous references/category labels and correct the N06 rubric in a future version, preserving these original results.',
        '\n## Reproduction and commit safety',
        '\nRun `backend\\.venv\\Scripts\\python.exe backend/benchmarks/milestone5b.py freeze` only before a first experiment. `... milestone5b.py execute` refuses existing results/QA DB and verifies source/label hashes. Do not overwrite or rerun for better scores. `backend\\.venv\\Scripts\\python.exe backend/benchmarks/report5b.py` regenerates this documentation with **zero inference**.',
        '\nSee [commit-readiness.md](commit-readiness.md) for exact A/B/C paths and reasons. No Git add, commit or push was executed. No user files were deleted. Milestone 5B ends with the frozen measured implementation and the unresolved defects disclosed; no follow-on milestone was started.',
    ]
    (DOCS/'report.md').write_text('\n\n'.join(pieces)+'\n',encoding='utf-8')
    print(json.dumps({'held_out':{key:h[key] for key in ['category','priority','order_id','complete','summary_language_agreement_proxy']},'development':{key:d[key] for key in ['category','priority','order_id','complete']},'replies':metrics['replies']},indent=2))


if __name__ == '__main__':
    main()
