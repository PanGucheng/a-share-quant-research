import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from model_research import lightgbm_nested as policy
from scripts import research_lightgbm as job
from scripts.evaluate_lightgbm import paired_day, evaluate


@pytest.mark.parametrize('year', range(2015, 2024))
def test_nested_purge_independent_session_oracle(year):
    protocol = job.v3.build_protocol(pd.bdate_range(job.v3.START, '2026-06-09'))
    train, valid = policy.inner_split(protocol, f'annual_{year}')
    days = pd.DatetimeIndex(protocol['intervals'].feature_time)
    inner_boundary = days.get_loc(days[days.year == year-1][0])
    outer_boundary = days.get_loc(days[days.year == year][0])
    assert train.equals(days[:inner_boundary-21])
    assert valid.equals(days[inner_boundary:outer_boundary-21])
    assert valid.max().year < year


def test_inner_split_rejects_bad_maturity_and_future():
    p = job.v3.build_protocol(pd.bdate_range(job.v3.START, '2026-06-09'))
    p['intervals'].loc[p['intervals'].feature_time.dt.year == 2014, 'label_end_time'] = pd.Timestamp('2015-01-02')
    with pytest.raises(ValueError, match='maturity'):
        policy.inner_split(p, 'annual_2015')
    with pytest.raises(ValueError):
        job.v3.allowed_dates(p, 'annual_2023', 'train', [pd.Timestamp('2024-01-02')])


def test_metric_ties_days_and_constants_against_scalar_oracle():
    y = np.array([1, 1, 3, 2, 5, 4, 1, 2, 3.])
    x = np.array([3, 3, 1, 1, 2, 1, 7, 7, 7.])
    values, constants = policy.daily_ic(x, y, [3, 3, 3])
    np.testing.assert_allclose(values, [spearmanr(x[:3], y[:3]).statistic,
                                        spearmanr(x[3:6], y[3:6]).statistic, 0], atol=1e-15)
    assert constants == 1
    with pytest.raises(ValueError):
        policy.daily_ic([1, np.nan], [1, 2], [2])


def test_plateau_uses_predeclared_complexity_not_peak():
    rows = [dict(trial=t, mean_ic=.1, rounds=150, leaves=15) for t, _ in policy.TRIALS]
    rows[0].update(mean_ic=.0995, rounds=100)
    rows[4].update(mean_ic=.1, leaves=63)
    result = policy.select_trial(rows)
    assert result['selected'] == 'fixed100' and not result['outer_outcomes_used']
    with pytest.raises(ValueError, match='all predefined'):
        policy.select_trial(rows[:-1])


def test_paired_samples_and_constant_shared_day():
    y = np.arange(120, dtype=float)
    b, t = y.copy(), -y.copy()
    b[0] = t[0] = np.nan
    y[1] = np.nan
    result = paired_day(y, b, t)
    assert result['common_count'] == 118
    assert result['baseline'] == pytest.approx(1) and result['tuned'] == pytest.approx(-1)
    assert paired_day(np.arange(120), np.ones(120), np.arange(120))['reason'] == 'constant_label_or_arm'
    t[4] = np.nan
    with pytest.raises(ValueError, match='mask changed'):
        paired_day(y, b, t)


