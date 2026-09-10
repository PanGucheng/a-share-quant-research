"""D2 high-risk boundaries and a synthetic 358-column Sequence/save/replay canary."""
from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from model_research import literature_precompute as job
from research_validation import literature_prediction_replay as replay
from factor_research.literature_representation import transform_day, KEYS


def test_freeze_and_learner_identity():
    ctx = job.context()  # only pinned metadata and receipt checks
    assert {k: len(v) for k, v in ctx['recipe']['arms'].items()} == {'R': 218, 'C': 201, 'H': 358}
    bs = job.d1.read_json(job.ROOT / job.freeze.BS / 'contract.json')
    assert ctx['config'] == bs['config']
    assert ctx['runtime'] == bs['runtime']
    assert ctx['approval']['semantics']['variable_node_composition']


def test_run_binding_rejects_identity_order_policy_changes(tmp_path):
    ctx = job.context()
    bound = job.bind(tmp_path, ctx)
    assert job.bind(tmp_path, ctx) == bound
    for mutate in [lambda c: c['recipe']['arms']['H'].reverse(),
                   lambda c: c['config']['model_params'].update(num_leaves=16),
                   lambda c: c['approval']['semantics'].update(variable_node_composition=False)]:
        altered = deepcopy(ctx)
        mutate(altered)
        with pytest.raises(ValueError, match='contract mismatch'):
            job.bind(tmp_path, altered)


def test_atomic_failure_and_corruption_are_preserved(tmp_path):
    target = tmp_path / 'unit'

    def fail(stage):
        (stage / 'original.txt').write_text('evidence')
        raise RuntimeError('interrupt')

    with pytest.raises(RuntimeError):
        job.publish(target, 'binding', fail)
    with pytest.raises(ValueError, match='incomplete unit'):
        job.publish(target, 'binding', lambda p: pytest.fail('must not rerun'))
    assert (tmp_path / '.unit.incomplete/original.txt').read_text() == 'evidence'
    other = tmp_path / 'good'
    job.publish(other, 'binding', lambda p: (p / 'data.txt').write_text('original'))
    job.publish(other, 'binding', lambda p: pytest.fail('completed writer must not run'))
    (other / 'data.txt').write_text('changed')
    with pytest.raises(ValueError, match='corrupted'):
        job.complete(other, 'binding')


@pytest.mark.parametrize('days', [['2024-01-02'], ['2023-12-29', '2023-12-28'], ['2023-12-29', '2023-12-29']])
def test_future_invalid_dates_fail_before_io(days, tmp_path, monkeypatch):
    monkeypatch.setattr(job.d1, 'read_json', lambda *a: pytest.fail('I/O before date gate'))
    with pytest.raises(ValueError):
        job.feature_month({}, days, lambda e: pytest.fail('access'))
    with pytest.raises(ValueError):
        job.cached_features(tmp_path, {}, 'bound', 'H', days, 'annual_2023', 'predict')


def test_training_fold_role_rejection_before_cache_io(tmp_path, monkeypatch):
    ctx = job.context()
    monkeypatch.setattr(job, 'complete', lambda *a: pytest.fail('cache accessed before fold gate'))
    with pytest.raises(ValueError):
        job.cached_features(tmp_path, ctx, 'bound', 'H', pd.to_datetime(['2023-01-03']), 'annual_2023', 'train')


def test_month_cache_matches_frozen_daily_hash_and_arm_order(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(job.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=100 * 2**30))
    ctx = job.context()
    recipe = ctx['recipe']
    dates = pd.DatetimeIndex(['2023-01-03', '2023-01-04'])
    rng = np.random.default_rng(11)
    raw = pd.concat([pd.DataFrame(dict(datetime=dates.repeat(120),
        instrument=[f'S{i:03}' for i in range(120)]*2)),
        pd.DataFrame(rng.normal(size=(240, 489)), columns=recipe['parents'])], axis=1)
    hashes = []
    expected = []
    for day, part in raw.groupby('datetime'):
        arms = transform_day(part.reset_index(drop=True), recipe)[0]
        hashes.append(dict(datetime=str(day.date()), hashes={k: job.frame_digest(v) for k, v in arms.items()}))
        expected.append(arms)
    evidence = dict(dates=dates.strftime('%Y-%m-%d').tolist(), output_hashes=hashes)
    monkeypatch.setattr(job.d1, 'scheduled_dates', lambda *a: dates)
    monkeypatch.setattr(job, 'feature_month', lambda *a: (raw, evidence))
    job.create_cache(tmp_path, ctx, 'bound')
    for arm in job.POOLS:
        actual, _ = job.cached_features(tmp_path, ctx, 'bound', arm, dates, 'annual_2023', 'predict')
        pd.testing.assert_frame_equal(actual, pd.concat([e[arm] for e in expected], ignore_index=True), check_exact=True)
    monkeypatch.setattr(job, 'feature_month', lambda *a: pytest.fail('completed cache reread canonical'))
    job.create_cache(tmp_path, ctx, 'bound')


