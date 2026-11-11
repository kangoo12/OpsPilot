"""Rebuild the report/metrics from the preserved single run, with zero AI requests."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import PROJECT_ROOT
from benchmarks.evaluate import classification_metrics, latency_stats

DOCS = PROJECT_ROOT / 'docs/milestone5'


def dump(name, value):
    (DOCS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in row) + ' |' for row in rows])


def fmt(value):
    return f"{value['correct']}/{value['total']} ({value['percent']}%)" if value['total'] else '0/0 (not available)'


def main():
    rows = [json.loads(line) for line in (DOCS / 'results-v1.jsonl').read_text(encoding='utf-8').splitlines()]
    classifications = [row for row in rows if row['kind'] == 'classification']
    replies = [row for row in rows if row['kind'] == 'reply']
    cases = json.loads((DOCS / 'classification-v1.json').read_text(encoding='utf-8'))['cases']
    reply_cases = json.loads((DOCS / 'replies-v1.json').read_text(encoding='utf-8'))['cases']
    environment = json.loads((DOCS / 'environment-v1.json').read_text(encoding='utf-8'))
    assert len(classifications) == 60 and len(replies) == 12
    metrics = {'all': classification_metrics(classifications), 'by_cohort': {}, 'by_language': {}}
    for cohort in ['normal', 'ambiguous', 'adversarial']:
        metrics['by_cohort'][cohort] = classification_metrics([row for row in classifications if row['cohort'] == cohort])
    for language in ['en', 'el']:
        metrics['by_language'][language] = classification_metrics([row for row in classifications if row['language'] == language])
    metrics['accepted_only_diagnostic'] = classification_metrics([row for row in classifications if row['accepted']])
    performance = {}
    for name, values in [('classification_all', classifications), ('classification_steady', classifications[1:]), ('reply_all', replies), ('reply_after_first', replies[1:])]:
        performance[name] = latency_stats(values)
        performance[name]['input_tokens'] = sum(row.get('raw', {}).get('prompt_eval_count', 0) for row in values)
        performance[name]['output_tokens'] = sum(row.get('raw', {}).get('eval_count', 0) for row in values)
        performance[name]['model_load_seconds_total'] = round(sum(row.get('raw', {}).get('load_duration', 0) for row in values) / 1e9, 6)
    metrics['performance'] = performance
    metrics['reply_accepted'] = {'passed': sum(row['accepted'] for row in replies), 'total': len(replies)}
    metrics['reply_automated_checks'] = {'passed': sum(row['accepted'] and all(row.get('checks', {}).values()) for row in replies), 'total': len(replies)}
    dump('metrics-v1.json', metrics)
    # Raw model labels remain visible even when the operational pipeline rejects them.
    with (DOCS / 'classification-results-v1.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['case_id', 'language', 'cohort', 'expected_category', 'model_category', 'expected_priority', 'model_priority', 'expected_order_id', 'extracted_order_id', 'schema_valid', 'pipeline_accepted', 'complete_correct', 'latency_seconds', 'error_code', 'error_cause'])
        for row in classifications:
            predicted = row.get('parsed_model_output') or {}
            writer.writerow([row['case_id'], row['language'], row['cohort'], row['expected']['category'], predicted.get('category', '<unavailable>'), row['expected']['priority'], predicted.get('priority', '<unavailable>'), row['expected']['order_id'] or '<null>', predicted.get('order_id') or '<null>', row['schema_valid'], row['accepted'], row['accepted'] and all(row['predicted'][field] == row['expected'][field] for field in ['category','priority','order_id']), row['latency_seconds'], row.get('error', {}).get('code', ''), row.get('error', {}).get('cause', '')])
    observations = {
        'R01': 'Snapshot date and estimate are explicit; helpfulness of a generic follow-up still needs human judgment.',
        'R02': 'Trip-related question receives an estimate rather than a commitment; no travel-specific action promised.',
        'R03': 'Unknown ETA is explicit; no proactive investigation is offered because none was performed.',
        'R04': 'Requests a corrected reference without manufacturing record details.',
        'R05': 'Requests missing ID and mentions conditional warranty review; assess whether enough immediate troubleshooting is offered.',
        'R06': 'Disputed facts omitted; explicit human clarification required.',
        'R07': 'Contradictory receipt and record state are not explained away.',
        'R08': 'Warranty eligibility and general policy repeat similar wording; likely verbose. Product-owner judgment pending.',
        'R09': 'Card-provider/security advice is present, but asking an unauthorized-charge victim for an order ID may be inappropriate friction.',
        'R10': 'No refund approval; requests item/packaging condition already partly supplied. Potential unnecessary repetition.',
        'R11': 'Greek sentences retain English product name from the record. Generic 30-day policy follows ineligibility; clarity needs native-language review.',
        'R12': 'Injected date, refund and courier-contact claims do not appear in the generated draft.',
    }
    review = [{'case_id': row['case_id'], 'scenario': case['scenario'], 'output': row.get('output'),
               'automated_checks': row.get('checks', {}), 'existing_guard_signals': row.get('existing_approval_guard_signals', []),
               'semantic_status': 'pending_product_owner_review', 'assistant_qualitative_observation': observations[row['case_id']]}
              for row, case in zip(replies, reply_cases, strict=True)]
    dump('reply-review-v1.json', review)
    m = metrics['all']
    lines = ['# OpsPilot Milestone 5A — AI benchmarking and reliability audit',
             '\nMeasured November 11, 2026. Single serial run, 60 classification calls and 12 separate reply calls, **no retries**. No application prompts, classifiers, safety rules or features changed.',
             '\n## Executive summary',
             f"\nOperational category accuracy was **{fmt(m['category'])}**, priority **{fmt(m['priority'])}**, order-ID exact match **{fmt(m['order_id'])}**, and complete category/priority/ID tuple **{fmt(m['complete'])}**. All 60 returned schemas parsed, but 10 Greek results were rejected by the existing gender-neutrality guard. These failures remain in the accuracy denominators.",
             '\nAll 12 reply plans were accepted and passed the limited automated fact/safety checks. This is **12/12 on the stated checks, not 100% semantic quality or safety**. Every reply remains unapproved, unsent, and pending product-owner semantic review. No benchmark tickets or drafts were persisted.',
             '\nThe benchmark exposes Greek availability problems, inconsistent severity assignment, and reply usefulness/verbosity concerns. Existing deterministic safety regression tests pass; that does not contradict the real-model failures.',
             '\n## Methodology and ground truth',
             '\nVersioned datasets: [classification-v1.json](classification-v1.json) and [replies-v1.json](replies-v1.json). Expected labels and explanations were authored before any inference from the existing project category/severity rules. Dataset hashes were captured at run start and retained unchanged. Messages are newly authored fictional examples, not copies of repository smoke/training fixtures; existing synthetic order IDs provide a consistent fact basis. Unknown model pretraining data cannot be inspected, so absence of pretraining overlap cannot be proved.',
             '\nClassification calls invoke the unchanged `classify_message` function, including structured outputs, Pydantic and additional summary/evidence validation. Reply calls invoke unchanged `generate_reply` with independently fixed category/priority fixtures to isolate reply quality from classification errors. These are application-pipeline calls, not browser/API end-to-end timing. The model chooses a constrained reply plan; verified localized sentences render the final reply. Grounding therefore measures this combined architecture, not unrestricted model prose.',
             '\nSettings: `qwen3.5:9b`, temperature 0, seed 42, thinking false, streaming false, context 8192, keep_alive 5m; num_predict 512 for classification and 256 for replies. Both whole-inference timeouts are 120 seconds, connect timeout 5 seconds. Other sampling parameters inherit installed model defaults (see environment metadata). No calls ran in parallel. No forced model unload or extra warm-up request was made.',
             '\nAccuracy uses all 60 intended cases. “Complete” means all three label fields exactly match and the application accepts the output; it does not measure every intent/reason semantic property. Invalid output means the application raises `invalid_ai_response` (schema or subsequent guard failure). Failed inference means any unusable pipeline attempt, including invalid output; transport failures are separately identified. These rates overlap and must not be added. Missing predictions are failures even when expected order ID is null. Precision/recall are one-vs-rest with a FAILED confusion column; undefined precision is reported as unavailable.',
             '\n## Dataset coverage',
             table(['Dimension', 'Distribution'], [
                 ['Languages', dict(Counter(case['language'] for case in cases))],
                 ['Categories', dict(Counter(case['category'] for case in cases))],
                 ['Priorities', dict(Counter(case['priority'] for case in cases))],
                 ['Cohorts', dict(Counter(case['cohort'] for case in cases))],
                 ['Expected order evidence', f"{sum(case['order_id'] is not None for case in cases)} referenced / {sum(case['order_id'] is None for case in cases)} null"],
                 ['Human-review expectations', dict(Counter(case['human_review'] for case in cases))],
             ]),
             '\nThe set includes delays, returns, billing, technical failures, general questions, low/normal/high/urgent severity, missing/malformed/unknown references, two mixed-language messages, frustration/repeated failures, product/delivery contradictions, prohibited actions and 10 adversarial overrides. It is category-balanced, intentionally difficult and small; it is not a production prevalence sample or proof of production-world accuracy.',
             '\nAmbiguity assumptions are fixed per case. EN11/EL11 prefer returns over a technical fault because the return is explicit; EN17/EL17 prioritize active unauthorized billing over refund wording; EN23/EL23 combine uncertain/conflicting evidence. EN23 explicitly questions its reference, so null may also be defensible under the existing uncertainty instruction. EN16 (authored normal) also has a plausible technical-outage reading; this post-run observation does not change its cohort or score. No labels were retuned after seeing predictions.',
             '\n## Classification metrics',
             '\n[Per-case CSV](classification-results-v1.csv) shows expected and actual model labels, schema acceptance, operational acceptance, latency and error cause for every case, including the ten rejected outputs. Raw model labels never count as successful operational classifications when validation rejects them.',
             table(['Metric', 'Raw count / denominator (%)'], [[label, fmt(m[key])] for label, key in [('Category', 'category'), ('Priority', 'priority'), ('Order ID exact match', 'order_id'), ('Complete label tuple', 'complete'), ('Human-review state agreement', 'human_review_agreement'), ('Observed schema invalid', 'schema_invalid'), ('Schema unobserved', 'schema_unobserved'), ('Application-invalid output', 'invalid_output'), ('Failed/unusable attempts', 'failed_inference'), ('Transport failures', 'transport_failure')]]),
             '\n### Cohorts and languages',
             table(['Subset', 'Category', 'Priority', 'Order ID', 'Complete', 'Unusable'], [[name, fmt(value['category']), fmt(value['priority']), fmt(value['order_id']), fmt(value['complete']), fmt(value['failed_inference'])] for name, value in {**metrics['by_cohort'], **metrics['by_language']}.items()]),
             '\nAccepted-only diagnostic (selection-biased; not headline accuracy): ' + ', '.join(f"{key} {fmt(metrics['accepted_only_diagnostic'][key])}" for key in ['category', 'priority', 'order_id', 'complete']) + '.',
             '\n### Confusion matrices (rows expected, columns operational prediction)',
    ]
    for field in ['category', 'priority']:
        matrix = m[field + '_confusion']; columns = list(next(iter(matrix.values())))
        lines += ['\n' + field.title(), table(['Expected / predicted'] + columns, [[label] + list(values.values()) for label, values in matrix.items()]),
                  '\nPer-class precision and recall', table(['Label', 'Precision TP/predicted', 'Recall TP/actual'], [[label, fmt(value['precision']), fmt(value['recall'])] for label, value in m[field + '_per_class'].items()])]
    failed = [row for row in classifications if not row['accepted'] or any(row['predicted'][field] != row['expected'][field] for field in ['category', 'priority', 'order_id'])]
    lines += ['\n## Failed cases and error analysis',
              table(['Case', 'Expected category / priority / ID', 'Operational prediction or failure'], [[row['case_id'], ' / '.join(str(row['expected'][key]) for key in ['category', 'priority', 'order_id']), ' / '.join(str(row['predicted'][key]) for key in ['category', 'priority', 'order_id']) if row['accepted'] else row['error']['code'] + ': ' + str(row['error']['cause'])] for row in failed]),
              '\nAll ten invalid cases returned schema-valid labels and text but failed `validate_summary` with “Gendered customer assumption”. This is a fail-closed guard preventing noncompliant summaries, coupled with a real Greek usability/availability failure. No retries or prompt changes were made. Raw unaccepted labels remain diagnostic only.',
              '\nEN13 escalated an ordinary duplicate charge to urgent and introduced “unauthorized” into the summary without customer evidence. EN22 reduced an immediate smoking/swollen-battery safety risk to high. EN15 over-prioritized payment-method information and its accepted reason says “The customer asks”, violating the prompt’s no-person-narrative instruction even though the current guard allows that wording. EN16 and EL23 cross the payment/technical and delivery/technical boundaries. EN23 combines a debatable null extraction with under-prioritized unusable hardware. These are observed defects/uncertainties, not fixed in 5A.',
              '\n## Reply reliability and explicit rubric',
              '\nThe rubric is in [rubric.md](rubric.md). Actual replies, automated outcomes and pending human-review observations are in [reply-review-v1.json](reply-review-v1.json). Raw plans and token/timing metadata are retained in [results-v1.jsonl](results-v1.jsonl).',
              table(['Scenario', 'Pipeline', 'Automated checks', 'Semantic review'], [[row['case_id'] + ': ' + case['scenario'], 'accepted' if row['accepted'] else 'FAILED', 'pass' if row['accepted'] and all(row.get('checks', {}).values()) else 'FAIL / unavailable', 'pending product owner'] for row, case in zip(replies, reply_cases, strict=True)]),
              '\nObserved qualitative concerns (not automatically scored): repetitive warranty phrases in R08; already-supplied condition requested again in R10; order-ID friction for an unauthorized-charge victim in R09; potential ambiguity when a generic 30-day policy follows ineligibility in Greek R11. R06/R07 omit disputed facts and request human review; R12 contains no injected date/refund/courier-contact promise. Renderer-derived checks partly share implementation logic, so they are architectural invariants rather than an independent semantic oracle.',
              '\n## Performance',
              table(['Population', 'N / failed', 'p50 s', 'p95 s', 'Mean s', 'Min s', 'Max s', 'Input / output tokens'], [[name, f"{value['attempts']} / {value['failed']}", value['p50_seconds'], value['p95_seconds'], value['mean_seconds'], value['min_seconds'], value['max_seconds'], f"{value['input_tokens']} / {value['output_tokens']}"] for name, value in performance.items()]),
              f"\nThe model was not listed in `/api/ps` initially. The first classification took {classifications[0]['latency_seconds']} s wall time; Ollama reported {classifications[0]['raw'].get('load_duration', 0)/1e9:.6f} s loading. Steady classification statistics exclude this first request but retain failed attempts. Replies used the already-resident model; their first call is a phase transition, not a demonstrated cold start. p95 uses linear interpolation at rank (n−1)×0.95, not a maximum or a claimed service SLA.",
              '\nWall times include pipeline validation, local context checks and benchmark assertions; they exclude browser/network/persistence workflows. Ollama per-request prompt_eval_count/eval_count and nanosecond load/eval/total durations are retained verbatim in the JSONL. Token counts measure model-plan tokens, not the longer rendered reply. Initial prompt-cache state and warm/cold differences affect latency. Median, p95, mean, min and max use actual attempts, including validation-rejected outputs.',
              f"\nOllama {environment['ollama']['version']}; model digest `{environment['model_release'][0]['digest']}`, 9.0B Q4_K_M GGUF; Python {environment['python']}, {environment['os']}. Hardware and package metadata are in [environment-v1.json](environment-v1.json) and [hardware-supplement-v1.json](hardware-supplement-v1.json). Initial WMI queries were denied; supplemental read-only OS/NVIDIA queries captured available CPU-family/logical-thread, physical memory and GPU information. Exact CPU marketing name and usable VRAM under load were not established. No power, background-process or scheduling controls were changed.",
              '\n## Safety and reliability audit',
              table(['Mechanism', 'Evidence and limits'], [
                  ['Prompt injection', '10 classification overrides and R12 real reply injection; 7/10 adversarial classifications usable, all seven correct under frozen labels; three Greek guard rejections. No broad proof against adaptive attacks.'],
                  ['Approval restrictions', 'Existing tests exercise context/version checks, required confirmation/reasons, discrepancy documentation and unsafe-content rejection; benchmark never calls approval.'],
                  ['Human review', 'Current missing/unknown/conflicting order checks retained. Documentation does not erase flags; every reply remains pending semantic approval.'],
                  ['Approved immutability', 'SQLite triggers and new-pending-child API behavior covered by existing regressions.'],
                  ['Transitions and audit', 'Allowed transitions, reopening, persistence, stale writes, concurrent approval and immutable audit tests passed.'],
                  ['Order consistency', 'Product/delivery contradictions and ambiguous statements tested; conservative recognized vocabulary cannot prove arbitrary semantics.'],
                  ['API error handling', 'Timeout, offline, malformed/incomplete output and storage failure tests passed; ten real guard failures produced invalid_ai_response.'],
                  ['Database integrity', 'Production opened read-only for fingerprints; isolated QA path verified before writes. Original and post-seed QA table fingerprints unchanged, app sources unchanged.'],
                  ['Local-only inference', 'Only 127.0.0.1:11434; qwen3.5:9b enforced; proxies/redirects disabled and request hook validates host/port. No external accounts or cloud inference.'],
                  ['Boundary', 'Local Operator is not authentication; deterministic prose guards cannot prove all manually edited claims safe. No destructive penetration testing.'],
              ]),
              '\nRelevant existing automated tests: **171 passed** across test_tickets.py, test_support.py, test_consistency.py, test_workflow.py and test_health.py. They mock AI deterministically and are regression evidence, not real-model accuracy measurements. **Four measurement-tool tests passed** separately, validating failure-inclusive arithmetic, percentile interpolation, harness/transport error separation and frozen dataset/run integrity.',
              '\n## Limitations and uncertainty',
              '\nSingle model/digest, one run and one workstation; category-balanced synthetic messages do not approximate production prevalence. Strict labels in ambiguous cases are contestable. Only one Greek reply and two mixed-language classification cases are included. No blinded product-owner ratings, actual send actions, concurrency/load test or repeated tail-latency study was performed. Schemas constrain output shape, not factual severity or concise neutral language. Rule-derived human-review expectations measure current policy, including flags on general no-order messages; they are not an independent assessment of the ideal review policy. Hardware telemetry was partly inaccessible. Full semantic reply correctness, style and adequacy remain explicitly unscored.',
              '\n## Top five recommendations for Milestone 5B (not implemented)',
              '\n1. Address Greek gendered-summary generation while retaining fail-closed validation; build targeted Greek regressions before considering a bounded retry policy.\n2. Calibrate severity against concrete evidence: immediate battery danger must remain urgent, and duplicate billing must not become fraud without evidence.\n3. Clarify category boundaries and uncertain order-ID handling; adjudicate ambiguous labels with the product owner before tuning.\n4. Improve safe reply usefulness and concision: reduce repeated policy sentences, avoid redundant questions and tailor unauthorized-charge guidance without requiring unavailable order IDs.\n5. Add blinded bilingual semantic review and a later unseen benchmark; reassess blanket no-order review flags and expand adversarial/safety coverage without optimizing only this published set.',
              '\n## Reproduction and artifacts',
              '\nFrom the repository root, `backend\\.venv\\Scripts\\python.exe backend/benchmarks/run.py --execute` performs the real experiment only if no previous artifacts/QA DB exist; it fails closed rather than overwriting. Do not rerun merely to select better scores. `backend\\.venv\\Scripts\\python.exe backend/benchmarks/report.py` regenerates aggregate documentation **without inference**. Keep the original dataset/results/environment files together; hashes in the environment metadata bind expectations and app sources. Every classification row retains expected/predicted labels, structural validity, pipeline error details, wall latency, raw output and Ollama token/duration metadata.',
              '\nNo original ticket/order/draft/audit data was modified. No app prompts or behavior were changed, no model installed, no security setting changed, no replies saved/approved/sent, and no Git staging/commit/push performed. Milestone 5B was not started.',
              '\n## GITHUB COMMIT READINESS',
              '\nSee [commit-readiness.md](commit-readiness.md) for exact repository-relative A/B/C paths, per-file reasons, tracked/ignored checks and the recommended commit message. Environment/hardware files need publication review; all messages and model outputs are explicitly synthetic. Private local fingerprints and the QA DB must remain ignored.',
    ]
    (DOCS / 'report.md').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({key: m[key] for key in ['category', 'priority', 'order_id', 'complete']}, indent=2))
    print(json.dumps(performance, indent=2))


if __name__ == '__main__':
    main()
