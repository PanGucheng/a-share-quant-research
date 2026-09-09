from pathlib import Path
import copy

import numpy as np
import pandas as pd
import pytest
import yaml

from research_validation.research_protocol_v3 import build_protocol, allowed_dates, training_dates, START, END, PHYSICAL_END
from model_research.long_history_inputs import read_features, read_labels, feature_profile, combine_profiles
from model_research.long_history_walk_forward import prepare_training_batch, fit_arrays, predict
from scripts.run_research_protocol_v3_mvp import publish, cached_training_labels


@pytest.fixture
def protocol():
    return build_protocol(pd.bdate_range(START, PHYSICAL_END))


def test_annual_purge_and_terminal_contract(protocol):
    assert len(protocol['folds']) == 9
    assert protocol['folds'].extra_embargo.eq(0).all()
    assert protocol['folds'].purged_dates.eq(21).all()
    for row in protocol['folds'].itertuples():
        train = training_dates(protocol, row.fold_id)
        intervals = protocol['intervals'].set_index('feature_time').loc[train]
        assert intervals.label_end_time.lt(row.evaluation_start).all()
        excluded = protocol['purged'].query('fold_id == @row.fold_id')
        assert excluded.label_end_time.min() == row.evaluation_start
        assert row.nominal_dates - row.usable_dates == (21 if row.fold_id == 'annual_2023' else 0)
        slide = training_dates(protocol, row.fold_id, 'sliding_4_calendar_years')
        assert slide.min().year == row.evaluation_start.year - 4
    assignments = protocol['assignments'].query("role == 'predict'")
    assert not assignments.datetime.duplicated().any()
    with pytest.raises(ValueError):
        allowed_dates(protocol, 'annual_2023', 'evaluate', [END])
    allowed_dates(protocol, 'annual_2023', 'predict', [END])


@pytest.mark.parametrize('mutation', ['duplicate', 'unordered', 'truncated'])
def test_bad_calendars(mutation):
    dates = pd.bdate_range(START, PHYSICAL_END)
    if mutation == 'duplicate':
        dates = dates.append(dates[-1:])
    elif mutation == 'unordered':
        dates = dates[::-1]
    else:
        dates = dates[:-1]
    with pytest.raises(ValueError):
        build_protocol(dates)


def test_illegal_requests_fail_before_io(protocol, monkeypatch):
    import model_research.long_history_inputs as inputs
    def forbidden(*args, **kwargs):
        pytest.fail('I/O reached before role check')
    monkeypatch.setattr(inputs, 'read_effective_partition', forbidden)
    next_year = protocol['folds'].iloc[0].evaluation_start
    with pytest.raises(ValueError):
        read_features(pd.DataFrame(), ['a'], [next_year], access=[], protocol=protocol,
                      fold_id='annual_2015', role='train')
    with pytest.raises(ValueError):
        read_features(pd.DataFrame(), ['a'], [pd.Timestamp('2024-01-02')], access=[])
    keys = pd.DataFrame({'datetime': [next_year], 'instrument': ['A']})
    with pytest.raises(ValueError):
        read_labels(keys, pd.bdate_range(START, END), forbidden, access=[], protocol=protocol,
                    fold_id='annual_2015', role='predict')


def test_reader_effective_boundaries_schema_and_key_axis(tmp_path, monkeypatch):
    dates = pd.bdate_range('2023-12-27', periods=5)
    frame = pd.DataFrame({'datetime': dates, 'instrument': 'A', 'a': range(5), 'b': range(5)})
    path = tmp_path / 'a.parquet'
    frame.to_parquet(path, index=False)
    partitions = pd.DataFrame([dict(partition_path=str(path), factors='a,b', effective_start='2023-12-28',
                                     effective_end='2024-01-02', output_sha256='fixture')])
    access = []
    result = read_features(partitions, ['b', 'a'], dates[1:3], access=access)
    assert list(result.columns) == ['datetime', 'instrument', 'b', 'a']
    assert result.datetime.max() == END
    assert result.a.tolist() == [1., 2.]
    assert access[0]['end'].startswith('2023-12-29')
    with pytest.raises(ValueError):
        read_features(partitions, ['absent'], dates[1:3], access=[])