def test_synthetic_full_width_sequence_and_independent_replay(tmp_path, monkeypatch):
    ctx = job.context()
    recipe = ctx['recipe']
    fold = 'annual_2023'
    train_day = job.v3.training_dates(ctx['protocol'], fold)[-1]
    predict_day = pd.Timestamp('2023-01-03')
    rng = np.random.default_rng(613)
    sources, produced = {}, {}
    for day in [train_day, predict_day]:
        values = rng.normal(size=(1600, len(recipe['parents'])))
        values[rng.random(values.shape) < .03] = np.nan
        raw = pd.concat([pd.DataFrame(dict(datetime=[day]*1600, instrument=[f'S{i:04}' for i in range(1600)])),
                         pd.DataFrame(values, columns=recipe['parents'])], axis=1)
        sources[day] = raw
        produced[day] = transform_day(raw, recipe)[0]['H']
    ctx['protocol']['assignments'] = pd.DataFrame(dict(fold_id=[fold, fold],
        role=['train', 'predict'], datetime=[train_day, predict_day]))
    monkeypatch.setattr(job.v3, 'training_dates', lambda *a: pd.DatetimeIndex([train_day]))

    def cached(out, context, bound, arm, days, fold, role):
        assert len(days) == 1
        return produced[days[0]].copy(), dict(role=role)

    def labels(*args):
        assert args[-1].equals(pd.DatetimeIndex([train_day]))
        raw = sources[train_day]
        label = np.nan_to_num(raw[recipe['representatives'][0]].to_numpy())
        end = ctx['protocol']['intervals'].set_index('feature_time').loc[train_day, 'label_end_time']
        return raw[KEYS].assign(**{job.v3.LABEL: label}, exit_date=end)

    monkeypatch.setattr(job, 'cached_features', cached)
    monkeypatch.setattr(job.v3, 'cached_training_labels', labels)
    _, _, _, batch = job.v3.prepare_training_batch(produced[train_day],
        labels(None, None, None, pd.DatetimeIndex([train_day])), recipe['arms']['H'],
        protocol=ctx['protocol'], fold_id=fold, minimum_pairs=100)
    ctx['anchors'] = {fold: dict(batch_receipts=[dict(month=str(train_day.to_period('M')), **batch)],
                               fit_rows=1600, prediction_rows=1600, predicted_dates=1)}
    folder = tmp_path / 'H' / fold
    job.publish(folder, 'bound', lambda stage: job.fit_fold(stage, tmp_path, ctx, 'bound', 'H', fold))
    resource = job.d1.read_json(folder / 'resource.json')
    assert resource['actual_iterations'] == 100 and resource['fit_rows'] == 1600
    assert len(resource['ordered_features']) == 358
    assert not list(folder.glob('*.float64'))
    monkeypatch.setattr(job, 'feature_month', lambda *a: (sources[predict_day], {}))

    def forbidden(*a, **k):
        pytest.fail('independent replay called production transform/predict or label reader')

    monkeypatch.setattr(job, 'transform_day', forbidden)
    monkeypatch.setattr(job.v3, 'predict', forbidden)
    monkeypatch.setattr(job.v3, 'cached_training_labels', forbidden)
    result = tmp_path / 'replay' / 'H' / fold
    job.publish(result, 'bound', lambda stage: replay.replay_fold(stage, folder, tmp_path, ctx, 'bound', 'H', fold))
    assert job.d1.read_json(result / 'result.json')['status'] == 'exact'
    # A modified score with an internally self-consistent file checksum must still
    # fail independent numerical replay, beyond ordinary receipt corruption checks.
    scores = pd.read_parquet(folder / 'predictions.parquet')
    scores.loc[0, 'score'] += .01
    scores.to_parquet(folder / 'predictions.parquet', index=False)
    receipt_path = folder / 'receipt.json'
    receipt = job.d1.read_json(receipt_path)
    receipt['file_hashes']['predictions.parquet'] = job.d1.sha(folder / 'predictions.parquet')
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(AssertionError):
        job.publish(tmp_path / 'bad_replay', 'bound',
            lambda stage: replay.replay_fold(stage, folder, tmp_path, ctx, 'bound', 'H', fold))


def test_same_day_transform_ignores_future_values():
    recipe, _ = job.d1.load_packet()
    rng = np.random.default_rng(30)
    raw = pd.concat([pd.DataFrame(dict(datetime=[pd.Timestamp('2023-12-28')]*120,
                                       instrument=[f'S{i:03}' for i in range(120)])),
                     pd.DataFrame(rng.normal(size=(120, 489)), columns=recipe['parents'])], axis=1)
    before = transform_day(raw, recipe)[0]['H']
    future = raw.copy()
    future['datetime'] = pd.Timestamp('2023-12-29')
    future.iloc[:, 2:] *= -10000
    combined = pd.concat([raw, future], ignore_index=True)
    after = pd.concat([transform_day(part.reset_index(drop=True), recipe)[0]['H']
                       for _, part in combined.groupby('datetime')], ignore_index=True)
    pd.testing.assert_frame_equal(before, after.iloc[:120].reset_index(drop=True), check_exact=True)
