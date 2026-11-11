"""Deterministic scoring. Failed/invalid cases remain in all denominators."""
import json
import math
from pathlib import Path
import statistics

from app.schemas import Category, Priority


def load_cases(path: Path, classification=False):
    dataset = json.loads(path.read_text(encoding='utf-8'))
    cases = dataset['cases']
    assert dataset['version'] == '1.0.0'
    assert len({case['id'] for case in cases}) == len(cases)
    for case in cases:
        Category(case['category']); Priority(case['priority'])
        assert case['language'] in {'en', 'el'}
        assert case['human_review'] in {'consistent', 'discrepancy', 'no_order_id', 'unknown_order'}
        assert case['message'].strip() and case['explanation'].strip()
    if classification:
        assert len(cases) == 60
        assert sum(case['language'] == 'en' for case in cases) == 30
        assert sum(case['cohort'] == 'adversarial' for case in cases) >= 10
        assert all(sum(case['category'] == category for case in cases) == 12 for category in Category)
    else:
        assert len(cases) == 12
    return dataset, cases


def rate(numerator, denominator):
    return {'correct': numerator, 'total': denominator, 'percent': round(100 * numerator / denominator, 2) if denominator else None}


def classification_metrics(rows):
    metrics = {}
    for field in ('category', 'priority', 'order_id'):
        metrics[field] = rate(sum(row['accepted'] and row['predicted'][field] == row['expected'][field] for row in rows), len(rows))
    metrics['complete'] = rate(sum(row['accepted'] and all(row['predicted'][field] == row['expected'][field] for field in ('category', 'priority', 'order_id')) for row in rows), len(rows))
    metrics['invalid_output'] = rate(sum(row.get('error', {}).get('code') == 'invalid_ai_response' for row in rows), len(rows))
    metrics['schema_invalid'] = rate(sum(row['schema_valid'] is False for row in rows), len(rows))
    metrics['schema_unobserved'] = rate(sum(row['schema_valid'] is None for row in rows), len(rows))
    metrics['failed_inference'] = rate(sum(not row['accepted'] for row in rows), len(rows))
    metrics['transport_failure'] = rate(sum(row.get('error', {}).get('code') in {'ai_unavailable', 'ai_timeout', 'ai_error', 'model_unavailable'} for row in rows), len(rows))
    metrics['harness_failure'] = rate(sum(row.get('error', {}).get('code') == 'benchmark_harness_error' for row in rows), len(rows))
    metrics['human_review_agreement'] = rate(sum(row['accepted'] and row.get('human_review') == row['expected']['human_review'] for row in rows), len(rows))
    for field, enum in [('category', Category), ('priority', Priority)]:
        labels = [str(item) for item in enum]
        matrix = {label: {pred: 0 for pred in labels + ['FAILED']} for label in labels}
        for row in rows:
            matrix[row['expected'][field]][row['predicted'][field] if row['accepted'] else 'FAILED'] += 1
        metrics[field + '_confusion'] = matrix
        metrics[field + '_per_class'] = {}
        for label in labels:
            tp = matrix[label][label]
            predicted = sum(matrix[actual][label] for actual in labels)
            actual = sum(matrix[label].values())
            metrics[field + '_per_class'][label] = {'precision': rate(tp, predicted), 'recall': rate(tp, actual)}
    return metrics


def latency_stats(rows):
    # Wall-clock timings include failed attempts. Percentiles use linear interpolation.
    values = sorted(row['latency_seconds'] for row in rows)
    if not values:
        return {'attempts': 0}
    rank = (len(values) - 1) * .95
    p95 = values[math.floor(rank)] + (values[math.ceil(rank)] - values[math.floor(rank)]) * (rank - math.floor(rank))
    return {'attempts': len(values), 'failed': sum(not row['accepted'] for row in rows),
            'p50_seconds': round(statistics.median(values), 4), 'p95_seconds': round(p95, 4),
            'mean_seconds': round(statistics.mean(values), 4), 'min_seconds': min(values), 'max_seconds': max(values)}