def test_label_exact_endpoints_and_missing_prices(protocol):
    days = training_dates(protocol, 'annual_2015')[:3]
    calendar = pd.bdate_range(START, END)
    keys = pd.DataFrame({'datetime': days, 'instrument': 'A'})
    calls = []
    def loader(symbols, lo, hi):
        calls.append((lo, hi))
        selected = calendar[(calendar >= lo) & (calendar <= hi)]
        values = np.arange(len(selected), dtype=float) + 10
        values[-1] = np.nan
        return pd.DataFrame({'datetime': selected, 'instrument': 'A', '$close': values})
    labels = read_labels(keys, calendar, loader, access=[], protocol=protocol, fold_id='annual_2015', role='train')
    assert labels.label_20d_t1.iloc[0] == 2.0
    assert pd.isna(labels.label_20d_t1.iloc[-1])
    assert labels.exit_date.max() == calendar[23]
    assert calls[0] == (calendar[1], calendar[23])


def test_feature_only_eligibility_and_year_combination():
    days = pd.bdate_range('2012-01-02', periods=3)
    first = pd.DataFrame({'datetime': days, 'instrument': 'A', 'a': [0, 1, np.nan],
                          'empty': np.nan, 'constant': 0., 'late': np.nan})
    second = first.copy()
    second.datetime += pd.DateOffset(years=1)
    second['late'] = [1., 2., 3.]
    p1 = feature_profile(first, ['a', 'empty', 'constant', 'late'])
    p2 = feature_profile(second, ['a', 'empty', 'constant', 'late'])
    one = combine_profiles([p1]).set_index('factor')
    both = combine_profiles([p1, p2]).set_index('factor')
    assert one.loc['a', 'eligible'] and not one.loc['late', 'eligible']
    assert both.loc['late', 'eligible']
    assert not both.loc['empty', 'eligible'] and not both.loc['constant', 'eligible']
    assert both.loc['a', 'finite_dates'] == 4


def fixture_training(protocol):
    days = training_dates(protocol, 'annual_2015')[:5]
    keys = pd.MultiIndex.from_product([days, [f'S{i:03d}' for i in range(120)]], names=['datetime', 'instrument']).to_frame(index=False)
    rng = np.random.default_rng(100)
    frame = keys.assign(a=rng.normal(size=len(keys)), b=rng.normal(size=len(keys)))
    labels = keys.assign(label_20d_t1=np.linspace(-1, 1, len(keys)))
    labels['exit_date'] = labels.datetime.map(protocol['intervals'].set_index('feature_time').label_end_time)
    return frame, labels


def test_target_rank_is_pool_independent_and_train_only(protocol):
    frame, labels = fixture_training(protocol)
    frame.loc[0, 'a'] = np.nan
    x, y, weights, receipt = prepare_training_batch(frame[['datetime', 'instrument', 'a']], labels, ['a'],
                                                   protocol=protocol, fold_id='annual_2015')
    expected = labels.groupby('datetime').label_20d_t1.rank(pct=True) - .5
    np.testing.assert_array_equal(y, expected.iloc[1:])
    assert receipt['fit_rows'] == len(frame) - 1
    assert weights[:119].sum() == pytest.approx(1)
    bad = labels.copy()
    bad.loc[0, 'exit_date'] += pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        prepare_training_batch(frame, bad, ['a', 'b'], protocol=protocol, fold_id='annual_2015')


def test_fixed_fit_prediction_order_and_oof_label_independence(protocol):
    frame, labels = fixture_training(protocol)
    config = yaml.safe_load((Path(__file__).resolve().parents[1] / 'configs/research_protocol_v3_mvp.yaml').read_text())
    x, y, w, _ = prepare_training_batch(frame, labels, ['a', 'b'], protocol=protocol, fold_id='annual_2015')
    model = fit_arrays(x, y, w, ['a', 'b'], fold_id='annual_2015', config=config)
    evaluation = protocol['assignments'].query("fold_id == 'annual_2015' and role == 'predict'").datetime.iloc[:5]
    future = frame.copy()
    future['datetime'] = np.repeat(evaluation.to_numpy(), 120)
    predictions = predict(model, future, protocol=protocol)
    pieces = pd.concat([predict(model, group, protocol=protocol) for _, group in future.groupby('datetime')], ignore_index=True)
    pd.testing.assert_frame_equal(predictions, pieces)
    # This checks deterministic refit only. Disk-backed OOF mutation is tested separately.
    again = fit_arrays(x, y, w, ['a', 'b'], fold_id='annual_2015', config=config)
    assert model.receipt['model_sha256'] == again.receipt['model_sha256']
    one_thread = copy.deepcopy(config)
    one_thread['model_params']['num_threads'] = 1
    single = fit_arrays(x, y, w, ['a', 'b'], fold_id='annual_2015', config=one_thread)
    np.testing.assert_array_equal(predict(single, future, protocol=protocol).score, predictions.score)
    with pytest.raises(ValueError):
        predict(model, future[['datetime', 'instrument', 'b', 'a']], protocol=protocol)
    future[['a', 'b']] = np.nan
    with pytest.raises(ValueError):
        predict(model, future, protocol=protocol)


