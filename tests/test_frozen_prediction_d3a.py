"""Synthetic/oracle tests only: never open repository outcomes."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from model_research import frozen_prediction_evaluation as e
from research_validation import frozen_prediction_statistics as s


@pytest.mark.parametrize('sign', [1, -1])
def test_perfect_and_ties(sign):
    y = np.repeat(np.arange(50), 2).astype(float)
    x = np.tile(sign * y[:, None], (1, 5))
    actual, mask = s.common_day(y, x)
    assert mask.all() and actual['scoreable']
    for arm in s.ARMS:
        assert actual[f'IC_{arm}'] == pytest.approx(sign)
        assert actual[f'IC_{arm}'] == pytest.approx(spearmanr(y, x[:, 0]).statistic)


def test_common_masks_and_minimum():
    rng = np.random.default_rng(12)
    y, x = rng.normal(size=103), rng.normal(size=(103, 5))
    x[0, 1], x[1, 4], y[2] = np.nan, np.inf, np.nan
    row, mask = s.common_day(y, x)
    assert row['common_count'] == 100 and row['mature_label_count'] == 102
    assert row['finite_S'] == row['finite_H'] == 102 and row['finite_B'] == 103
    assert row['scoreable'] and not mask[:3].any()
    for i, arm in enumerate(s.ARMS):
        assert row[f'IC_{arm}'] == pytest.approx(spearmanr(y[mask], x[mask, i]).statistic)
    x[3, 0] = np.nan
    row, _ = s.common_day(y, x)
    assert row['common_count'] == 99 and not row['scoreable']
    assert all(np.isnan(row[f'IC_{a}']) for a in s.ARMS)


def test_constant_and_immature():
    y = np.arange(100.)
    x = np.tile(y[:, None], (1, 5))
    x[:, 2] = 1
    row, _ = s.common_day(y, x)
    assert not row['scoreable'] and row['reason'] == 'constant_label_or_arm_on_common_sample'
    row, _ = s.common_day(y, x, mature=False)
    assert row['common_count'] == row['mature_label_count'] == 0
    assert row['reason'] == 'unscored_development_boundary'


@pytest.mark.parametrize('gap', [False, True])
@pytest.mark.parametrize('lag', [20, 40])
def test_hac_dense_kernel_oracle(gap, lag):
    rng = np.random.default_rng(98)
    x = rng.normal(.02, .1, 123)
    if gap:
        x[[3, 10, 11, 39, 67, 92]] = np.nan
    valid = np.isfinite(x)
    mu = x[valid].mean()
    pos = np.flatnonzero(valid)
    # Independent O(n^2) kernel sandwich on original session distances.
    kernel = np.maximum(0, 1 - np.abs(pos[:, None] - pos[None, :])/(lag+1))
    u = x[valid] - mu
    variance = float(u @ kernel @ u) / len(u)**2
    got = s.hac_mean(x, lag)
    assert got['se']**2 == pytest.approx(variance)
    if gap:
        assert not np.isclose(got['se'], s.hac_mean(x[valid], lag)['se'], rtol=1e-6)


def test_hac_zero_and_known_delta():
    assert s.hac_mean(np.zeros(100), 20)['p'] == 1
    assert not s.hac_mean(np.ones(100)*.25, 20)['testable']
    x = np.tile([.1, .2, -.1, 0], 30)
    assert s.hac_mean(x, 20)['mean'] == pytest.approx(.05)
    assert not s.hac_mean([np.nan], 20)['testable']


def test_hac_normal_p_oracle():
    from scipy.stats import norm
    x = np.random.default_rng(91).normal(.03, .2, 200)
    result = s.hac_mean(x, 20)
    assert result['p'] == pytest.approx(2*norm.sf(abs(result['mean']/result['se'])))


def test_holm_fixed_family():
    p = [0.001, 0.01, 0.03, 0.04, 0.2, np.nan]
    np.testing.assert_allclose(s.holm_six(p), [.006, .05, .12, .12, .4, 1])
    with pytest.raises(ValueError):
        s.holm_six([.01]*5)


def test_shared_bootstrap_boundaries_and_oracle():
    x = np.arange(120.)
    x[60:65] = np.nan
    matrix = np.column_stack([x, -x, 2*x])
    ci, support = s.moving_block_intervals(matrix, 20, samples=20)
    starts, _ = s.block_support(np.isfinite(x), 20)
    assert support['available'] and not any(41 <= n <= 64 for n in starts)
    rng, means = np.random.default_rng(20260909), []
    for _ in range(20):
        positions = s.sampled_indices(starts, 115, 20, rng)
        for start in range(0, len(positions), 20):
            block = positions[start:start+20]
            assert np.all(np.diff(block) == 1) and np.isfinite(x[block]).all()
        means.append(matrix[positions].mean(axis=0))
    np.testing.assert_array_equal(ci, np.quantile(means, [.025, .975], axis=0))
    np.testing.assert_allclose(ci[:, 0], -ci[::-1, 1])
    np.testing.assert_allclose(ci[:, 2], ci[:, 0]*2)
    assert support == s.moving_block_intervals(matrix, 20, samples=20)[1]


def test_short_segments_never_publish_overall_interval():
    matrix = np.ones((130, 2))
    matrix[10:20] = np.nan
    ci, support = s.moving_block_intervals(matrix, 20)
    assert support['unsupported_dates'] == 10 and np.isnan(ci).all()
    matrix[22, 1] = np.nan
    with pytest.raises(ValueError, match='share scoreable dates'):
        s.moving_block_intervals(matrix, 20)


def synthetic_contract(tmp_path):
    schedules, sources, predictions = {}, [], []
    for year in range(2015, 2024):
        fold = f'annual_{year}'
        days = pd.bdate_range(f'{year}-10-01', periods=45)
        # Last synthetic 2023 prediction is intentionally immature.
        mature = days[:-1] if year == 2023 else days
        exits = mature + pd.Timedelta(days=29)
        schedules[fold] = dict(predict=e.date_strings(days), evaluate=e.date_strings(mature), exits=e.date_strings(exits))
        keys = pd.MultiIndex.from_product([days, [f'S{i:03}' for i in range(100)]], names=e.KEYS).to_frame(index=False)
        lab = keys.loc[keys.datetime.isin(mature)].copy()
        lab[e.LABEL] = np.tile(np.arange(100.), len(mature))
        lab['exit_date'] = lab.datetime.map(pd.Series(exits, index=mature))
        kp, lp = f'{year}_keys.parquet', f'{year}_labels.parquet'
        keys.to_parquet(tmp_path / kp, index=False)
        lab.to_parquet(tmp_path / lp, index=False)
        sources.append(dict(fold=fold, keys=kp, labels=lp, keys_sha256=e.sha(tmp_path/kp), label_sha256=e.sha(tmp_path/lp)))
        for i, a in enumerate(s.ARMS):
            pred = keys.copy()
            values = np.tile(np.arange(100.), len(days))
            # Perfect correlation and deterministic ties, with day-varying signal.
            pred['score'] = np.floor(values/(i+1)) + np.repeat(np.arange(len(days)) % 3, 100)
            pred['reason'] = 'predicted'
            path = f'{year}_{a}.parquet'
            pred.to_parquet(tmp_path/path, index=False)
            predictions.append(dict(fold=fold, arm=a, path=path, prediction_sha256=e.sha(tmp_path/path)))
    return dict(schedules=schedules, sources=sources, predictions=predictions, cutoff='2023-12-29',
        ordered_arms={a: [a] for a in s.ARMS}, scope=e.SCOPE, authorization='synthetic fixture',
        freeze_hash='synthetic', arm_identity_hashes={a: 'synthetic' for a in s.ARMS}, code_hashes_lf={}, runtime={})


@pytest.mark.parametrize('days,kind', [(['2024-01-02'], 'prediction'), (['2024-01-02'], 'label'),
                                     (['2023-12-01'], 'label'), (['2023-10-03','2023-10-02'], 'label'),
                                     (['2023-10-02','2023-10-02'], 'label')])
def test_illegal_read_before_io(tmp_path, monkeypatch, days, kind):
    contract = dict(cutoff='2023-12-29', schedules={'annual_2023': dict(predict=['2023-10-02'],
                    evaluate=['2023-10-02'], exits=['2023-10-31'])})
    monkeypatch.setattr(e, 'sha', lambda *args: pytest.fail('I/O before date rejection'))
    with pytest.raises(ValueError):
        e.read_bounded(tmp_path, contract, {'fold': 'annual_2023'}, kind, days, lambda _: None)


def test_synthetic_full_publication_and_reentry(tmp_path):
    contract = synthetic_contract(tmp_path)
    events = []
    daily = e.evaluate_daily(tmp_path, contract, events.append)
    assert len(daily) == 405 and daily.scoreable.sum() == 404
    assert len(events) == 9*7*2
    assert daily.common_count.sum() == 40400
    expected = [spearmanr(np.arange(100.), np.floor(np.arange(100.)/(i+1))).statistic for i in range(5)]
    for i, arm in enumerate(s.ARMS):
        np.testing.assert_allclose(daily.loc[daily.scoreable, f'IC_{arm}'], expected[i])
    for contrast in s.CONTRASTS:
        a, b = contrast.split('-')
        np.testing.assert_allclose(daily.loc[daily.scoreable, contrast], expected[s.ARMS.index(a)]-expected[s.ARMS.index(b)], atol=1e-15)
    assert all(event['kind'] in {'keys','label','prediction'} for event in events)
    assert e.run_once(tmp_path, contract, 'd3a_synthetic', 'test') == 'complete'
    sealed = tmp_path / 'outputs/literature_factor_representation_d3a/d3a_synthetic/sealed'
    e.verify_sealed(sealed, e.d2.digest(contract))
    assert e.run_once(tmp_path, contract, 'd3a_synthetic', 'test',
                      daily_evaluator=lambda *_: pytest.fail('numerical rerun')) == 'already_complete_verified'
    with pytest.raises(ValueError, match='different run'):
        e.run_once(tmp_path, contract, 'd3a_other', 'test')
    (sealed / 'daily.csv').write_text('damaged')
    with pytest.raises(ValueError, match='source bytes changed'):
        e.run_once(tmp_path, contract, 'd3a_synthetic', 'test')


def test_failure_leaves_opening_forever(tmp_path):
    contract = synthetic_contract(tmp_path)
    def fail(root, contract, log):
        assert (root / e.REPORT / 'OUTCOME_OPENED.json').exists()
        raise RuntimeError('synthetic interruption before values')
    with pytest.raises(RuntimeError):
        e.run_once(tmp_path, contract, 'd3a_fail', 'test', daily_evaluator=fail)
    receipt = tmp_path / 'outputs/literature_factor_representation_d3a/d3a_fail/OUTCOME_ACCESS_RECEIPT.json'
    digest = e.sha(receipt)
    with pytest.raises(ValueError, match='incomplete evidence'):
        e.run_once(tmp_path, contract, 'd3a_fail', 'test')
    assert e.sha(receipt) == digest


def test_corrupted_keys_exit_and_hash(tmp_path):
    contract = synthetic_contract(tmp_path)
    source = contract['sources'][0]
    schedule = contract['schedules'][source['fold']]
    original = pd.read_parquet(tmp_path/source['labels'])
    bad = original.copy()
    bad.loc[0, 'exit_date'] = pd.Timestamp('2024-01-02')
    bad.to_parquet(tmp_path/source['labels'], index=False)
    with pytest.raises(ValueError, match='changed after preflight'):
        e.read_bounded(tmp_path, contract, source, 'label', schedule['evaluate'], lambda _: None)
    source['label_sha256'] = e.sha(tmp_path/source['labels'])
    with pytest.raises(ValueError, match='maturity mapping'):
        e.read_bounded(tmp_path, contract, source, 'label', schedule['evaluate'], lambda _: None)
    original.iloc[[0, 0]].to_parquet(tmp_path/source['labels'], index=False)
    source['label_sha256'] = e.sha(tmp_path/source['labels'])
    with pytest.raises(ValueError, match='duplicate'):
        e.read_bounded(tmp_path, contract, source, 'label', schedule['evaluate'], lambda _: None)


def test_year_failure_preserves_six_family(tmp_path):
    contract = synthetic_contract(tmp_path)
    daily = e.evaluate_daily(tmp_path, contract, lambda _: None)
    absent = daily.datetime.dt.year == 2018
    daily.loc[absent, 'scoreable'] = False
    daily.loc[absent, [f'IC_{a}' for a in s.ARMS]+list(s.CONTRASTS)] = np.nan
    contrasts, _ = s.infer(daily)
    assert len(contrasts) == 6 and not contrasts.testable.any()
    assert not contrasts.reject.any() and contrasts.holm_p.eq(1).all()


def test_contract_mutation_detected(tmp_path, monkeypatch):
    contract = {'identity': 'frozen'}
    monkeypatch.setattr(e, 'ROOT', tmp_path)
    e.exclusive_json(tmp_path / e.PACKET / 'contract.json', contract)
    monkeypatch.setattr(e, 'preflight', lambda: {'identity': 'changed'})
    with pytest.raises(ValueError, match='differs from frozen'):
        e.checked_contract()
    with pytest.raises(FileExistsError):
        e.exclusive_json(tmp_path / e.PACKET / 'contract.json', {})


def test_preflight_does_not_read_value_tables(monkeypatch):
    # Guard contract validation at entry before heavy source traversal; no fallback reader.
    monkeypatch.setattr(e.d2, 'context', lambda: {'approval': {'evaluation_contract': {}}})
    monkeypatch.setattr(pd, 'read_parquet', lambda *a, **kw: pytest.fail('preflight must not load values'))
    with pytest.raises(ValueError, match='formal evaluation contract differs'):
        e.preflight()


def test_calendar_holiday_is_not_artificial_gap():
    # A normal weekend is adjacent in canonical-session positions.
    days = pd.to_datetime(['2023-10-05','2023-10-06','2023-10-09','2023-10-10'])
    starts, support = s.block_support(np.ones(len(days), dtype=bool), 2)
    assert support['available'] and 1 in starts


def test_pre_maturity_rejected_even_if_schedule_is_bad(monkeypatch, tmp_path):
    contract = dict(cutoff='2023-12-29', schedules={'annual_2023': dict(predict=['2023-12-01'],
                    evaluate=['2023-12-01'], exits=['2024-01-02'])})
    monkeypatch.setattr(e, 'sha', lambda *args: pytest.fail('I/O before maturity rejection'))
    with pytest.raises(ValueError, match='unmatured before I/O'):
        e.read_bounded(tmp_path, contract, {'fold': 'annual_2023'}, 'label', ['2023-12-01'], lambda _: None)


def test_real_maturity_metadata_without_values():
    # Deterministic synthetic complete calendar; role assignment enforces t+21, not a hardcoded cutoff.
    from research_validation.research_protocol_v3 import build_protocol
    calendar = pd.bdate_range('2010-01-29', '2026-06-09')
    protocol = build_protocol(calendar)
    dates = e.dates_for(protocol, 'annual_2023', 'evaluate')
    interval = protocol['intervals'].set_index('feature_time').loc[dates]
    assert interval.label_end_time.max() <= pd.Timestamp('2023-12-29')
    assert dates[-1] == calendar[calendar.get_loc(pd.Timestamp('2023-12-29'))-21]
