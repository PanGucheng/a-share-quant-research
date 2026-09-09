"""Read-only post-run verification; write a separate compact review artifact.

Reload all four saved models and replay all their development predictions from
canonical features without using prediction labels or the runner's predict helper.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_research_protocol_v3_mvp as runner  # noqa: E402
from scripts.revalidate_research_protocol_v3 import calendar_oracle, verify_counts  # noqa: E402
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check(run):
    contract = read_json(run / 'contract.json')
    bound = runner.canonical_hash(contract)
    if runner.runtime_identity() != contract['runtime']:
        raise ValueError('runtime differs from completed run')
    for name, expected in contract['code_hashes'].items():
        if runner.sha256_file(ROOT / name) != expected:
            raise ValueError(f'code mismatch: {name}')
    canonical = ROOT / contract['config']['canonical_root']
    for name, expected in contract['canonical_metadata'].items():
        if runner.sha256_file(canonical / name) != expected:
            raise ValueError(f'metadata mismatch: {name}')
    for name, expected in contract['frozen_evidence'].items():
        if runner.sha256_file(ROOT / name) != expected:
            raise ValueError(f'upstream evidence mismatch: {name}')
    provider = Path(contract['provider'])
    for name, expected in contract['price_source_hashes'].items():
        if runner.sha256_file(provider / name) != expected:
            raise ValueError(f'price content mismatch: {name}')
    partitions = pd.read_csv(canonical / 'partition_manifest.csv')
    source_count = 0
    relevant = partitions.loc[(pd.to_datetime(partitions.effective_start) <= runner.END) &
                              (pd.to_datetime(partitions.effective_end) >= runner.START)]
    for row in relevant.drop_duplicates('partition_path').itertuples():
        if runner.sha256_file(Path(row.partition_path)) != row.output_sha256:
            raise ValueError(f'partition content mismatch: {row.partition_path}')
        source_count += 1
    calendar_path = provider / 'calendars/day.txt'
    if runner.sha256_file(calendar_path) != contract['config']['calendar_sha256']:
        raise ValueError('calendar mismatch')
    calendar = pd.DatetimeIndex(pd.to_datetime(calendar_path.read_text().splitlines()))
    calendar = calendar[calendar >= runner.START]
    protocol = runner.build_protocol(calendar)
    oracle = calendar_oracle(calendar, protocol)
    folders = [run / 'p0', run / 'p1', *[run / 'audit' / str(y) for y in range(2010, 2024)],
               *[run / kind / fold for kind in ['canary', 'wide_canary']
                 for fold in contract['config']['canary_folds']], run / 'revalidation_probe',
               run / 'revalidation_probe_summary', run / 'revalidation_verify_summary']
    receipts = {}
    for folder in folders:
        receipt = runner.completed_chunk(folder, bound)
        if not receipt:
            raise ValueError(f'missing completed chunk: {folder}')
        receipts[folder.relative_to(run).as_posix()] = dict(
            receipt_sha256=runner.sha256_file(folder / 'receipt.json'), files=len(receipt['file_hashes']))
    counts = verify_counts(run, protocol)
    # Old/new equality is a diagnostic comparison, not the source of qualification.
    old = run.parent / 'v3_mvp_20260909_v2'
    comparisons = {}
    for kind in ['p0', 'p1', *[f'audit/{y}' for y in range(2010, 2024)]]:
        old_receipt = read_json(old / kind / 'receipt.json')
        new_receipt = read_json(run / kind / 'receipt.json')
        names = set(old_receipt['file_hashes']) & set(new_receipt['file_hashes'])
        names -= {'timing.json', 'access.json'}
        for name in sorted(names):
            left, right = old / kind / name, run / kind / name
            if runner.sha256_file(left) != old_receipt['file_hashes'][name]:
                raise ValueError(f'old comparison source no longer matches receipt: {left}')
            if name.endswith('.csv'):
                pd.testing.assert_frame_equal(pd.read_csv(left), pd.read_csv(right), check_exact=True)
            elif name.endswith('.parquet'):
                pd.testing.assert_frame_equal(pd.read_parquet(left), pd.read_parquet(right), check_exact=True)
            else:
                raise ValueError(f'unhandled comparison: {name}')
            comparisons[f'{kind}/{name}'] = 'exact_table_equality'
    results = []
    for kind in ['canary', 'wide_canary']:
        for fold in contract['config']['canary_folds']:
            folder = run / kind / fold
            resource = read_json(folder / 'resource.json')
            model = lgb.Booster(model_file=str(folder / 'model.txt'))
            model_hash = hashlib.sha256(model.model_to_string().encode()).hexdigest()
            if model_hash != resource['model_sha256'] or model.current_iteration() != 100:
                raise ValueError('saved model hash or iteration mismatch')
            factors = resource['ordered_features']
            if model.feature_name() != factors or len(factors) != resource['feature_count']:
                raise ValueError('saved model feature order mismatch')
            stored = pd.read_parquet(folder / 'engineering_predictions.parquet')
            if stored.duplicated(runner.KEYS).any():
                raise ValueError('duplicate prediction keys')
            expected_keys = pd.read_parquet(run / 'audit' / fold[-4:] / 'keys.parquet')
            pd.testing.assert_frame_equal(stored[runner.KEYS], expected_keys)
            days = pd.DatetimeIndex(stored.datetime.unique())
            expected_days = pd.DatetimeIndex(protocol['assignments'].loc[
                (protocol['assignments'].fold_id == fold) & (protocol['assignments'].role == 'predict'), 'datetime'])
            if not days.equals(expected_days):
                raise ValueError('incomplete prediction calendar')
            access = []
            for month in days.to_period('M').unique():
                selected = days[days.to_period('M') == month]
                frame = runner.read_features(partitions, factors, selected, access=access,
                    protocol=protocol, fold_id=fold, role='predict')
                matrix = frame[factors].to_numpy(dtype='float64', copy=True)
                matrix[~np.isfinite(matrix)] = np.nan
                valid = np.isfinite(matrix).any(axis=1)
                scores = np.full(len(frame), np.nan)
                scores[valid] = model.predict(matrix[valid], num_threads=8)
                saved = stored.loc[stored.datetime.isin(selected)].reset_index(drop=True)
                pd.testing.assert_frame_equal(frame[runner.KEYS], saved[runner.KEYS])
                np.testing.assert_array_equal(scores, saved.score.to_numpy())
                np.testing.assert_array_equal(np.where(valid, 'predicted', 'all_features_missing'), saved.reason)
                del frame, matrix, scores, saved
                gc.collect()
            coverage = float(stored.score.notna().mean())
            if coverage != resource['prediction_coverage'] or len(stored) != resource['prediction_rows']:
                raise ValueError('prediction coverage summary mismatch')
            old_model_equal = None
            if kind == 'canary':
                old_resource = read_json(old / kind / fold / 'resource.json')
                old_model_equal = model_hash == old_resource['model_sha256']
                pd.testing.assert_frame_equal(stored, pd.read_parquet(old / kind / fold / 'engineering_predictions.parquet'), check_exact=True)
                if not old_model_equal:
                    raise ValueError('8-column old/new model mismatch')
            recorded = read_json(folder / 'access.json')['access']
            for event in recorded:
                runner.allowed_dates(protocol, fold, event['role'], [pd.Timestamp(event['start'])])
                runner.allowed_dates(protocol, fold, event['role'], [pd.Timestamp(event['end'])])
                if pd.Timestamp(event['end']) > runner.END:
                    raise ValueError('out-of-development access')
            results.append(dict(kind=kind, fold_id=fold, feature_count=len(factors),
                fit_rows=resource['fit_rows'], model_sha256=model_hash, replayed_rows=len(stored),
                replayed_dates=len(days), all_saved_predictions_exact=True, old_model_equal=old_model_equal,
                coverage=coverage, peak_rss_gib=resource['peak_rss_mib']/1024,
                fit_seconds=resource['fit_seconds'], prepare_seconds=resource['prepare_seconds'],
                dataset_seconds=resource['dataset_seconds'], predict_seconds=resource['predict_seconds'],
                wall_seconds=read_json(folder / 'receipt.json')['wall_seconds']))
            print(f'Verified {kind}/{fold}: {len(stored)} predictions, coverage={coverage:.8f}', flush=True)
    return dict(run_id=run.name, contract_hash=bound, checked_chunks=receipts,
                checked_partition_files=source_count, checked_price_files=len(contract['price_source_hashes']),
                calendar_oracle=oracle, count_check=counts, old_new_tables=comparisons, models=results,
                scope='P0-P2 engineering verification only; no IC, returns, model selection or recent replay',
                remaining_scope='No full 36-fit pool experiment or all-history independent label oracle',
                verification_script_sha256=runner.sha256_file(Path(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'v3_recompute_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid recomputation run-id')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('preserve prior verification; choose a new output path')
    result = check(ROOT / 'outputs/research_protocol_v3_mvp' / args.run_id)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(f'Post-run verification complete: {output}', flush=True)


if __name__ == '__main__':
    main()
