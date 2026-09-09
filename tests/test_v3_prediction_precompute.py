import ast

import numpy as np
import pandas as pd
import pytest

from scripts import precompute_research_protocol_v3 as job
from scripts import replay_research_protocol_v3_predictions as replay


def test_sequence_numerical_loop_matches_authority():
    """The generalized path must preserve the qualified numerical operations."""
    old = ast.parse((job.ROOT / 'scripts/run_research_protocol_v3_mvp.py').read_text())
    new = ast.parse((job.ROOT / 'model_research/v3_prediction_precompute.py').read_text())
    original = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == 'wide_canary')
    generalized = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == 'precompute_fold')
    start = next(i for i, n in enumerate(original.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'days' for t in n.targets))
    expected = original.body[start:]
    assert [ast.dump(n) for n in generalized.body[:len(expected)]] == [ast.dump(n) for n in expected]


def test_independent_calendar_and_future_rejection():
    p = job.v3.build_protocol(pd.bdate_range(job.v3.START, '2026-06-09'))
    p['intervals'] = p['intervals'].loc[p['intervals'].feature_time <= job.v3.END]
    job.validate_protocol(p)
    p['assignments'].loc[0, 'datetime'] = pd.Timestamp('2024-01-02')
    with pytest.raises(ValueError, match='outside development'):
        job.validate_protocol(p)


def test_strict_requires_broad_replay(tmp_path):
    with pytest.raises(ValueError, match='Broad494 independent replay'):
        job.run_pool(tmp_path, 'Strict332', (None, None, None, None, None), 'hash')


def test_replay_is_label_free_and_detects_corruption(tmp_path, monkeypatch):
    import hashlib
    days = pd.date_range('2023-01-03', periods=2)
    frame = pd.DataFrame({'datetime': days.repeat(2), 'instrument': ['A', 'B'] * 2,
                          'factor': [1., np.nan, 2., 3.]})
    stored = frame[job.v3.KEYS].assign(score=frame.factor * 2,
        reason=['predicted', 'all_features_missing', 'predicted', 'predicted'])
    stored.to_parquet(tmp_path / 'engineering_predictions.parquet', index=False)
    config = dict(num_boost_round=100)
    resource = dict(model_sha256=hashlib.sha256(b'model').hexdigest(), ordered_features=['factor'],
        config_hash=job.v3.canonical_hash(config), fold_id='annual_2023', outer_labels_accessed=False,
        storage='monthly_float64_sequence', prediction_rows=4, predicted_dates=2, prediction_coverage=.75)
    job.v3.atomic_write_json(tmp_path / 'resource.json', resource)
    job.v3.atomic_write_json(tmp_path / 'access.json', {'access': []})
    class Model:
        def model_to_string(self): return 'model'
        def current_iteration(self): return 100
        def feature_name(self): return ['factor']
        def predict(self, x, **kwargs): return x[:, 0] * 2
    monkeypatch.setattr(replay.lgb, 'Booster', lambda **kwargs: Model())
    monkeypatch.setattr(job.v3, 'read_features', lambda *a, **k: frame)
    monkeypatch.setattr(replay, 'read_keys', lambda *a, **k: frame[job.v3.KEYS])
    def forbidden(*a, **k): pytest.fail('labels or runner predict accessed by independent replay')
    monkeypatch.setattr(job.v3, 'read_labels', forbidden)
    monkeypatch.setattr(job.v3, 'cached_training_labels', forbidden)
    monkeypatch.setattr(job.v3, 'predict', forbidden)
    p = {'assignments': pd.DataFrame({'fold_id': ['annual_2023'] * 2, 'role': ['predict'] * 2, 'datetime': days})}
    result, _ = replay.replay_fold(tmp_path, 'annual_2023', ['factor'], None, p, config)
    assert result['exact']
    stored.loc[0, 'score'] = 999
    stored.to_parquet(tmp_path / 'engineering_predictions.parquet', index=False)
    with pytest.raises(AssertionError):
        replay.replay_fold(tmp_path, 'annual_2023', ['factor'], None, p, config)


def test_bounded_integrity_never_opens_recent_values(tmp_path, monkeypatch):
    from factor_research.long_history_screening import frame_hash
    import research_validation.canonical_dataset as canonical
    frame = pd.DataFrame({'datetime': [pd.Timestamp('2023-01-03')], 'instrument': ['A'], 'f': [1.]})
    event = dict(kind='feature', role='predict', start='2023-01-03', end='2023-01-03',
        path='mixed.parquet', columns=['f'], parent_sha256='parent', rows=1, slice_hash=frame_hash(frame))
    for folder in [*[tmp_path / 'audit' / str(y) for y in range(2010, 2023)], tmp_path / 'wide_canary/annual_2023']:
        folder.mkdir(parents=True)
        job.v3.atomic_write_json(folder / 'access.json', {'access': [event]})
        job.v3.atomic_write_json(folder / 'receipt.json', dict(contract_hash=job.SOURCE_HASH, status='complete',
            file_hashes={'access.json': job.v3.sha256_file(folder / 'access.json')}))
    partitions = pd.DataFrame([dict(partition_path='mixed.parquet', output_sha256='parent',
                                   effective_start='2021-01-01', effective_end='2026-06-09')])
    def bounded(row, columns):
        assert row['effective_end'] <= job.v3.END
        assert columns == ['f']
        return frame
    monkeypatch.setattr(canonical, 'read_effective_partition', bounded)
    context = (tmp_path, {}, partitions, {'intervals': pd.DataFrame({'feature_time': frame.datetime})}, {'Broad494': ['f']})
    job.verify_feature_slices(context)
    frame.loc[0, 'f'] = 2
    with pytest.raises(ValueError, match='slice changed'):
        job.verify_feature_slices(context)