LABEL_NAME = 'label_20d_t1'


def test_atomic_resume_tamper_and_interruption(tmp_path):
    folder = tmp_path / 'chunk'
    def writer(stage):
        (stage / 'value.txt').write_text('evidence')
    publish(folder, 'hash', writer)
    publish(folder, 'hash', lambda stage: pytest.fail('completed chunk reexecuted'))
    (folder / 'value.txt').write_text('tampered')
    with pytest.raises(ValueError):
        publish(folder, 'hash', writer)
    def interrupted(stage):
        (stage / 'partial').write_text('partial')
        raise RuntimeError('interrupt')
    with pytest.raises(RuntimeError):
        publish(tmp_path / 'new', 'hash', interrupted)
    assert not (tmp_path / 'new').exists()
    publish(tmp_path / 'new', 'hash', writer)


def test_cached_training_loader_never_opens_current_oof_labels(tmp_path, protocol, monkeypatch):
    frame, labels = fixture_training(protocol)
    path = tmp_path / 'audit/2010'
    path.mkdir(parents=True)
    labels.to_parquet(path / 'labels.parquet', index=False)
    future = tmp_path / 'audit/2015'
    future.mkdir()
    (future / 'labels.parquet').write_bytes(b'corrupted OOF labels must never be opened by this fit')
    days = pd.DatetimeIndex(frame.datetime.unique())
    original_reader = pd.read_parquet
    calls = []
    def spy(path, **kwargs):
        calls.append(str(path))
        assert '2015' not in str(path)
        assert kwargs['filters'][0] == ('datetime', 'in', days.tolist())
        return original_reader(path, **kwargs)
    monkeypatch.setattr(pd, 'read_parquet', spy)
    first = cached_training_labels(tmp_path, protocol, 'annual_2015', days)
    (future / 'labels.parquet').write_bytes(b'changed outcome')
    second = cached_training_labels(tmp_path, protocol, 'annual_2015', days)
    pd.testing.assert_frame_equal(first, second)
    assert len(calls) == 2
    with pytest.raises(ValueError):
        cached_training_labels(tmp_path, protocol, 'annual_2015', [pd.Timestamp('2015-01-05')])
    assert len(calls) == 2


def test_feature_key_mismatch_and_duplicate_segments(tmp_path):
    days = pd.bdate_range('2014-01-02', periods=2)
    first = pd.DataFrame({'datetime': days, 'instrument': 'A', 'a': [1., 2.]})
    second = pd.DataFrame({'datetime': days, 'instrument': 'B', 'b': [1., 2.]})
    rows = []
    for name, frame in [('a', first), ('b', second)]:
        path = tmp_path / (name + '.parquet')
        frame.to_parquet(path, index=False)
        rows.append(dict(partition_path=str(path), factors=name, effective_start=days[0],
                         effective_end=days[-1], output_sha256='fixture'))
    with pytest.raises(ValueError, match='key axes'):
        read_features(pd.DataFrame(rows), ['a', 'b'], days, access=[])
    with pytest.raises(ValueError, match='overlapping'):
        read_features(pd.DataFrame([rows[0], rows[0]]), ['a'], days, access=[])


def test_missing_receipt_and_wrong_contract_fail_before_writer(tmp_path):
    folder = tmp_path / 'existing'
    folder.mkdir()
    (folder / 'old.txt').write_text('preserve')
    with pytest.raises(FileNotFoundError):
        publish(folder, 'new', lambda stage: pytest.fail('writer ran without receipt'))
    publish(tmp_path / 'sealed', 'old', lambda stage: (stage / 'a').write_text('original'))
    with pytest.raises(ValueError, match='invalid receipt'):
        publish(tmp_path / 'sealed', 'new', lambda stage: pytest.fail('writer ran with wrong binding'))
    assert (folder / 'old.txt').read_text() == 'preserve'


