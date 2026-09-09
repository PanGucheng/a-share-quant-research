"""P0-P2 only: annual assignments, feature/maturity audit, two engineering fits."""
# ruff: noqa: E402
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gc
import json
import importlib.metadata
import os
import multiprocessing
from pathlib import Path
import re
import sys
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

import numpy as np
import pandas as pd
import psutil
import yaml

from factor_research.candidate_consolidation import verify_primary
from factor_research.long_history_screening import KEYS, LABEL, sha256_file
from model_research.long_history_inputs import read_features, read_keys, read_labels, feature_profile, combine_profiles
from model_research.long_history_walk_forward import (
    prepare_training_batch, fit_arrays, predict, fit_sequences, Float64FileSequence,
)
from model_research.linear_models import _MemorySampler
from qlib_baseline.io import atomic_write_json
from qlib_baseline.settings import load_settings
from research_validation.canonical_dataset import canonical_dataset_identity, canonical_hash
from research_validation.research_protocol_v3 import START, END, DATASET_ID, build_protocol, training_dates, allowed_dates
from scripts.run_candidate_consolidation_v0_5 import run_lock, completed_chunk

CODE = ['scripts/run_research_protocol_v3_mvp.py', 'research_validation/research_protocol_v3.py',
        'model_research/long_history_inputs.py', 'model_research/long_history_walk_forward.py',
        'research_validation/canonical_dataset.py', 'research_validation/purged_split.py',
        'research_validation/labels.py', 'factor_research/long_history_screening.py',
        'model_research/targets.py', 'model_research/preprocessing.py', 'qlib_baseline/io.py',
        'scripts/run_candidate_consolidation_v0_5.py', 'model_research/linear_models.py',
        'qlib_baseline/settings.py', 'scripts/revalidate_research_protocol_v3.py']


def write_csv(path, frame):
    frame.to_csv(path, index=False)


def publish(folder, contract_hash, writer):
    if completed_chunk(folder, contract_hash):
        return
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = folder.parent / ('.' + folder.name + '_' + uuid.uuid4().hex)
    stage.mkdir()
    tick = time.perf_counter()
    writer(stage)
    files = {p.name: sha256_file(p) for p in stage.iterdir() if p.is_file()}
    atomic_write_json(stage / 'receipt.json', dict(status='complete', contract_hash=contract_hash,
                                                 file_hashes=files, wall_seconds=time.perf_counter() - tick))
    stage.replace(folder)


