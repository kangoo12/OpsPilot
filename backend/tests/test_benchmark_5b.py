from pathlib import Path

import pytest

from app.config import PROJECT_ROOT
from benchmarks.milestone5b import LOCAL, datasets, verified_qa_path, verify_freeze, frozen_files


def test_new_dataset_coverage_and_no_development_duplicates():
    values = datasets()
    assert len(values['held_out']) == 40 and len(values['reply']) == 12
    assert len({case['message'] for case in values['held_out']}) == 40
    assert {case['category'] for case in values['held_out']} == {'delivery', 'returns', 'payments', 'technical_support', 'other'}
    assert {case['priority'] for case in values['held_out']} == {'low', 'medium', 'high', 'urgent'}


def test_isolation_checks_reject_production_and_paths_outside_qa():
    original = PROJECT_ROOT / 'data/opspilot.db'
    for path in (original, PROJECT_ROOT / 'data/another.db', PROJECT_ROOT.parent / 'elsewhere.db'):
        with pytest.raises(ValueError):
            verified_qa_path(path, original)
    assert verified_qa_path(LOCAL / 'unused-safety-test.db', original) == (LOCAL / 'unused-safety-test.db').resolve()


def test_freeze_detects_source_or_dataset_change_without_inference():
    hashes = frozen_files()
    verify_freeze({'sha256': hashes})
    name = next(iter(hashes))
    hashes[name] = '0' * 64
    with pytest.raises(RuntimeError, match='Freeze mismatch'):
        verify_freeze({'sha256': hashes})