def test_outer_evaluation_gate_precedes_label_io(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail('outer labels accessed before replay')
    monkeypatch.setattr(pd, 'read_parquet', forbidden)
    with pytest.raises(ValueError, match='replay required'):
        evaluate(tmp_path, tmp_path, (None, None, None, None, None), 'h')


@pytest.mark.parametrize('trial', ['fixed100', 'base_es'])
def test_real_lightgbm_sequence_inner_saved_model_and_objective(tmp_path, trial):
    rng = np.random.default_rng(142)
    cache, stage = tmp_path/'cache', tmp_path/'trial'
    cache.mkdir()
    stage.mkdir()
    inventory = {}
    for role, n in [('inner_train', 800), ('inner_valid', 240)]:
        x = rng.normal(size=(n, 3)).astype('float64')
        y = x[:, 0]*.1+rng.normal(size=n)*.03
        x.tofile(cache/f'{role}.float64')
        np.save(cache/f'{role}_target.npy', y)
        np.save(cache/f'{role}_weight.npy', np.full(n, 1/40))
        pd.DataFrame(dict(datetime=pd.bdate_range('2013-01-01', periods=n//40).repeat(40),
                          instrument=[f'S{i}' for i in range(40)]*(n//40))).to_parquet(cache/f'{role}_keys.parquet', index=False)
        inventory[role] = [dict(file=f'{role}.float64')]
    (cache/'blocks.json').write_text(json.dumps(inventory))
    config = dict(model_params=dict(objective='regression', num_leaves=3, min_data_in_leaf=10,
        learning_rate=.03, num_threads=8, deterministic=True, force_col_wise=True,
        verbosity=-1, feature_pre_filter=False, seed=12))
    job.train_inner(stage, cache, ['a', 'b', 'c'], config, trial, {})
    result = job.base.read_json(stage/'result.json')
    assert 1 <= result['rounds'] <= 800 and not result['outer_labels_accessed']
    if trial == 'fixed100':
        assert result['rounds'] == 100
    pred = pd.read_parquet(stage/'inner_predictions.parquet')
    expected = [spearmanr(p.score, p.target).statistic for _, p in pred.groupby('datetime')]
    assert np.mean(expected) == pytest.approx(result['mean_ic'], abs=1e-12)


def test_cache_retirement_is_scoped_and_resumable(tmp_path):
    fold, bound = 'annual_2015', 'h'
    def cache(stage):
        (stage/'a.float64').write_bytes(b'12345678')
        (stage/'keys.json').write_text('{}')
    job.v3.publish(tmp_path/fold/'cache', bound, cache)
    job.v3.publish(tmp_path/fold/'outer', bound, lambda stage: (stage/'model.txt').write_text('model'))
    receipt = (tmp_path/fold/'cache/receipt.json').read_bytes()
    job.retire_cache(tmp_path, fold, bound)
    job.retire_cache(tmp_path, fold, bound)
    assert not (tmp_path/fold/'cache/a.float64').exists()
    assert (tmp_path/fold/'cache/keys.json').exists()
    assert (tmp_path/fold/'cache/receipt.json').read_bytes() == receipt


def test_nine_year_evaluator_synthetic_common_sample_and_maturity(tmp_path, monkeypatch):
    source, baseline, out, stage = [tmp_path/p for p in ['source', 'baseline', 'out', 'evaluation']]
    stage.mkdir()
    monkeypatch.setattr(job, 'BASELINE', baseline)
    monkeypatch.setattr(job, 'verify_selection', lambda *args: None)
    monkeypatch.setattr(job, 'selection', lambda *args: {'selected': 'fixed100', 'rounds': 100})
    assignments, intervals = [], []
    for year in range(2015, 2024):
        fold = f'annual_{year}'
        dates = pd.bdate_range(f'{year}-01-05', periods=3)
        keys = pd.DataFrame(dict(datetime=dates.repeat(120), instrument=[f'S{i:03}' for i in range(120)]*3))
        pred = keys.assign(score=np.tile(np.arange(120, dtype=float), 3), reason='predicted')
        labels = keys.loc[keys.datetime.isin(dates[:2])].copy()
        labels[job.v3.LABEL] = np.tile(np.arange(120, dtype=float), 2)
        labels['exit_date'] = labels.datetime + pd.Timedelta(days=30)
        # Two mature dates and one deliberately unscored date on the full prediction axis.
        assignments.extend(dict(fold_id=fold, role='evaluate', datetime=d) for d in dates[:2])
        intervals.extend(dict(feature_time=d, label_end_time=d+pd.Timedelta(days=30)) for d in dates[:2])
        job.v3.publish(source/'audit'/str(year), job.base.SOURCE_HASH,
                       lambda folder: labels.to_parquet(folder/'labels.parquet', index=False))
        (baseline/'Broad494'/fold).mkdir(parents=True)
        pred.to_parquet(baseline/'Broad494'/fold/'engineering_predictions.parquet', index=False)
        tuned = pred.assign(score=-pred.score)
        job.v3.publish(out/fold/'outer', 'h', lambda folder: tuned.to_parquet(folder/'engineering_predictions.parquet', index=False))
        for name, _ in policy.TRIALS:
            folder = out/fold/'trials'/name
            folder.mkdir(parents=True)
            (folder/'result.json').write_text(json.dumps({'trial': name}))
    job.v3.publish(out/'verification', 'h', lambda folder: (folder/'result.json').write_text('{}'))
    protocol = dict(assignments=pd.DataFrame(assignments), intervals=pd.DataFrame(intervals))
    evaluate(stage, out, (source, None, None, protocol, None), 'h')
    daily = pd.read_csv(stage/'daily.csv')
    assert len(daily) == 27 and daily.delta.notna().sum() == 18
    np.testing.assert_allclose(daily.delta.dropna(), -2.)
    summary = job.base.read_json(stage/'summary.json')
    assert summary['recommended_model'] is None
    assert summary['descriptive'][1]['negative_year_count'] == 9
    assert len(summary['trials']) == 81