def runtime_identity():
    import qlib
    source = Path(qlib.__file__).resolve().parents[1]
    commit = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                            capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', str(source), 'status', '--porcelain'],
                           capture_output=True, text=True, check=True).stdout
    runtime_dirty = subprocess.run(['git', '-C', str(source), 'status', '--porcelain', '--', 'qlib'],
                                   capture_output=True, text=True, check=True).stdout
    if runtime_dirty:
        raise ValueError('Qlib runtime source must be clean for a recomputation contract')
    return dict(python=sys.version, qlib_commit=commit,
                qlib_runtime_clean=True, qlib_other_worktree_status=dirty,
                packages={n: importlib.metadata.version(n) for n in
                          ['numpy', 'pandas', 'pyarrow', 'lightgbm', 'pyqlib', 'scipy', 'psutil']},
                threads={n: os.environ[n] for n in
                         ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']})


def bind(config, out, provider):
    if (config['canonical_dataset_id'] != DATASET_ID or config['development_end'] != str(END.date())
            or config['entry_lag'] != 1 or config['holding_days'] != 20 or config['extra_embargo'] != 0
            or config['history'] != 'expanding' or config['sliding_sensitivity_enabled']
            or config['competition_authorized'] or config['recent_diagnostic_authorized']):
        raise ValueError('unsupported P0-P2 contract')
    base = ROOT / config['canonical_root']
    partitions = pd.read_csv(base / 'partition_manifest.csv')
    lineage = pd.read_csv(base / 'factor_lineage.csv')
    if canonical_dataset_identity(partitions, lineage) != DATASET_ID:
        raise ValueError('canonical identity mismatch')
    if len(lineage) != 774 or lineage.research_usable.sum() != 765 or lineage.factor.nunique() != 774:
        raise ValueError('invalid canonical qualification')
    path = provider / 'calendars/day.txt'
    if sha256_file(path) != config['calendar_sha256']:
        raise ValueError('canonical calendar differs from audited plan')
    calendar = pd.DatetimeIndex(pd.to_datetime(path.read_text().splitlines()))
    protocol = build_protocol(calendar)
    calendar = calendar[(calendar >= START) & (calendar <= END)]
    frozen = verify_primary(ROOT)
    frozen.update({str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (ROOT / 'reports/candidate_consolidation_v0_5/v0_5_1').iterdir() if p.is_file()})
    working_path = ROOT / 'reports/candidate_consolidation_v0_5/working_set.csv'
    frozen[str(working_path.relative_to(ROOT))] = sha256_file(working_path)
    contract = dict(config=config, runtime=runtime_identity(),
                    execution=dict(wide_storage='monthly_float64_sequence', wide_memory_budget_gib=12),
                    code_hashes={p: sha256_file(ROOT / p) for p in CODE},
                    canonical_metadata={p.name: sha256_file(p) for p in
                                        [base / 'manifest.json', base / 'partition_manifest.csv', base / 'factor_lineage.csv']},
                    frozen_evidence=frozen, provider=str(provider),
                    price_source_hashes={str(p.relative_to(provider)): sha256_file(p)
                                        for p in sorted((provider / 'features').glob('*/close.day.bin'))})
    if not contract['price_source_hashes']:
        raise ValueError('no price sources')
    out.mkdir(parents=True, exist_ok=True)
    contract_path = out / 'contract.json'
    if contract_path.exists() and json.loads(contract_path.read_text()) != contract:
        raise ValueError('run identity changed: use a new run-id')
    if not contract_path.exists():
        atomic_write_json(contract_path, contract)
    return partitions, lineage, calendar, protocol, canonical_hash(contract)


def prepare(out, protocol, contract_hash):
    def writer(stage):
        for name, table in protocol.items():
            write_csv(stage / (name + '.csv'), table)
        sliding = []
        for fold_id in protocol['folds'].fold_id:
            days = training_dates(protocol, fold_id, 'sliding_4_calendar_years')
            sliding.append(dict(fold_id=fold_id, start=days[0], end=days[-1], dates=len(days), execution_enabled=False))
        write_csv(stage / 'sliding_preview.csv', pd.DataFrame(sliding))
    publish(out / 'p0', contract_hash, writer)


def audit_year(stage, year, partitions, lineage, calendar, protocol, loader):
    tick, access = time.perf_counter(), []
    days = calendar[calendar.year == year]
    keys = read_keys(partitions, days, access=access)
    write_csv(stage / 'daily_keys.csv', keys.groupby('datetime').agg(keys=('instrument', 'size')).reset_index())
    keys.to_parquet(stage / 'keys.parquet', index=False)
    if year <= 2022:
        next_fold = f'annual_{year + 1}'
        # Before 2014 only whole years are required by all registered folds.
        cutoff = protocol['folds'].set_index('fold_id').loc[next_fold, 'last_legal_train_signal'] if year >= 2014 else days[-1]
        names = sorted(lineage.loc[lineage.research_usable, 'factor'])
        profiles, prefixes = [], []
        for offset in range(0, len(names), 25):
            selected = names[offset:offset + 25]
            frame = read_features(partitions, selected, days, access=access)
            if not frame[KEYS].equals(keys):
                raise ValueError('audit feature/universe key axes differ')
            profiles.append(feature_profile(frame, selected))
            prefixes.append(feature_profile(frame.loc[frame.datetime <= cutoff], selected))
            print(f'P1 {year}: features {min(offset + 25, len(names))}/{len(names)}', flush=True)
            del frame
        write_csv(stage / 'full_profile.csv', pd.concat(profiles, ignore_index=True))
        write_csv(stage / 'prefix_profile.csv', pd.concat(prefixes, ignore_index=True))
    feature_seconds = time.perf_counter() - tick
    # Count labels only after the year's feature-only statistics have been sealed to disk.
    mature = protocol['intervals'].loc[protocol['intervals'].label_end_time <= END, 'feature_time']
    label_keys = keys.loc[keys.datetime.isin(mature)]
    labels = read_labels(label_keys, calendar, loader, access=access)
    labels.to_parquet(stage / 'labels.parquet', index=False)
    counts = labels.assign(finite=np.isfinite(labels[LABEL])).groupby('datetime').agg(
        label_keys=('instrument', 'size'), finite_labels=('finite', 'sum')).reset_index()
    write_csv(stage / 'daily_labels.csv', counts)
    atomic_write_json(stage / 'access.json', {'access': access})
    atomic_write_json(stage / 'timing.json', dict(feature_seconds=feature_seconds, total_seconds=time.perf_counter() - tick))


def aggregate_audit(out, protocol, contract_hash):
    eligibility, sample_rows = [], []
    for fold in protocol['folds'].itertuples(index=False):
        year = pd.Timestamp(fold.evaluation_start).year
        profiles = [pd.read_csv(out / 'audit' / str(y) / 'full_profile.csv') for y in range(2010, year - 1)]
        profiles.append(pd.read_csv(out / 'audit' / str(year - 1) / 'prefix_profile.csv'))
        profile = combine_profiles(profiles).assign(fold_id=fold.fold_id)
        eligibility.append(profile)
        for role in ['train', 'predict', 'evaluate']:
            source = protocol['assignments']
            days = pd.DatetimeIndex(source.loc[(source.fold_id == fold.fold_id) & (source.role == role), 'datetime'])
            selected = []
            for y in sorted(set(days.year)):
                path = out / 'audit' / str(y) / ('daily_keys.csv' if role == 'predict' else 'daily_labels.csv')
                data = pd.read_csv(path, parse_dates=['datetime'])
                selected.append(data[data.datetime.isin(days)])
            table = pd.concat(selected)
            if len(table) != len(days):
                raise ValueError('audit count dates missing')
            sample_rows.append(dict(fold_id=fold.fold_id, role=role, dates=len(days),
                                    keys=int(table['keys' if role == 'predict' else 'label_keys'].sum()),
                                    finite_labels=None if role == 'predict' else int(table.finite_labels.sum()),
                                    min_daily_finite_labels=None if role == 'predict' else int(table.finite_labels.min()),
                                    dates_below_100=None if role == 'predict' else int(table.finite_labels.lt(100).sum())))
    all_eligibility = pd.concat(eligibility, ignore_index=True)
    board = pd.read_csv(ROOT / 'reports/long_history_multi_evaluator_screening_v1/candidate_board.csv',
                        usecols=['factor', 'pass_count'])
    broad = set(pd.read_csv(ROOT / 'reports/candidate_consolidation_v0_5/working_set.csv').factor)
    strict = set(board.loc[board.pass_count == 3, 'factor'])
    if len(broad) != 494 or len(strict) != 332:
        raise ValueError('diagnostic pool identities changed')
    pools = []
    for fold_id, group in all_eligibility.groupby('fold_id'):
        for name, members in [('physical_765', set(group.factor)), ('broad_working_494', broad), ('strict_3of3', strict)]:
            pool = group.loc[group.factor.isin(members)]
            pools.append(dict(fold_id=fold_id, pool=name, identity_count=len(members),
                              train_eligible=int(pool.eligible.sum()), status='diagnostic_identity_not_P3_freeze'))
        for name in ['baseline', 'human_economic_diversified']:
            pools.append(dict(fold_id=fold_id, pool=name, identity_count=None, train_eligible=None,
                              status='pool_identity_not_frozen'))
    def writer(stage):
        write_csv(stage / 'feature_eligibility.csv', all_eligibility)
        write_csv(stage / 'sample_counts.csv', pd.DataFrame(sample_rows))
        write_csv(stage / 'pool_counts.csv', pd.DataFrame(pools))
    publish(out / 'p1', contract_hash, writer)


def audit_worker(year, out, provider, partitions, lineage, calendar, protocol, contract_hash):
    folder = out / 'audit' / str(year)
    if completed_chunk(folder, contract_hash):
        return year
    import qlib
    from qlib.data import D
    qlib.init(provider_uri=str(provider), region='cn', kernels=1)
    def loader(symbols, lo, hi):
        return D.features(symbols, ['$close'], start_time=lo, end_time=hi, freq='day').reset_index()
    publish(folder, contract_hash,
            lambda stage: audit_year(stage, year, partitions, lineage, calendar, protocol, loader))
    gc.collect()
    return year


def cached_training_labels(out, protocol, fold_id, days):
    allowed_dates(protocol, fold_id, 'train', days)
    pieces = []
    for year in sorted(set(days.year)):
        part = days[days.year == year]
        data = pd.read_parquet(out / 'audit' / str(year) / 'labels.parquet',
                               filters=[('datetime', 'in', part.tolist())], columns=[*KEYS, LABEL, 'exit_date'])
        if not data.datetime.isin(part).all():
            raise ValueError('cached label dates outside request')
        pieces.append(data)
    result = pd.concat(pieces, ignore_index=True).sort_values(KEYS).reset_index(drop=True)
    boundary = protocol['folds'].set_index('fold_id').loc[fold_id, 'evaluation_start']
    if result.exit_date.isna().any() or result.exit_date.ge(boundary).any():
        raise ValueError('cached labels not available before annual fit')
    if (result.duplicated(KEYS).any()
            or not pd.DatetimeIndex(result.datetime.unique()).equals(pd.DatetimeIndex(days))):
        raise ValueError('cached label keys or dates missing/duplicated')
    return result


def require_audit(out, contract_hash, years):
    for folder in [out / 'p0', out / 'p1', *[out / 'audit' / str(y) for y in years]]:
        if not completed_chunk(folder, contract_hash):
            raise ValueError(f'verified audit required: {folder}')


def canary(stage, fold_id, out, config, partitions, protocol):
    access, batch_receipts = [], []
    eligible = pd.read_csv(out / 'p1/feature_eligibility.csv')
    eligible = eligible[(eligible.fold_id == fold_id) & eligible.eligible]
    factors = list(config['canary_features'])
    if not set(factors) <= set(eligible.factor):
        raise ValueError('registered engineering feature not train-eligible')
    days = training_dates(protocol, fold_id)
    # Upper bound from the feature-only key grid, not label-selected membership.
    count = pd.read_csv(out / 'p1/sample_counts.csv')
    capacity = int(count.loc[(count.fold_id == fold_id) & (count.role == 'train'), 'keys'].iloc[0])
    bytes_required = capacity * (len(factors) + 2) * 8
    if bytes_required * 4 > min(config['canary_memory_budget_gib'] * 2**30, psutil.virtual_memory().available * .8):
        raise MemoryError('insufficient memory for bounded resource canary')
    tick = time.perf_counter()
    with _MemorySampler() as sampler:
        matrix = np.empty((capacity, len(factors)), dtype='float64')
        target, weights = np.empty(capacity), np.empty(capacity)
        position = 0
        for year in sorted(set(days.year)):
            selected = days[days.year == year]
            features = read_features(partitions, factors, selected, access=access,
                                     protocol=protocol, fold_id=fold_id, role='train')
            labels = cached_training_labels(out, protocol, fold_id, selected)
            x, y, w, receipt = prepare_training_batch(features, labels, factors, protocol=protocol,
                                                     fold_id=fold_id, minimum_pairs=config['minimum_daily_pairs'])
            end = position + len(y)
            matrix[position:end], target[position:end], weights[position:end] = x, y, w
            position = end
            batch_receipts.append(dict(year=int(year), **receipt))
            del features, labels, x, y, w
            gc.collect()
        prepare_seconds = time.perf_counter() - tick
        model = fit_arrays(matrix[:position], target[:position], weights[:position], factors,
                           fold_id=fold_id, config=config)
        model.booster.save_model(str(stage / 'model.txt'))
        del matrix, target, weights
        gc.collect()
        source = protocol['assignments']
        evaluation = pd.DatetimeIndex(source.loc[(source.fold_id == fold_id) & (source.role == 'predict'), 'datetime'])
        tick = time.perf_counter()
        features = read_features(partitions, factors, evaluation, access=access,
                                 protocol=protocol, fold_id=fold_id, role='predict')
        predictions = predict(model, features, protocol=protocol)
        monthly = pd.concat([predict(model, g, protocol=protocol)
                             for _, g in features.groupby(features.datetime.dt.month)], ignore_index=True)
        if not predictions.equals(monthly):
            raise ValueError('year/month prediction parity failed')
        predict_seconds = time.perf_counter() - tick
        # No OOF label load, IC, importance, return, or winner calculation in P2.
        predictions.to_parquet(stage / 'engineering_predictions.parquet', index=False)
        receipt = dict(**model.receipt, prepare_seconds=prepare_seconds,
                        predict_seconds=predict_seconds, prediction_rows=len(predictions),
                        prediction_coverage=float(predictions.score.notna().mean()),
                        predicted_dates=int(predictions.datetime.nunique()), monthly_exact_parity=True,
                        full_width_resource_qualified=False, feature_count=len(factors),
                        experiment_class='engineering_canary_no_model_selection', batch_receipts=batch_receipts)
    receipt['peak_rss_mib'] = sampler.peak_mb
    atomic_write_json(stage / 'resource.json', receipt)
    atomic_write_json(stage / 'access.json', {'access': access})


def wide_canary(stage, fold_id, out, config, partitions, protocol):
    """Recompute all training values in float64; no imported audit or float32 cache."""
    factors = sorted(pd.read_csv(ROOT / 'reports/candidate_consolidation_v0_5/working_set.csv').factor)
    eligible = pd.read_csv(out / 'p1/feature_eligibility.csv')
    eligible = eligible[(eligible.fold_id == fold_id) & eligible.eligible]
    if len(factors) != 494 or len(set(factors)) != 494 or not set(factors) <= set(eligible.factor):
        raise ValueError('wide pool is not the registered train-eligible 494 identities')
    days = training_dates(protocol, fold_id)
    access, receipts, sequences, targets, weights = [], [], [], [], []
    tick = time.perf_counter()
    try:
        with _MemorySampler() as sampler:
            for month in days.to_period('M').unique():
                selected = days[days.to_period('M') == month]
                features = read_features(partitions, factors, selected, access=access, protocol=protocol,
                                         fold_id=fold_id, role='train')
                labels = cached_training_labels(out, protocol, fold_id, selected)
                x, y, w, receipt = prepare_training_batch(features, labels, factors,
                    protocol=protocol, fold_id=fold_id, minimum_pairs=config['minimum_daily_pairs'])
                path = stage / f'train_{month}.float64'
                x.tofile(path)
                sequences.append(Float64FileSequence(path, len(factors)))
                targets.append(y)
                weights.append(w)
                receipts.append(dict(month=str(month), **receipt))
                print(f'{fold_id}: prepared {month}, rows={len(y)}', flush=True)
                del features, labels, x
                gc.collect()
            prepare_seconds = time.perf_counter() - tick
            model = fit_sequences(sequences, np.concatenate(targets), np.concatenate(weights), factors,
                                  fold_id=fold_id, config=config)
            model.booster.save_model(str(stage / 'model.txt'))
            import lightgbm as lgb
            restored = lgb.Booster(model_file=str(stage / 'model.txt'))
            source = protocol['assignments']
            evaluation = pd.DatetimeIndex(source.loc[
                (source.fold_id == fold_id) & (source.role == 'predict'), 'datetime'])
            predictions = []
            tick = time.perf_counter()
            for month in evaluation.to_period('M').unique():
                selected = evaluation[evaluation.to_period('M') == month]
                frame = read_features(partitions, factors, selected, access=access,
                                      protocol=protocol, fold_id=fold_id, role='predict')
                pred = predict(model, frame, protocol=protocol)
                daily = pd.concat([predict(model, part, protocol=protocol)
                                  for _, part in frame.groupby('datetime')], ignore_index=True)
                if not pred.equals(daily):
                    raise ValueError('wide month/day prediction parity failed')
                original = model.booster
                model.booster = restored
                if not pred.equals(predict(model, frame, protocol=protocol)):
                    raise ValueError('saved wide model prediction parity failed')
                model.booster = original
                predictions.append(pred)
                del frame
            predictions = pd.concat(predictions, ignore_index=True)
            predictions.to_parquet(stage / 'engineering_predictions.parquet', index=False)
            predict_seconds = time.perf_counter() - tick
    finally:
        for seq in sequences:
            seq.close()
    resource = dict(model.receipt)
    resource.update(storage='monthly_float64_sequence', feature_count=len(factors),
        peak_rss_mib=sampler.peak_mb, prepare_seconds=prepare_seconds, predict_seconds=predict_seconds,
        prediction_rows=len(predictions), prediction_coverage=float(predictions.score.notna().mean()),
        predicted_dates=int(predictions.datetime.nunique()), monthly_daily_exact_parity=True,
        saved_model_exact_parity=True, memory_budget_gib=12,
        fold_resource_within_budget=bool(sampler.peak_mb <= 12 * 1024),
        full_width_resource_qualified=False, engineering_only=True, batch_receipts=receipts)
    atomic_write_json(stage / 'resource.json', resource)
    atomic_write_json(stage / 'access.json', {'access': access})


def finalize(out, config, contract_hash):
    for path in [out / 'p0', out / 'p1', *[out / 'audit' / str(y) for y in range(2010, 2024)],
                 *[out / 'canary' / f for f in config['canary_folds']]]:
        if not completed_chunk(path, contract_hash):
            raise ValueError(f'phase incomplete: {path}')
    samples = pd.read_csv(out / 'p1/sample_counts.csv')
    if samples.dates_below_100.dropna().gt(0).any():
        raise ValueError('some dates lack sufficient finite labels')
    atomic_write_json(out / 'status.json', dict(status='p0_p2_recomputed_pending_review',
                                              protocol_ready=False, pool_experiment_ready=False,
                                              full_width_resource_qualified=False,
                                              held_recent_accessed=False, competition_started=False,
                                              contract_hash=contract_hash))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='v3_mvp_20260909')
    parser.add_argument('--stage', choices=['prepare', 'audit', 'canary', 'wide-canary', 'finalize', 'all'], default='prepare')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=4,
                        help='Independent audit years only; model fits stay sequential with 8 threads')
    parser.add_argument('--wide-fold', choices=['annual_2015', 'annual_2023'], default='annual_2015')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run-id')
    config = yaml.safe_load((ROOT / 'configs/research_protocol_v3_mvp.yaml').read_text())
    settings = load_settings(project_root=ROOT)
    out = ROOT / 'outputs/research_protocol_v3_mvp' / args.run_id
    with run_lock(out / 'run.lock'):
        print('Binding V3 canonical metadata and immutable source hashes', flush=True)
        partitions, lineage, calendar, protocol, contract_hash = bind(config, out, settings.qlib_provider)
        prepare(out, protocol, contract_hash)
        if args.stage == 'prepare':
            atomic_write_json(out / 'status.json', dict(status='p0_complete', contract_hash=contract_hash))
            return
        # Verify physical source integrity once per invocation before consuming any values.
        relevant = partitions[(pd.to_datetime(partitions.effective_start) <= END) &
                              (pd.to_datetime(partitions.effective_end) >= START)]
        for row in relevant.drop_duplicates('partition_path').itertuples(index=False):
            if sha256_file(Path(row.partition_path)) != row.output_sha256:
                raise ValueError('canonical partition hash mismatch')
        if args.stage in ['audit', 'all']:
            atomic_write_json(out / 'status.json', dict(status='auditing', completed_years=0,
                                                       workers=args.workers, contract_hash=contract_hash))
            with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn')) as executor:
                jobs = [executor.submit(audit_worker, year, out, settings.qlib_provider, partitions,
                                        lineage, calendar, protocol, contract_hash) for year in range(2010, 2024)]
                for count, future in enumerate(as_completed(jobs), 1):
                    year = future.result()
                    atomic_write_json(out / 'status.json', dict(status='auditing', completed_years=count,
                                                               last_completed_year=year, workers=args.workers,
                                                               contract_hash=contract_hash))
                    print(f'P1 completed {count}/14 years (year {year})', flush=True)
            aggregate_audit(out, protocol, contract_hash)
            atomic_write_json(out / 'status.json', dict(status='p1_complete', contract_hash=contract_hash))
        if args.stage in ['canary', 'all']:
            for fold_id in config['canary_folds']:
                require_audit(out, contract_hash, sorted(set(training_dates(protocol, fold_id).year)))
                atomic_write_json(out / 'status.json', dict(status='resource_canary', fold_id=fold_id, contract_hash=contract_hash))
                publish(out / 'canary' / fold_id, contract_hash,
                        lambda stage, f=fold_id: canary(stage, f, out, config, partitions, protocol))
        if args.stage == 'wide-canary':
            fold_id = args.wide_fold
            require_audit(out, contract_hash, sorted(set(training_dates(protocol, fold_id).year)))
            atomic_write_json(out / 'status.json', dict(status='wide_recomputation_running',
                                                       fold_id=fold_id, contract_hash=contract_hash))
            try:
                publish(out / 'wide_canary' / fold_id, contract_hash,
                        lambda stage: wide_canary(stage, fold_id, out, config, partitions, protocol))
            except Exception as error:
                atomic_write_json(out / 'status.json', dict(status='wide_recomputation_failed',
                    fold_id=fold_id, contract_hash=contract_hash, error_type=type(error).__name__, error=str(error)))
                raise
            atomic_write_json(out / 'status.json', dict(status='wide_fold_recomputed_pending_review',
                fold_id=fold_id, contract_hash=contract_hash, full_width_resource_qualified=False))
        if args.stage in ['finalize', 'all']:
            finalize(out, config, contract_hash)


if __name__ == '__main__':
    main()
