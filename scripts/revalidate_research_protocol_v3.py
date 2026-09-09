"""Independent calendar/count checks and a bounded real-data input parity probe.

This does not approve research results or evaluate model performance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_research_protocol_v3_mvp as runner  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from model_research.long_history_walk_forward import Float64FileSequence, fit_arrays, fit_sequences  # noqa: E402


def calendar_oracle(calendar, protocol):
    """Position arithmetic independent of build_protocol / label_intervals."""
    dates = pd.DatetimeIndex(calendar)
    rows = []
    for year in range(2015, 2024):
        vintage = dates[dates.year == year]
        start_pos = dates.get_loc(vintage[0])
        train = dates[:start_pos - 21]
        mature = dates[dates.get_indexer(vintage) + 21]
        scored = vintage[mature <= runner.END]
        for role, expected in [('train', train), ('predict', vintage), ('evaluate', scored)]:
            actual = pd.DatetimeIndex(protocol['assignments'].loc[
                (protocol['assignments'].fold_id == f'annual_{year}') &
                (protocol['assignments'].role == role), 'datetime'])
            if not actual.equals(expected):
                raise ValueError(f'independent calendar mismatch: {year}/{role}')
        row = protocol['folds'].set_index('fold_id').loc[f'annual_{year}']
        if (row.last_legal_train_signal != train[-1] or row.train_label_end != dates[start_pos - 1]
                or row.latest_mature_eval_signal != scored[-1] or row.purged_dates != 21):
            raise ValueError('independent fold boundary mismatch')
        rows.append(dict(year=year, train_dates=len(train), prediction_dates=len(vintage),
                         scored_dates=len(scored), last_train=str(train[-1].date())))
    return rows


def real_probe(stage, partitions, calendar, protocol, config, provider):
    """Ten predetermined 2020 train sessions; no old labels, features or model cache."""
    import qlib
    from qlib.data import D
    qlib.init(provider_uri=str(provider), region='cn', kernels=1)
    days = calendar[calendar.year == 2020][:10]
    factors = sorted(pd.read_csv(ROOT / 'reports/candidate_consolidation_v0_5/working_set.csv').factor)
    access = []
    features = runner.read_features(partitions, factors, days, access=access,
                                   protocol=protocol, fold_id='annual_2023', role='train')
    keys = runner.read_keys(partitions, days, access=access)
    pd.testing.assert_frame_equal(features[runner.KEYS], keys)
    captured = []
    def loader(symbols, lo, hi):
        prices = D.features(symbols, ['$close'], start_time=lo, end_time=hi, freq='day').reset_index()
        captured.append(prices)
        return prices
    labels = runner.read_labels(keys, calendar, loader, access=access,
                                protocol=protocol, fold_id='annual_2023', role='train')
    prices = captured[0].set_index(runner.KEYS)['$close']
    positions = calendar.get_indexer(pd.DatetimeIndex(keys.datetime))
    entry_keys = pd.MultiIndex.from_arrays([calendar[positions + 1], keys.instrument], names=runner.KEYS)
    exit_keys = pd.MultiIndex.from_arrays([calendar[positions + 21], keys.instrument], names=runner.KEYS)
    entry = prices.reindex(entry_keys).to_numpy(dtype='float64')
    exit_price = prices.reindex(exit_keys).to_numpy(dtype='float64')
    with np.errstate(divide='ignore', invalid='ignore'):
        oracle = exit_price / entry - 1
    oracle[(entry <= 0) | (exit_price <= 0) | ~np.isfinite(entry) | ~np.isfinite(exit_price)] = np.nan
    oracle[~np.isfinite(oracle)] = np.nan
    np.testing.assert_array_equal(labels[runner.LABEL].to_numpy(), oracle)
    # Small probe may contain all-empty columns; this is not a full-history pool eligibility rule.
    profile = runner.feature_profile(features, factors)
    selected = profile.loc[(profile.finite_dates >= 2) & (profile.minimum < profile.maximum), 'factor'].tolist()
    x, y, w, receipt = runner.prepare_training_batch(features[[*runner.KEYS, *selected]], labels, selected,
        protocol=protocol, fold_id='annual_2023', minimum_pairs=config['minimum_daily_pairs'])
    dense = fit_arrays(x, y, w, selected, fold_id='annual_2023', config=config)
    sequences = []
    try:
        for number, block in enumerate(np.array_split(x, 2)):
            path = stage / f'probe_{number}.float64'
            block.tofile(path)
            sequences.append(Float64FileSequence(path, len(selected)))
        streamed = fit_sequences(sequences, y, w, selected, fold_id='annual_2023', config=config)
        np.testing.assert_array_equal(dense.booster.predict(x, num_threads=8), streamed.booster.predict(x, num_threads=8))
        if dense.receipt['model_sha256'] != streamed.receipt['model_sha256']:
            raise ValueError('real-data dense/sequence model mismatch')
        streamed.booster.save_model(str(stage / 'model.txt'))
    finally:
        for seq in sequences:
            seq.close()
    runner.write_csv(stage / 'feature_profile.csv', profile)
    runner.atomic_write_json(stage / 'probe.json', dict(start=str(days[0]), end=str(days[-1]),
        requested_columns=len(factors), fitted_columns=len(selected), fit_rows=len(y),
        excluded_probe_only=sorted(set(factors) - set(selected)), label_oracle_exact=True,
        dense_sequence_model_exact=True, receipt=receipt, model_sha256=streamed.receipt['model_sha256'],
        full_width_resource_qualified=False))
    runner.atomic_write_json(stage / 'access.json', dict(access=access))


def verify_counts(out, protocol):
    """Recount saved row-level labels/keys instead of trusting summary CSV values."""
    samples = pd.read_csv(out / 'p1/sample_counts.csv')
    daily = []
    for year in range(2010, 2024):
        labels = pd.read_parquet(out / 'audit' / str(year) / 'labels.parquet')
        keys = pd.read_parquet(out / 'audit' / str(year) / 'keys.parquet')
        if labels.duplicated(runner.KEYS).any() or keys.duplicated(runner.KEYS).any():
            raise ValueError('duplicate audit keys')
        label_count = labels.assign(finite=np.isfinite(labels[runner.LABEL])).groupby('datetime').agg(
            label_keys=('instrument', 'size'), finite_labels=('finite', 'sum'))
        key_count = keys.groupby('datetime').size().rename('keys')
        daily.append(pd.concat([key_count, label_count], axis=1))
    daily = pd.concat(daily)
    for row in samples.itertuples():
        days = protocol['assignments'].loc[(protocol['assignments'].fold_id == row.fold_id) &
                                          (protocol['assignments'].role == row.role), 'datetime']
        values = daily.loc[days]
        expected = values['keys' if row.role == 'predict' else 'label_keys'].sum()
        if row.keys != expected or row.dates != len(days):
            raise ValueError('sample count mismatch')
        if row.role != 'predict' and (row.finite_labels != values.finite_labels.sum()
                or row.min_daily_finite_labels != values.finite_labels.min()
                or row.dates_below_100 != values.finite_labels.lt(100).sum()):
            raise ValueError('finite label count mismatch')
    return dict(recounted_rows=len(samples), annual_audits=14)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--mode', choices=['probe', 'verify'], required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'v3_recompute_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('use an independent v3_recompute_ run-id')
    out = ROOT / 'outputs/research_protocol_v3_mvp' / args.run_id
    config = yaml.safe_load((ROOT / 'configs/research_protocol_v3_mvp.yaml').read_text())
    provider = runner.load_settings(project_root=ROOT).qlib_provider
    with runner.run_lock(out / 'run.lock'):
        partitions, _, calendar, protocol, bound = runner.bind(config, out, provider)
        full_calendar = pd.DatetimeIndex(pd.to_datetime((provider / 'calendars/day.txt').read_text().splitlines()))
        full_calendar = full_calendar[full_calendar >= runner.START]
        oracle = calendar_oracle(full_calendar, protocol)
        runner.prepare(out, protocol, bound)
        if args.mode == 'probe':
            for row in partitions.loc[pd.to_datetime(partitions.effective_start) <= runner.END].drop_duplicates('partition_path').itertuples():
                if runner.sha256_file(Path(row.partition_path)) != row.output_sha256:
                    raise ValueError('canonical source integrity failure')
            runner.publish(out / 'revalidation_probe', bound,
                lambda stage: real_probe(stage, partitions, calendar, protocol, config, provider))
            result = dict(status='bounded_probe_complete_full_recomputation_pending', calendar=oracle)
        else:
            runner.require_audit(out, bound, range(2010, 2024))
            for folder in [out / 'revalidation_probe', *[out / kind / fold for kind in ['canary', 'wide_canary']
                                                       for fold in config['canary_folds']]]:
                if not runner.completed_chunk(folder, bound):
                    raise ValueError(f'recomputation incomplete: {folder}')
            result = dict(status='recomputed_counts_checked_review_pending', calendar=oracle,
                          counts=verify_counts(out, protocol), full_width_resource_qualified=False)
        runner.publish(out / ('revalidation_' + args.mode + '_summary'), bound,
                       lambda stage: runner.atomic_write_json(stage / 'result.json', result))
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
