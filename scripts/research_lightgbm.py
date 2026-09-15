"""Nested B494 research: long runs are user-operated; no 2024+ or portfolio access."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import precompute_research_protocol_v3 as base  # noqa: E402
from model_research import lightgbm_nested as policy  # noqa: E402
from model_research.long_history_walk_forward import Float64FileSequence  # noqa: E402
from model_research.v3_prediction_precompute import precompute_fold  # noqa: E402
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

v3 = base.v3
BASELINE = ROOT / 'outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1'
BASELINE_HASH = 'f45bc6e4aab96d8d5897fcf69ee59c1e62ab2b12a53c8cf911ad217bd92e2130'
CODE = ['model_research/lightgbm_nested.py', 'scripts/research_lightgbm.py',
        'scripts/research_lightgbm.ps1', 'scripts/evaluate_lightgbm.py',
        'docs/LIGHTGBM_HYPERPARAMETER_RESEARCH.md',
        'research_validation/frozen_prediction_statistics.py']


def context():
    ctx = base.load_context()
    if v3.canonical_hash(base.read_json(BASELINE / 'contract.json')) != BASELINE_HASH:
        raise ValueError('baseline identity changed')
    for fold in [*base.FOLDS, 'verification/Broad494']:
        path = BASELINE / ('Broad494/' + fold if fold.startswith('annual') else fold)
        if not v3.completed_chunk(path, BASELINE_HASH):
            raise ValueError('baseline incomplete or changed')
    return ctx


def contract(ctx):
    source, old, _, protocol, members = ctx
    code = sorted(set([*CODE, *v3.CODE, *base.EXTRA_CODE]))
    splits = {}
    for fold in base.FOLDS:
        train, valid = policy.inner_split(protocol, fold)
        splits[fold] = dict(train=train.strftime('%Y-%m-%d').tolist(),
                            valid=valid.strftime('%Y-%m-%d').tolist())
    return dict(kind='LIGHTGBM_NESTED_DEVELOPMENT_V1', trials=policy.TRIALS,
        maximum_rounds=policy.MAX_ROUNDS, patience=policy.PATIENCE, min_delta=0,
        plateau_tolerance=policy.PLATEAU_TOLERANCE, maximum_fits=90,
        baseline_hash=BASELINE_HASH, source_hash=base.SOURCE_HASH, config=old['config'],
        runtime=old['runtime'], factors=members['Broad494'], splits=splits,
        code_lf={p: hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in code},
        audit_receipts={str(y): v3.sha256_file(source/'audit'/str(y)/'receipt.json') for y in range(2010, 2024)},
        portfolio=False, recent=False, evidence='retrospective_development_not_fresh_OOS')


def bind(out, ctx):
    value = json.loads(json.dumps(contract(ctx)))
    path = out/'contract.json'
    if path.exists() and base.read_json(path) != value:
        raise ValueError('research contract changed; preserve all evidence and stop')
    out.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        v3.atomic_write_json(path, value)
    return v3.canonical_hash(value)


def prepare_blocks(stage, ctx, fold):
    source, old, partitions, protocol, members = ctx
    factors = members['Broad494']
    train, valid = policy.inner_split(protocol, fold)
    access, inventory = [], {}
    for role, days in [('inner_train', train), ('inner_valid', valid)]:
        targets, weights, keys, records = [], [], [], []
        finite_columns = np.zeros(len(factors), dtype=bool)
        for month in days.to_period('M').unique():
            selected = days[days.to_period('M') == month]
            frame = v3.read_features(partitions, factors, selected, access=access,
                                    protocol=protocol, fold_id=fold, role='train')
            labels = v3.cached_training_labels(source, protocol, fold, selected)
            x, y, w, receipt = v3.prepare_training_batch(frame, labels, factors,
                protocol=protocol, fold_id=fold, minimum_pairs=old['config']['minimum_daily_pairs'])
            # This is the same mask as prepare_training_batch after its per-day eligibility check.
            mask = np.isfinite(labels[v3.LABEL].to_numpy()) & np.isfinite(frame[factors].to_numpy()).any(axis=1)
            selected_keys = frame.loc[mask, v3.KEYS].reset_index(drop=True)
            key_hash = hashlib.sha256(pd.util.hash_pandas_object(selected_keys, index=False).values.tobytes()).hexdigest()
            if key_hash != receipt['fit_keys_hash'] or len(selected_keys) != len(y):
                raise ValueError('inner metric/training sample mismatch')
            name = f'{role}_{month}.float64'
            x.tofile(stage/name)
            finite_columns |= np.isfinite(x).any(axis=0)
            records.append(dict(file=name, **receipt))
            targets.append(y)
            weights.append(w)
            keys.append(selected_keys)
            print(f'{fold}: {role} prepared {month}', flush=True)
            del x, frame, labels
            gc.collect()
        if role == 'inner_train' and not finite_columns.all():
            raise ValueError('all-empty inner training column; no retrospective feature removal')
        np.save(stage/f'{role}_target.npy', np.concatenate(targets))
        np.save(stage/f'{role}_weight.npy', np.concatenate(weights))
        pd.concat(keys, ignore_index=True).to_parquet(stage/f'{role}_keys.parquet', index=False)
        inventory[role] = records
    v3.atomic_write_json(stage/'blocks.json', inventory)
    v3.atomic_write_json(stage/'access.json', access)


def train_inner(stage, cache, factors, config, trial, changes):
    """Two Sequence datasets, train-only bins; callback closes over inner labels only."""
    inventory = base.read_json(cache/'blocks.json')
    sequences = {}
    tick = time.perf_counter()
    try:
        arrays = {}
        for role in ['inner_train', 'inner_valid']:
            sequences[role] = [Float64FileSequence(cache/r['file'], len(factors)) for r in inventory[role]]
            arrays[role] = [np.load(cache/f'{role}_{kind}.npy') for kind in ['target', 'weight']]
        valid_keys = pd.read_parquet(cache/'inner_valid_keys.parquet')
        counts = valid_keys.groupby('datetime', sort=True).size().to_numpy()
        params = {**config['model_params'], **changes, 'metric': 'None'}
        train = lgb.Dataset(sequences['inner_train'], label=arrays['inner_train'][0],
            weight=arrays['inner_train'][1], feature_name=factors, params=params)
        valid = lgb.Dataset(sequences['inner_valid'], label=arrays['inner_valid'][0],
            weight=arrays['inner_valid'][1], feature_name=factors, reference=train, params=params)
        def metric(pred, data):
            if data is not valid:
                raise ValueError('early stopping received an unexpected dataset')
            values, _ = policy.daily_ic(pred, arrays['inner_valid'][0], counts)
            return 'mean_daily_rank_ic', float(values.mean()), True
        history = {}
        callbacks = [lgb.record_evaluation(history), lgb.log_evaluation(50)]
        if trial != 'fixed100':
            callbacks.append(lgb.early_stopping(policy.PATIENCE, first_metric_only=True, verbose=False, min_delta=0.))
        limit = 100 if trial == 'fixed100' else policy.MAX_ROUNDS
        with v3._MemorySampler() as sampler:
            booster = lgb.train(params, train, num_boost_round=limit, valid_sets=[valid],
                                valid_names=['inner'], feval=metric, callbacks=callbacks)
        rounds = 100 if trial == 'fixed100' else booster.best_iteration
        if not 1 <= rounds <= limit or booster.current_iteration() < rounds:
            raise ValueError('insufficient constructed trees')
        booster.save_model(str(stage/'model.txt'), num_iteration=rounds)
        restored = lgb.Booster(model_file=str(stage/'model.txt'))
        predictions = []
        for seq in sequences['inner_valid']:
            values = []
            for start in range(0, len(seq), 4096):
                batch = seq[start:min(start+4096, len(seq))]
                pred = booster.predict(batch, num_iteration=rounds, num_threads=8)
                np.testing.assert_array_equal(pred, restored.predict(batch, num_threads=8))
                values.append(pred)
            predictions.append(np.concatenate(values))
        prediction = np.concatenate(predictions)
        scores, constants = policy.daily_ic(prediction, arrays['inner_valid'][0], counts)
        valid_keys.assign(score=prediction, target=arrays['inner_valid'][0]).to_parquet(stage/'inner_predictions.parquet', index=False)
        daily = pd.DataFrame({'datetime': valid_keys.datetime.unique(), 'ic': scores})
        daily.to_csv(stage/'daily.csv', index=False)
        curve = history['inner']['mean_daily_rank_ic']
        # Callback and saved model must use the same selected iteration and sample.
        if not np.isclose(scores.mean(), curve[rounds-1], atol=1e-12, rtol=0):
            raise ValueError('saved model differs from early-stop objective')
        result = dict(trial=trial, changes=changes, rounds=int(rounds), leaves=params['num_leaves'],
            **policy.describe(scores), constant_days=constants,
            half_year={str(h): policy.describe(part.ic) for h, part in daily.groupby((daily.datetime.dt.month-1)//6+1)},
            iterations_evaluated=len(curve), budget_exhausted=trial != 'fixed100' and len(curve) == limit,
            fit_seconds=time.perf_counter()-tick, peak_rss_mib=sampler.peak_mb,
            ordered_features=factors, outer_labels_accessed=False)
        v3.atomic_write_json(stage/'result.json', result)
        v3.atomic_write_json(stage/'curve.json', history)
    finally:
        for group in sequences.values():
            for seq in group:
                seq.close()


def selection(out, fold):
    rows = [base.read_json(out/fold/'trials'/name/'result.json') for name, _ in policy.TRIALS]
    return policy.select_trial(rows)


def outer_config(ctx, chosen):
    config = {**ctx[1]['config']}
    config['model_params'] = {**config['model_params'], **dict(policy.TRIALS)[chosen['selected']]}
    config['num_boost_round'] = chosen['rounds']
    config['model_id'] = 'nested_b494_v1_' + chosen['selected']
    # The unchanged refit primitive is a fixed-parameter learner. Selection was external and past-only.
    return config


def run(out, ctx, bound):
    base.verify_inputs(ctx)
    for fold in base.FOLDS:
        if v3.completed_chunk(out/fold/'outer', bound):
            verify_selection(out, fold, bound)
            retire_cache(out, fold, bound)
            continue
        if shutil.disk_usage(out).free < 60 * 2**30:
            raise OSError('60 GiB free disk required')
        cache = out/fold/'cache'
        v3.publish(cache, bound, lambda stage: prepare_blocks(stage, ctx, fold))
        for trial, changes in policy.TRIALS:
            print(f'{fold}: trial {trial}', flush=True)
            v3.publish(out/fold/'trials'/trial, bound,
                lambda stage: train_inner(stage, cache, ctx[-1]['Broad494'], ctx[1]['config'], trial, changes))
        chosen = selection(out, fold)
        def freeze_selection(stage):
            v3.atomic_write_json(stage/'selection.json', chosen)
        v3.publish(out/fold/'selection', bound, freeze_selection)
        verify_selection(out, fold, bound)
        def refit(stage):
            precompute_fold(stage, fold, ctx[0], outer_config(ctx, chosen), ctx[2], ctx[3], ctx[-1]['Broad494'])
            current = base.read_json(stage/'resource.json')
            original = base.read_json(BASELINE/'Broad494'/fold/'resource.json')
            if current['batch_receipts'] != original['batch_receipts']:
                raise ValueError('outer refit sample changed from frozen B494')
        v3.publish(out/fold/'outer', bound, refit)
        retire_cache(out, fold, bound)
        print(f'{fold}: outer completed; {chosen}', flush=True)
    v3.atomic_write_json(out/'status.json', {'status': 'NINE_OUTER_PREDICTIONS_AWAITING_REPLAY'})


def retire_cache(out, fold, bound):
    """Release only this run's verified scratch, preserving the original receipt and a deletion intent."""
    cache = out/fold/'cache'
    receipt = base.read_json(cache/'receipt.json')
    if receipt['contract_hash'] != bound or not v3.completed_chunk(out/fold/'outer', bound):
        raise ValueError('cannot retire cache before committed outer refit')
    marker = out/fold/'cache_retirement.json'
    intent = dict(cache_receipt_sha256=v3.sha256_file(cache/'receipt.json'),
        files={n: h for n, h in receipt['file_hashes'].items() if n.endswith('.float64')},
        reason='consumed_scratch_not_required_for_replay')
    if marker.exists():
        if base.read_json(marker) != intent:
            raise ValueError('cache retirement mismatch')
    else:
        v3.completed_chunk(cache, bound)
        v3.atomic_write_json(marker, intent)
    for name, expected in intent['files'].items():
        path = (cache/name).resolve()
        if path.parent != cache.resolve() or path.suffix != '.float64':
            raise ValueError('scratch outside current cache')
        if path.exists():
            if v3.sha256_file(path) != expected:
                raise ValueError('scratch changed before retirement')
            path.unlink()