def test_foreign_p1_rejected_before_training_and_oof_audit_not_required(tmp_path):
    from scripts.run_research_protocol_v3_mvp import require_audit
    for name in ['p0', 'p1', 'audit/2010']:
        publish(tmp_path / name, 'parent', lambda stage: (stage / 'a').write_text('original'))
    with pytest.raises(ValueError, match='invalid receipt'):
        require_audit(tmp_path, 'child', [2010])
    require_audit(tmp_path, 'parent', [2010])  # OOF audit/2015 deliberately absent.


def test_float64_sequence_matches_array_with_extreme_values(tmp_path):
    from model_research.long_history_walk_forward import Float64FileSequence, fit_sequences
    config = yaml.safe_load(Path('configs/research_protocol_v3_mvp.yaml').read_text())
    rng = np.random.default_rng(907)
    x = rng.normal(size=(900, 12)).astype('float64')
    x[::11, 2] = np.nan
    x[::13, 3] = 2.95e107
    x[:, 5] = 0.0
    y = x[:, 0] / 5 + rng.normal(size=len(x)) / 10
    w = np.ones(len(x))
    names = [f'f{i}' for i in range(x.shape[1])]
    seqs = []
    try:
        for i, part in enumerate(np.array_split(x, 3)):
            path = tmp_path / f'{i}.float64'
            part.tofile(path)
            seqs.append(Float64FileSequence(path, len(names)))
        a = fit_arrays(x, y, w, names, fold_id='annual_2015', config=config)
        b = fit_sequences(seqs, y, w, names, fold_id='annual_2015', config=config)
        np.testing.assert_array_equal(a.booster.predict(x), b.booster.predict(x))
        assert a.receipt['model_sha256'] == b.receipt['model_sha256']
        path = tmp_path / 'model.txt'
        b.booster.save_model(str(path))
        import lightgbm as lgb
        np.testing.assert_array_equal(b.booster.predict(x), lgb.Booster(model_file=str(path)).predict(x))
    finally:
        for seq in seqs:
            seq.close()
    with pytest.raises(ValueError, match='float64'):
        fit_arrays(np.ones((900, 12), dtype='float32'), y, w, names, fold_id='annual_2015', config=config)


def test_disk_oof_mutation_preserves_training_model_and_predictions(tmp_path, protocol, monkeypatch):
    frame, labels = fixture_training(protocol)
    train = tmp_path / 'audit/2010'
    train.mkdir(parents=True)
    labels.to_parquet(train / 'labels.parquet', index=False)
    future = tmp_path / 'audit/2015'
    future.mkdir()
    future_labels = labels.copy()
    evaluation = protocol['assignments'].query("fold_id == 'annual_2015' and role == 'predict'").datetime.iloc[:5]
    future_labels.datetime = np.repeat(evaluation.to_numpy(), 120)
    future_labels.to_parquet(future / 'labels.parquet', index=False)
    features_path = tmp_path / 'features.parquet'
    frame.to_parquet(features_path, index=False)
    days = pd.DatetimeIndex(frame.datetime.unique())
    partitions = pd.DataFrame([dict(partition_path=str(features_path), factors='a,b',
        effective_start=days.min(), effective_end=days.max(), output_sha256='fixture')])
    original = pd.read_parquet
    def checked(path, **kwargs):
        assert Path(path) != future / 'labels.parquet', 'fit read current OOF labels'
        return original(path, **kwargs)
    monkeypatch.setattr(pd, 'read_parquet', checked)
    config = yaml.safe_load(Path('configs/research_protocol_v3_mvp.yaml').read_text())
    def execute():
        features = read_features(partitions, ['a', 'b'], days, access=[], protocol=protocol,
                                 fold_id='annual_2015', role='train')
        eligibility = combine_profiles([feature_profile(features, ['a', 'b'])])
        loaded = cached_training_labels(tmp_path, protocol, 'annual_2015', days)
        x, y, w, keys = prepare_training_batch(features, loaded, ['a', 'b'], protocol=protocol, fold_id='annual_2015')
        model = fit_arrays(x, y, w, ['a', 'b'], fold_id='annual_2015', config=config)
        predictions = predict(model, features.assign(datetime=np.repeat(evaluation.to_numpy(), 120)), protocol=protocol)
        return eligibility, x, y, w, keys, model.receipt['model_sha256'], predictions
    first = execute()
    future_labels['label_20d_t1'] = 1e100
    future_labels.to_parquet(future / 'labels.parquet', index=False)
    second = execute()
    pd.testing.assert_frame_equal(first[0], second[0])
    for i in [1, 2, 3]:
        np.testing.assert_array_equal(first[i], second[i])
    assert first[4:6] == second[4:6]
    pd.testing.assert_frame_equal(first[6], second[6])


