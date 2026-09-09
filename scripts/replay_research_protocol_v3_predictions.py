"""Independent saved-model replay of all prediction keys; never read outcome labels."""
from __future__ import annotations

import argparse
import gc
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import precompute_research_protocol_v3 as job  # noqa: E402
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from model_research.long_history_inputs import read_keys  # noqa: E402


def replay_fold(folder, fold, factors, partitions, protocol, config):
    resource = job.read_json(folder / 'resource.json')
    model = lgb.Booster(model_file=str(folder / 'model.txt'))
    if (hashlib.sha256(model.model_to_string().encode()).hexdigest() != resource['model_sha256']
            or model.current_iteration() != config['num_boost_round']
            or model.feature_name() != factors or resource['ordered_features'] != factors
            or resource['config_hash'] != job.v3.canonical_hash(config)
            or resource['fold_id'] != fold or resource['outer_labels_accessed'] is not False
            or resource['storage'] != 'monthly_float64_sequence'):
        raise ValueError('saved model authority mismatch')
    stored = pd.read_parquet(folder / 'engineering_predictions.parquet')
    if list(stored.columns) != [*job.v3.KEYS, 'score', 'reason'] or stored.duplicated(job.v3.KEYS).any():
        raise ValueError('invalid prediction schema/keys')
    assignments = protocol['assignments']
    days = pd.DatetimeIndex(assignments.loc[(assignments.fold_id == fold) &
                                            (assignments.role == 'predict'), 'datetime'])
    if not pd.DatetimeIndex(stored.datetime.unique()).equals(days):
        raise ValueError('incomplete annual prediction calendar')
    access = []
    for month in days.to_period('M').unique():
        selected = days[days.to_period('M') == month]
        frame = job.v3.read_features(partitions, factors, selected, access=access,
                                    protocol=protocol, fold_id=fold, role='predict')
        keys = read_keys(partitions, selected, access=access)
        saved = stored.loc[stored.datetime.isin(selected)].reset_index(drop=True)
        pd.testing.assert_frame_equal(keys, saved[job.v3.KEYS], check_exact=True)
        pd.testing.assert_frame_equal(frame[job.v3.KEYS], keys, check_exact=True)
        matrix = frame[factors].to_numpy(dtype='float64', copy=True)
        matrix[~np.isfinite(matrix)] = np.nan
        valid = np.isfinite(matrix).any(axis=1)
        scores = np.full(len(frame), np.nan)
        scores[valid] = model.predict(matrix[valid], num_threads=8)
        if not np.isfinite(scores[valid]).all():
            raise ValueError('nonfinite model prediction')
        np.testing.assert_array_equal(scores, saved.score.to_numpy())
        np.testing.assert_array_equal(np.where(valid, 'predicted', 'all_features_missing'), saved.reason)
        del frame, keys, saved, matrix, scores
        gc.collect()
    for event in job.read_json(folder / 'access.json')['access']:
        if event['kind'] != 'feature' or event['role'] not in ('train', 'predict'):
            raise ValueError('unexpected data access in precompute')
        job.v3.allowed_dates(protocol, fold, event['role'], [pd.Timestamp(event['start'])])
        job.v3.allowed_dates(protocol, fold, event['role'], [pd.Timestamp(event['end'])])
    if (len(stored) != resource['prediction_rows'] or len(days) != resource['predicted_dates']
            or float(stored.score.notna().mean()) != resource['prediction_coverage']):
        raise ValueError('prediction receipt counts mismatch')
    return dict(fold=fold, rows=len(stored), dates=len(days), exact=True,
                model_sha256=resource['model_sha256']), access


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--pool', required=True, choices=job.POOLS)
    args = parser.parse_args()
    if not re.fullmatch(r'v3_precompute_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run-id')
    out = ROOT / 'outputs/research_protocol_v3_precompute' / args.run_id
    if not (out / 'contract.json').exists():
        raise FileNotFoundError('precompute contract required')
    context = job.load_context()
    source, old, partitions, protocol, members = context
    with job.v3.run_lock(out / 'run.lock'):
        bound = job.bind_run(out, context)
        # Integrity-check only the bounded canonical feature files; no label cache reads.
        job.verify_feature_slices(context)
        for fold in job.FOLDS:
            if not job.v3.completed_chunk(out / args.pool / fold, bound):
                raise ValueError(f'missing complete fold: {fold}')
        def writer(stage):
            results, accesses = [], {}
            for fold in job.FOLDS:
                result, access = replay_fold(out / args.pool / fold, fold, members[args.pool],
                                             partitions, protocol, old['config'])
                results.append(result)
                accesses[fold] = access
                print(f'Independent replay exact: {args.pool}/{fold}', flush=True)
            job.v3.atomic_write_json(stage / 'result.json', dict(pool=args.pool, folds=results,
                status='all_nine_exact', outcome_evaluation=False, pool_comparison=False, recent_access=False))
            job.v3.atomic_write_json(stage / 'access.json', accesses)
        try:
            job.v3.publish(out / 'verification' / args.pool, bound, writer)
            complete = all((out / 'verification' / pool / 'receipt.json').exists() for pool in job.POOLS)
            job.v3.atomic_write_json(out / 'status.json', dict(
                status='all_precompute_and_replay_complete' if complete else 'pool_replay_complete',
                pool=args.pool, outcome_evaluation=False, pool_comparison=False, recent_access=False))
        except Exception as error:
            job.v3.atomic_write_json(out / 'status.json', dict(status='replay_failed', pool=args.pool,
                error_type=type(error).__name__, error=str(error)))
            raise


if __name__ == '__main__':
    main()
