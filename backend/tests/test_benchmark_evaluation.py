"""Validate measurement arithmetic and frozen dataset integrity, without inference."""
import json
from pathlib import Path

import pytest

from app.config import PROJECT_ROOT
from benchmarks.evaluate import classification_metrics, latency_stats, load_cases


def row(category='delivery', predicted='delivery', accepted=True, order_id=None):
    return {'accepted': accepted, 'expected': {'category': category, 'priority': 'medium', 'order_id': order_id, 'human_review': 'consistent'},
            'predicted': {'category': predicted, 'priority': 'medium', 'order_id': None} if accepted else None,
            'schema_valid': True if accepted else False, 'human_review': 'consistent', 'latency_seconds': 1,
            **({} if accepted else {'error': {'code': 'invalid_ai_response'}})}


def test_failures_are_not_dropped_or_scored_as_correct_null_orders():
    metrics = classification_metrics([row(), row(category='returns'), row(accepted=False)])
    assert metrics['category'] == {'correct': 1, 'total': 3, 'percent': 33.33}
    assert metrics['order_id']['correct'] == 2  # Failed null prediction is not a true match.
    assert metrics['invalid_output']['total'] == metrics['failed_inference']['total'] == 3
    assert metrics['category_confusion']['delivery']['FAILED'] == 1
    assert metrics['category_per_class']['delivery']['precision']['correct'] == 1
    assert metrics['category_per_class']['delivery']['precision']['total'] == 2
    assert metrics['category_per_class']['delivery']['recall']['total'] == 2


def test_percentiles_include_failed_attempts_and_use_linear_interpolation():
    rows = [dict(row(), latency_seconds=value) for value in [1, 2, 3, 4, 5]]
    rows[-1]['accepted'] = False
    stats = latency_stats(rows)
    assert stats['attempts'] == 5 and stats['failed'] == 1
    assert stats['p50_seconds'] == stats['mean_seconds'] == 3
    assert stats['p95_seconds'] == pytest.approx(4.8)
    assert latency_stats([]) == {'attempts': 0}


def test_harness_errors_are_not_mislabeled_as_transport_failures():
    failed = row(accepted=False)
    failed['error']['code'] = 'benchmark_harness_error'
    metrics = classification_metrics([failed])
    assert metrics['failed_inference']['correct'] == metrics['harness_failure']['correct'] == 1
    assert metrics['transport_failure']['correct'] == metrics['invalid_output']['correct'] == 0


def test_versioned_datasets_have_required_coverage_and_frozen_hashes():
    import hashlib
    folder = PROJECT_ROOT / 'docs/milestone5'
    manifest = json.loads((folder / 'environment-v1.json').read_text(encoding='utf-8'))
    for name, classification in [('classification-v1.json', True), ('replies-v1.json', False)]:
        _, cases = load_cases(folder / name, classification)
        assert len({case['message'] for case in cases}) == len(cases)
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == manifest['dataset_sha256'][name]
    rows = [json.loads(line) for line in (folder / 'results-v1.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 72 and len({row['case_id'] for row in rows}) == 72
    assert sum(row['kind'] == 'classification' for row in rows) == 60
    assert sum(row['kind'] == 'reply' for row in rows) == 12
