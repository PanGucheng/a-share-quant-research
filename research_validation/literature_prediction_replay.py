"""Independent D2 saved-Booster replay: no production composite or predict calls."""
from __future__ import annotations

import hashlib
import time

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from research_validation.literature_oracle import naive_day
from factor_research.literature_inputs import frame_digest
from factor_research.literature_representation import KEYS
from model_research import literature_precompute as job


def replay_fold(stage, folder, out, ctx, bound, arm, fold):
    if not job.complete(folder, bound):
        raise ValueError('completed model required for replay')
    resource = job.d1.read_json(folder / 'resource.json')
    identity = job.d1.read_json(folder / 'representation.json')
    columns = ctx['recipe']['arms'][arm]
    if (identity['ordered_columns'] != columns or identity['recipe_hash'] != ctx['recipe']['recipe_hash']
            or identity['freeze_hash'] != ctx['approval']['freeze_hash']
            or identity['output_types'] != job.output_types(ctx['recipe'], arm)
            or identity['parent_dependencies'] != job.dependencies(ctx['recipe'], arm)):
        raise ValueError('model representation mismatch')
    model = lgb.Booster(model_file=str(folder / 'model.txt'))
    if (model.feature_name() != columns or model.current_iteration() != 100
            or hashlib.sha256(model.model_to_string().encode()).hexdigest() != resource['model_sha256']
            or resource['config_hash'] != job.v3.canonical_hash(ctx['config'])
            or resource['fold_id'] != fold or resource['outer_labels_accessed'] is not False):
        raise ValueError('saved learner mismatch')
    assignments = ctx['protocol']['assignments']
    days = job.legal_dates(assignments.loc[
        (assignments.fold_id == fold) & (assignments.role == 'predict'), 'datetime'])
    job.v3.allowed_dates(ctx['protocol'], fold, 'predict', days)
    path = folder / 'predictions.parquet'
    # Predicate before score I/O; metadata row count detects any excluded dates.
    stored = pd.read_parquet(path, columns=KEYS + ['score', 'reason'],
                             filters=[('datetime', 'in', days.tolist())])
    if (len(stored) != pq.ParquetFile(path).metadata.num_rows or stored.duplicated(KEYS).any()
            or not pd.DatetimeIndex(stored.datetime.unique()).equals(days)):
        raise ValueError('prediction keys/date axis mismatch')
    tick = time.perf_counter()
    maximum = 0.
    with (stage / 'access.jsonl').open('x', encoding='utf-8') as stream:
        import json

        def log(event):
            stream.write(json.dumps(event) + '\n')
            stream.flush()

        with job.v3._MemorySampler() as memory:
            for month in days.to_period('M').unique():
                selected = days[days.to_period('M') == month]
                raw, _ = job.feature_month(ctx, selected, log)
                # Independently compute ranks/ties/means, never call transform_day.
                rebuilt = pd.concat([naive_day(part.reset_index(drop=True), ctx['recipe'])[arm]
                    for _, part in raw.groupby('datetime')], ignore_index=True)
                cached, _ = job.cached_features(out, ctx, bound, arm, selected, fold, 'predict')
                pd.testing.assert_frame_equal(rebuilt[KEYS], cached[KEYS], check_exact=True)
                a, b = rebuilt[columns].to_numpy(), cached[columns].to_numpy()
                np.testing.assert_array_equal(np.isfinite(a), np.isfinite(b))
                np.testing.assert_allclose(a, b, atol=1e-12, rtol=0, equal_nan=True)
                finite = np.isfinite(a)
                maximum = max(maximum, float(np.abs(a[finite] - b[finite]).max()) if finite.any() else 0.)
                expected = stored.loc[stored.datetime.isin(selected)].reset_index(drop=True)
                pd.testing.assert_frame_equal(rebuilt[KEYS], expected[KEYS], check_exact=True)
                valid = np.isfinite(a).any(axis=1)
                scores = np.full(len(a), np.nan)
                scores[valid] = model.predict(a[valid], num_threads=8)
                if not np.isfinite(scores[valid]).all():
                    raise ValueError('nonfinite independent prediction')
                np.testing.assert_array_equal(scores, expected.score.to_numpy())
                np.testing.assert_array_equal(np.where(valid, 'predicted', 'all_features_missing'), expected.reason)
                print(f'Independent prediction exact: {arm}/{fold}/{month}', flush=True)
    if (len(stored) != resource['prediction_rows'] or len(days) != resource['predicted_dates']
            or frame_digest(stored[KEYS]) != resource['prediction_keys_hash']
            or float(stored.score.notna().mean()) != resource['prediction_coverage']):
        raise ValueError('prediction resource/count mismatch')
    job.d1.write_json(stage / 'result.json', dict(status='exact', arm=arm, fold=fold,
        rows=len(stored), dates=len(days), model_sha256=resource['model_sha256'],
        model_receipt_sha256=job.d1.sha(folder / 'receipt.json'),
        recipe_hash=ctx['recipe']['recipe_hash'], representation_max_abs_error=maximum,
        replay_seconds=time.perf_counter() - tick, peak_rss_mib=memory.peak_mb,
        outcomes_authorized=False, recent_authorized=False))


def run(out, ctx, bound, arm, folds):
    for fold in folds:
        job.publish(out / 'replay' / arm / fold, bound,
            lambda stage: replay_fold(stage, out / arm / fold, out, ctx, bound, arm, fold))


def summary(out, ctx, bound):
    rows = []
    for arm in job.POOLS:
        for fold in job.FOLDS:
            folder = out / arm / fold
            replay = out / 'replay' / arm / fold
            if not job.complete(folder, bound) or not job.complete(replay, bound):
                raise ValueError(f'not all 27 units replayed: {arm}/{fold}')
            result = job.d1.read_json(replay / 'result.json')
            resource = job.d1.read_json(folder / 'resource.json')
            if (result['status'] != 'exact' or result['model_receipt_sha256'] != job.d1.sha(folder / 'receipt.json')
                    or result['model_sha256'] != resource['model_sha256']):
                raise ValueError('independent replay binding mismatch')
            rows.append(dict(arm=arm, fold=fold, train_rows=resource['fit_rows'],
                prediction_rows=resource['prediction_rows'], coverage=resource['prediction_coverage'],
                model_sha256=resource['model_sha256'], replay='exact',
                prepare_seconds=resource['prepare_seconds'], fit_seconds=resource['fit_seconds'],
                dataset_seconds=resource['dataset_seconds'], predict_seconds=resource['predict_seconds'],
                peak_rss_mib=resource['peak_rss_mib'], temporary_disk_bytes=resource['temporary_disk_bytes']))

    def writer(stage):
        pd.DataFrame(rows).to_csv(stage / 'folds.csv', index=False)
        job.d1.write_json(stage / 'result.json', dict(status='all_three_arms_all_nine_exact',
            arms={arm: 'all_nine_exact' for arm in job.POOLS}, models=27,
            freeze_hash=ctx['approval']['freeze_hash'], recipe_hash=ctx['recipe']['recipe_hash'],
            outcomes_authorized=False, pool_comparison=False, recent_authorized=False))
    job.publish(out / 'sealed', bound, writer)