@pytest.mark.parametrize('kind', ['duplicate', 'unordered', 'nat'])
def test_key_reader_rejects_dates_before_io(monkeypatch, kind):
    from model_research.long_history_inputs import read_keys
    import model_research.long_history_inputs as inputs
    dates = pd.bdate_range('2014-01-02', periods=2)
    dates = dates.append(dates[:1]) if kind == 'duplicate' else dates[::-1] if kind == 'unordered' else dates.append(pd.DatetimeIndex([pd.NaT]))
    monkeypatch.setattr(inputs, 'read_effective_partition', lambda *a, **k: pytest.fail('illegal I/O'))
    with pytest.raises(ValueError):
        read_keys(pd.DataFrame(), dates, access=[])


def test_wide_pipeline_saves_model_predictions_and_keeps_qualification_pending(tmp_path, protocol, monkeypatch):
    import json
    from scripts import run_research_protocol_v3_mvp as runner
    config = yaml.safe_load(Path('configs/research_protocol_v3_mvp.yaml').read_text())
    names = [f'factor_{i:03d}' for i in range(494)]
    membership = tmp_path / 'reports/candidate_consolidation_v0_5'
    membership.mkdir(parents=True)
    pd.DataFrame({'factor': names}).to_csv(membership / 'working_set.csv', index=False)
    (tmp_path / 'p1').mkdir()
    pd.DataFrame({'factor': names, 'fold_id': 'annual_2015', 'eligible': True}).to_csv(
        tmp_path / 'p1/feature_eligibility.csv', index=False)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    frame, labels = fixture_training(protocol)
    days = pd.DatetimeIndex(frame.datetime.unique())
    monkeypatch.setattr(runner, 'training_dates', lambda *a: days)
    monkeypatch.setattr(runner, 'cached_training_labels', lambda out, protocol, fold, selected:
                        labels.loc[labels.datetime.isin(selected)].reset_index(drop=True))
    local = copy.deepcopy(protocol)
    prediction_days = local['assignments'].query("fold_id == 'annual_2015' and role == 'predict'").datetime.iloc[[0, 22]]
    local['assignments'] = local['assignments'].loc[
        local['assignments'].role.ne('predict') | local['assignments'].datetime.isin(prediction_days)]
    def features(partitions, factors, requested, **kwargs):
        keys = pd.MultiIndex.from_product([requested, [f'S{i:03d}' for i in range(120)]],
                                         names=['datetime', 'instrument'])
        data = np.random.default_rng(901).normal(size=(len(keys), len(factors)))
        data[::13, 2] = 2.95e107
        return pd.DataFrame(data, index=keys, columns=factors).reset_index()
    monkeypatch.setattr(runner, 'read_features', features)
    stage = tmp_path / 'new-stage'
    stage.mkdir()
    runner.wide_canary(stage, 'annual_2015', tmp_path, config, None, local)
    resource = json.loads((stage / 'resource.json').read_text())
    assert resource['saved_model_exact_parity'] and resource['monthly_daily_exact_parity']
    assert resource['feature_count'] == 494 and resource['full_width_resource_qualified'] is False
    assert resource['predicted_dates'] == 2 and (stage / 'model.txt').is_file()
    assert not list(stage.glob('*.memmap'))
    pd.DataFrame({'factor': names, 'fold_id': 'annual_2015', 'eligible': False}).to_csv(
        tmp_path / 'p1/feature_eligibility.csv', index=False)
    monkeypatch.setattr(runner, 'read_features', lambda *a, **k: pytest.fail('read unqualified features'))
    with pytest.raises(ValueError, match='train-eligible'):
        runner.wide_canary(stage, 'annual_2015', tmp_path, config, None, local)