def verify_selection(out, fold, bound):
    for name, _ in policy.TRIALS:
        if not v3.completed_chunk(out/fold/'trials'/name, bound):
            raise ValueError('missing/changed inner trial')
    if not v3.completed_chunk(out/fold/'selection', bound):
        raise ValueError('missing selection receipt')
    if selection(out, fold) != base.read_json(out/fold/'selection/selection.json'):
        raise ValueError('selection changed or used different inputs')


def replay(out, ctx, bound):
    from scripts.replay_research_protocol_v3_predictions import replay_fold
    from scipy.stats import spearmanr
    for fold in base.FOLDS:
        verify_selection(out, fold, bound)
        if not v3.completed_chunk(out/fold/'outer', bound):
            raise ValueError('missing outer predictions')
    def writer(stage):
        results, accesses = [], {}
        for fold in base.FOLDS:
            # Independent scalar statistics: do not call policy.daily_ic.
            for trial, _ in policy.TRIALS:
                folder = out/fold/'trials'/trial
                pred = pd.read_parquet(folder/'inner_predictions.parquet')
                values = []
                for _, part in pred.groupby('datetime'):
                    values.append(0. if part.score.nunique() < 2 or part.target.nunique() < 2
                                  else float(spearmanr(part.score, part.target).statistic))
                expected = pd.read_csv(folder/'daily.csv').ic.to_numpy()
                np.testing.assert_allclose(values, expected, atol=1e-12, rtol=0)
                if not np.isclose(np.mean(values), base.read_json(folder/'result.json')['mean_ic'], atol=1e-12, rtol=0):
                    raise ValueError('independent inner aggregation mismatch')
            result, access = replay_fold(out/fold/'outer', fold, ctx[-1]['Broad494'], ctx[2], ctx[3],
                                         outer_config(ctx, selection(out, fold)))
            results.append(result)
            accesses[fold] = access
            print(f'{fold}: independent outer replay exact', flush=True)
        v3.atomic_write_json(stage/'result.json', dict(status='all_nine_exact', folds=results,
                             inner_statistics='independent_scipy_verified', outer_labels_accessed=False))
        v3.atomic_write_json(stage/'access.json', accesses)
    v3.publish(out/'verification', bound, writer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'run', 'replay'])
    parser.add_argument('--run-id', default='lgbm_nested_20260916_v1')
    args = parser.parse_args()
    if not re.fullmatch(r'lgbm_nested_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run id')
    ctx = context()
    if args.action == 'preflight':
        packet = contract(ctx)
        print(json.dumps(dict(status='METADATA_PREFLIGHT_PASS', factors=len(packet['factors']),
            trials=len(policy.TRIALS), folds=len(base.FOLDS), maximum_fits=90,
            free_gib=shutil.disk_usage(ROOT).free/2**30,
            splits={fold: {role: [days[0], days[-1], len(days)] for role, days in data.items()}
                    for fold, data in packet['splits'].items()}, research_values_read=False), indent=2))
        return
    out = ROOT/'outputs/lightgbm_hyperparameter_research'/args.run_id
    with v3.run_lock(out/'run.lock'):
        bound = bind(out, ctx)
        try:
            (run if args.action == 'run' else replay)(out, ctx, bound)
        except Exception as error:
            v3.atomic_write_json(out/'status.json', dict(status='FAILED_PRESERVE_EVIDENCE', action=args.action,
                                                       error_type=type(error).__name__, error=str(error)))
            raise


if __name__ == '__main__':
    main()
